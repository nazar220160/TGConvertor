"""Conversion of bot/test authorizations, incomplete metadata, and multiple accounts."""

import asyncio
from pathlib import Path

import pytest
from typer.testing import CliRunner

from TGConvertor import SessionManager, ValidationError, convert
from TGConvertor.__main__ import app
from TGConvertor.converter import load_session
from TGConvertor.sessions.tdata import _opentele

from .test_conversion_matrix import (
    KINDS,
    SOURCE_PASSCODE,
    cli_args,
    destination_for,
    format_backend,
    format_of,
    snapshot,
)


@pytest.mark.parametrize("interface", ["api", "cli"])
@pytest.mark.parametrize("test_mode,is_bot", [(False, True), (True, False), (True, True)])
@pytest.mark.parametrize("source_kind", ["pyrogram_string", "pyrogram_file", "kurigram_file"])
@pytest.mark.parametrize("target_kind", KINDS)
async def test_bot_and_test_dc_profiles(
    interface, test_mode, is_bot, source_kind, target_kind, session, tmp_path
):
    session.test_mode, session.is_bot = test_mode, is_bot
    if source_kind == "pyrogram_string":
        source = session.to_pyrogram_string()
    else:
        source = tmp_path / "profile.session"
        await session.to_pyrogram_file(source, backend=format_backend(source_kind))
    before = snapshot(tmp_path)
    destination = destination_for(target_kind, tmp_path)
    rejects_tdata = target_kind.startswith("tdata")
    if interface == "api":
        if rejects_tdata:
            with pytest.raises(ValidationError, match="production user accounts"):
                await convert(source, "pyrogram", "tdata", destination, api=session.api)
            assert snapshot(tmp_path) == before
            return
        output = await convert(
            source,
            "pyrogram",
            format_of(target_kind),
            destination,
            api=session.api,
            backend=format_backend(target_kind),
        )
    else:
        args, env, destination = cli_args(source, source_kind, target_kind, session, tmp_path)
        result = await asyncio.to_thread(CliRunner().invoke, app, args, env=env)
        if rejects_tdata:
            assert result.exit_code == 1
            assert "production user accounts" in result.stderr
            assert result.stdout == ""
            assert snapshot(tmp_path) == before
            return
        assert result.exit_code == 0, result.output
        output = destination if destination is not None else result.stdout.strip()
    restored = await load_session(output, format_of(target_kind), api=session.api)
    assert restored.auth_key == session.auth_key
    assert restored.dc_id == session.dc_id
    assert restored.test_mode is test_mode
    if format_of(target_kind) == "pyrogram":
        assert restored.is_bot is is_bot
        assert restored.user_id == session.user_id
        assert restored.api_id == session.api_id
    else:
        # Telethon has no persisted owner ID or bot flag.
        assert restored.user_id is None
        assert restored.is_bot is False
    if isinstance(source, Path):
        assert source.read_bytes() == before[source.name]


@pytest.mark.parametrize("interface", ["api", "cli"])
@pytest.mark.parametrize(
    "source_kind", ["telethon_file", "telethon_string", "gramjs_file", "gramjs_string"]
)
@pytest.mark.parametrize(
    "target_kind", [kind for kind in KINDS if format_of(kind) in ("pyrogram", "tdata")]
)
async def test_owner_required_for_every_identity_target(
    interface, source_kind, target_kind, session, tmp_path
):
    if source_kind.endswith("string"):
        source = getattr(session, f"to_{format_of(source_kind)}_string")()
    else:
        source = tmp_path / "ownerless.session"
        await getattr(session, f"to_{format_of(source_kind)}_file")(source)
    before = snapshot(tmp_path)
    destination = destination_for(target_kind, tmp_path)
    if interface == "api":
        with pytest.raises(ValidationError, match="user_id"):
            await convert(source, format_of(source_kind), format_of(target_kind), destination)
    else:
        args, env, _ = cli_args(source, source_kind, target_kind, session, tmp_path)
        index = args.index("--user-id")
        del args[index : index + 2]
        result = await asyncio.to_thread(CliRunner().invoke, app, args, env=env)
        assert result.exit_code == 1
        assert "user_id" in result.stderr
        assert result.stdout == ""
        assert "Traceback" not in result.output
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("passcode", ["", SOURCE_PASSCODE])
@pytest.mark.parametrize("account_index", [None, 0, 1])
async def test_native_multi_account_selection(session, tmp_path, passcode, account_index):
    pytest.importorskip("opentele2")
    TDesktop, Account, AuthKey, AuthKeyType, DcId, NativeAPI, _ = _opentele()
    native_api = NativeAPI(**vars(session.api))
    desktop = TDesktop(api=native_api)
    desktop.kPerformanceMode = False
    identities = [
        (session.user_id, session.auth_key, 2),
        (session.user_id + 100, bytes(reversed(session.auth_key)), 4),
    ]
    for index, (owner, key, dc) in enumerate(identities):
        account = Account(owner=desktop, api=native_api, index=index)
        account._setMtpAuthorizationCustom(
            DcId(dc), owner, [AuthKey(key, AuthKeyType.ReadFromFile, DcId(dc))]
        )
        desktop._addSingleAccount(account)
    # The selected main account differs from accounts[0]. Native metadata persists it.
    desktop._TDesktop__active_index = 1
    source = tmp_path / "multi-account"
    assert desktop.SaveTData(str(source), passcode=passcode)
    before = snapshot(source)
    native = TDesktop(str(source), passcode=passcode)
    assert len(native.accounts) == 2
    assert native.mainAccount.UserId == identities[1][0]
    expected_id, expected_key, expected_dc = identities[
        1 if account_index is None else account_index
    ]
    loaded = SessionManager.from_tdata_folder(
        source, passcode=passcode, account_index=account_index
    )
    assert (loaded.user_id, loaded.auth_key, loaded.dc_id) == (
        expected_id,
        expected_key,
        expected_dc,
    )
    output = await convert(
        source, "tdata", "pyrogram", passcode=passcode, account_index=account_index
    )
    restored = SessionManager.from_pyrogram_string(output)
    assert (restored.user_id, restored.auth_key, restored.dc_id) == (
        expected_id,
        expected_key,
        expected_dc,
    )
    options = [] if account_index is None else ["--account-index", str(account_index)]
    result = await asyncio.to_thread(
        CliRunner().invoke,
        app,
        ["convert", str(source), "-f", "tdata", "-t", "pyrogram", *options],
        env={"TGCONVERTOR_TDATA_PASSCODE": passcode},
    )
    assert result.exit_code == 0, result.output
    restored = SessionManager.from_pyrogram_string(result.stdout.strip())
    assert (restored.user_id, restored.auth_key, restored.dc_id) == (
        expected_id,
        expected_key,
        expected_dc,
    )
    info = await asyncio.to_thread(
        CliRunner().invoke,
        app,
        ["info", str(source), "-f", "tdata", *options],
        env={"TGCONVERTOR_TDATA_PASSCODE": passcode},
    )
    assert info.exit_code == 0, info.output
    assert str(expected_id) in info.output
    assert expected_key.hex() not in info.output
    assert snapshot(source) == before
