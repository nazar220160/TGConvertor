"""Opt-in server checks for every direction and interface. PYTEST_DONT_REWRITE"""

import asyncio
import hashlib
import importlib.util
import logging
import os
import shutil
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

from TGConvertor import API, APIData
from TGConvertor.converter import load_session
from TGConvertor.sessions.pyro import PyroSession

from ._live_helpers import native_client, native_identity, perform_conversion, rate_limited_get_me
from .test_conversion_matrix import (
    KINDS,
    OUTPUT_PASSCODE,
    SOURCE_PASSCODE,
    STRING_KINDS,
    format_backend,
    format_of,
)

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.getenv("TGCONVERTOR_RUN_LIVE") != "1", reason="Live verification is opt-in"
    ),
]


def source_snapshot(path):
    files = list(path.rglob("*")) if path.is_dir() else [path]
    if path.is_file():
        files += [Path(str(path) + suffix) for suffix in ("-wal", "-shm", "-journal")]
    return {str(p): hashlib.sha256(p.read_bytes()).digest() for p in files if p.is_file()}


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def live_account(tmp_path_factory):
    source_env = os.getenv("TGCONVERTOR_LIVE_SESSION")
    if not source_env:
        pytest.fail(
            "Set TGCONVERTOR_LIVE_SESSION to an already authorized local session", pytrace=False
        )
    backend = PyroSession.installed_backend()
    if backend is None or any(
        importlib.util.find_spec(name) is None for name in ("telethon", "opentele2")
    ):
        pytest.fail(
            "Install dev, telethon, tdata and exactly one of pyrogram/kurigram", pytrace=False
        )
    api_id, api_hash = os.getenv("TGCONVERTOR_API_ID"), os.getenv("TGCONVERTOR_API_HASH")
    if api_id is None and api_hash is None:
        api = API.TelegramDesktop.copy()
    elif not api_id or not api_hash:
        pytest.fail("Set both TGCONVERTOR_API_ID and TGCONVERTOR_API_HASH", pytrace=False)
    else:
        api = APIData(int(api_id), api_hash)
    path = Path(source_env)
    before = source_snapshot(path)
    previous_logging = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        with tempfile.TemporaryDirectory(
            prefix="live-inputs-", dir=tmp_path_factory.getbasetemp()
        ) as temp:
            root = Path(temp)
            source_format = os.getenv("TGCONVERTOR_LIVE_FORMAT", "telethon")
            passcode = os.getenv("TGCONVERTOR_TDATA_PASSCODE", "")
            seed = await load_session(
                path, source_format, api=api, input_type="file", passcode=passcode
            )
            # Open a private copy directly with the native SDK before using any conversion.
            original = root / ("baseline-tdata" if source_format == "tdata" else "baseline.session")
            if path.is_dir():
                shutil.copytree(path, original)
                for item in original.rglob("*"):
                    item.chmod(0o700 if item.is_dir() else 0o600)
            else:
                shutil.copyfile(path, original)
                original.chmod(0o600)
            original_kind = (
                "tdata_plain"
                if source_format == "tdata"
                else "telethon_file"
                if source_format == "telethon"
                else f"{backend}_file"
            )
            client, family = await native_client(original_kind, original, api, passcode=passcode)
            try:
                user = await asyncio.wait_for(
                    native_identity(client, family, expected_key=seed.auth_key), timeout=180
                )
            except Exception as exc:
                pytest.fail(
                    f"Source authorization check failed: {type(exc).__name__}. Supply a new authorized session.",
                    pytrace=False,
                )
            seed.user_id = user.id
            seed.is_bot = bool(getattr(user, "bot", getattr(user, "is_bot", False)))
            if seed.is_bot or seed.test_mode:
                pytest.fail(
                    "The full tdata matrix requires a production user test account", pytrace=False
                )
            assert source_snapshot(path) == before, "The original source changed"
            inputs = {}
            for kind in KINDS:
                if kind in STRING_KINDS:
                    inputs[kind] = getattr(seed, f"to_{format_of(kind)}_string")()
                else:
                    output = (
                        root / kind / ("tdata" if kind.startswith("tdata") else "input.session")
                    )
                    if kind.startswith("tdata"):
                        await seed.to_tdata_folder(
                            output, passcode=SOURCE_PASSCODE if kind == "tdata_encrypted" else ""
                        )
                    elif kind == "telethon_file":
                        await seed.to_telethon_file(output)
                    else:
                        await seed.to_pyrogram_file(output, backend=format_backend(kind))
                    inputs[kind] = output
            yield seed, inputs, backend, source_snapshot(root)
            assert source_snapshot(path) == before, "The original source changed"
    finally:
        logging.disable(previous_logging)


@pytest.mark.parametrize("interface", ["api", "manager", "cli", "process"])
@pytest.mark.parametrize("source_kind", KINDS)
@pytest.mark.parametrize("target_kind", KINDS)
async def test_real_authorization_every_direction(
    interface, source_kind, target_kind, live_account, tmp_path
):
    seed, inputs, backend, before = live_account
    if target_kind in ("pyrogram_file", "kurigram_file") and format_backend(target_kind) != backend:
        pytest.skip("Run this output with its matching native client in the other live environment")
    # Remove real authorization outputs even after a failed test; pytest normally retains tmp_path.
    with tempfile.TemporaryDirectory(prefix="live-output-", dir=tmp_path) as directory:
        result = await perform_conversion(
            interface, inputs[source_kind], source_kind, target_kind, seed, Path(directory)
        )
        client, family = await native_client(
            target_kind,
            result,
            seed.api,
            passcode=OUTPUT_PASSCODE if target_kind == "tdata_encrypted" else "",
        )
        try:
            user = await asyncio.wait_for(
                native_identity(client, family, expected_key=seed.auth_key), timeout=180
            )
        except Exception as exc:
            pytest.fail(f"Native output authorization failed: {type(exc).__name__}", pytrace=False)
        assert user.id == seed.user_id, "Telegram returned a different account"
    # Every file used as an input must remain untouched by the conversion.
    root = next(Path(value).parents[1] for value in inputs.values() if isinstance(value, Path))
    current = source_snapshot(root)
    assert current == before, "Live input files changed"
    await asyncio.sleep(1)


async def test_real_public_manager_operations(live_account):
    from TGConvertor import SessionManager

    seed, _, _, _ = live_account
    manager = SessionManager.from_telethon_string(seed.to_telethon_string(), seed.api)
    assert await manager.validate() is True, "Public validate() did not confirm authorization"
    assert await manager.get_user_id() == seed.user_id, "Owner lookup returned another account"
    assert manager.client is None, "The manager did not disconnect"
    context = SessionManager.from_telethon_string(seed.to_telethon_string(), seed.api)
    async with context as client:
        user = await rate_limited_get_me(client)
        assert user.id == seed.user_id, "The async context returned another account"
    assert context.client is None, "The async context did not disconnect"
    client = seed.pyrogram_client()
    try:
        user = await asyncio.wait_for(
            native_identity(client, "pyrogram", expected_key=seed.auth_key), timeout=180
        )
    except Exception as exc:
        pytest.fail(f"Public Pyrogram/Kurigram client failed: {type(exc).__name__}", pytrace=False)
    assert user.id == seed.user_id, "The public native client returned another account"
