"""Offline verification of the exact native adapters used by the live suite."""

import hmac
from pathlib import Path

import pytest

from TGConvertor.converter import load_session
from TGConvertor.sessions.pyro import PyroSession

from ._live_helpers import close_native, native_client, perform_conversion
from .test_conversion_matrix import (
    KINDS,
    OUTPUT_PASSCODE,
    STRING_KINDS,
    format_backend,
    format_of,
)


@pytest.mark.parametrize("interface", ["api", "manager", "cli", "process"])
@pytest.mark.parametrize("kind", KINDS)
async def test_live_native_adapter_and_producer_offline(
    interface, kind, session, tmp_path, offline_process_env
):
    if kind.startswith("tdata"):
        pytest.importorskip("opentele2")
    backend = PyroSession.installed_backend()
    if kind.startswith("telethon"):
        pytest.importorskip("telethon")
    if format_of(kind) == "pyrogram":
        pytest.importorskip("pyrogram")
        if kind not in STRING_KINDS and format_backend(kind) != backend:
            pytest.skip("Native file reader is tested with its matching client")
    result = await perform_conversion(
        interface,
        session.to_pyrogram_string(),
        "pyrogram_string",
        kind,
        session,
        tmp_path,
        process_env=offline_process_env,
    )
    restored = await load_session(
        result,
        format_of(kind),
        api=session.api,
        passcode=OUTPUT_PASSCODE if kind == "tdata_encrypted" else "",
    )
    assert hmac.compare_digest(restored.auth_key, session.auth_key)
    client, family = await native_client(
        kind,
        result,
        session.api,
        passcode=OUTPUT_PASSCODE if kind == "tdata_encrypted" else "",
    )
    try:
        if family == "pyrogram":
            await client.storage.open()
            assert hmac.compare_digest(await client.storage.auth_key(), session.auth_key)
            assert await client.storage.user_id() == session.user_id
            assert await client.storage.dc_id() == session.dc_id
        else:
            assert hmac.compare_digest(client.session.auth_key.key, session.auth_key)
            assert client.session.dc_id == session.dc_id
            if isinstance(result, Path):
                assert result.exists()
    finally:
        await close_native(client, family)


@pytest.mark.parametrize(
    "error_name,attribute", [("FloodWait", "value"), ("FloodWaitError", "seconds")]
)
async def test_live_rate_limit_waits_before_retry(error_name, attribute, monkeypatch):
    from ._live_helpers import rate_limited_get_me

    error = type(error_name, (Exception,), {attribute: 2})
    waits = []
    identity = object()

    class Client:
        calls = 0

        async def get_me(self):
            self.calls += 1
            if self.calls == 1:
                raise error()
            return identity

    async def sleep(seconds):
        waits.append(seconds)

    monkeypatch.setattr("tests._live_helpers.asyncio.sleep", sleep)
    client = Client()
    assert await rate_limited_get_me(client) is identity
    assert client.calls == 2
    assert waits == [3]


async def test_live_rate_limit_retries_are_bounded(monkeypatch):
    from ._live_helpers import rate_limited_get_me

    error = type("FloodWait", (Exception,), {"value": 2})
    waits = []

    class Client:
        calls = 0

        async def get_me(self):
            self.calls += 1
            raise error()

    async def sleep(seconds):
        waits.append(seconds)

    monkeypatch.setattr("tests._live_helpers.asyncio.sleep", sleep)
    client = Client()
    with pytest.raises(error):
        await rate_limited_get_me(client)
    assert client.calls == 3
    assert waits == [3, 3]


async def test_live_authorization_errors_are_not_retried(monkeypatch):
    from ._live_helpers import rate_limited_get_me

    error = type("AuthKeyUnregisteredError", (Exception,), {})

    class Client:
        calls = 0

        async def get_me(self):
            self.calls += 1
            raise error()

    async def sleep(seconds):
        pytest.fail("Authorization failures must not be treated as rate limits")

    monkeypatch.setattr("tests._live_helpers.asyncio.sleep", sleep)
    client = Client()
    with pytest.raises(error):
        await rate_limited_get_me(client)
    assert client.calls == 1
