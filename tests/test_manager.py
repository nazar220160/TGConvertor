from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from TGConvertor import API, APIData, MissingDependencyError, ValidationError
from TGConvertor.sessions.pyro import PyroSession


def test_api_copy_and_repr(session, api):
    assert session.api is not api
    session.api.device_model = "Changed"
    assert api.device_model == "Desktop"
    assert api.api_hash not in repr(api)
    assert session.auth_key.hex() not in repr(session)
    assert session.auth_key_hex == session.auth_key.hex()
    assert API.TelegramDesktop.api_id == 2040


@pytest.mark.parametrize("api_id,api_hash", [(0, "hash"), (True, "hash"), (123, ""), (123, None)])
def test_invalid_api(api_id, api_hash):
    with pytest.raises(ValueError):
        APIData(api_id, api_hash)


@pytest.mark.parametrize("kwargs", [{"is_bot": True}, {"test_mode": True}])
def test_tdata_account_constraints(session, kwargs):
    for key, value in kwargs.items():
        setattr(session, key, value)
    with pytest.raises(ValidationError, match="production user"):
        _ = session.tdata


@pytest.fixture
def client(session, monkeypatch):
    fake = SimpleNamespace(
        connect=AsyncMock(),
        disconnect=AsyncMock(),
        get_me=AsyncMock(return_value=SimpleNamespace(id=12345, bot=False, phone="123456789")),
    )
    monkeypatch.setattr(session, "telethon_client", lambda: fake)
    return fake


async def test_context_lifecycle(session, client):
    async with session as active:
        assert active is client
        assert session.client is client
        with pytest.raises(RuntimeError, match="already"):
            await session.__aenter__()
    client.connect.assert_awaited_once()
    client.disconnect.assert_awaited_once()
    assert session.client is None


async def test_context_cleans_up_on_body_exception(session, client):
    with pytest.raises(RuntimeError, match="body"):
        async with session:
            raise RuntimeError("body")
    client.disconnect.assert_awaited_once()
    assert session.client is None


async def test_context_cleans_up_on_connect_failure(session, client):
    client.connect.side_effect = RuntimeError("connect")
    with pytest.raises(RuntimeError, match="connect"):
        async with session:
            pass
    client.disconnect.assert_awaited_once()
    assert session.client is None


async def test_context_cleans_up_on_disconnect_failure(session, client):
    client.disconnect.side_effect = RuntimeError("disconnect")
    with pytest.raises(RuntimeError, match="disconnect"):
        async with session:
            pass
    assert session.client is None


async def test_network_identity_is_explicit_and_cached(session, client):
    session.user_id = None
    assert await session.get_user_id() == 12345
    assert session.phone_number == "123456789"
    assert session.valid is True
    assert await session.get_user_id() == 12345
    client.get_me.assert_awaited_once()
    assert await session.validate() is True


async def test_invalid_network_authorization(session, client):
    session.user_id = None
    client.get_me.return_value = None
    assert await session.validate() is False
    assert session.user_id is None
    with pytest.raises(ValidationError, match="not logged in"):
        await session.get_user_id()


def test_optional_client_dependency_detection(monkeypatch, session):
    from importlib.metadata import PackageNotFoundError

    from TGConvertor.sessions.pyro import pyro

    def missing(name):
        raise PackageNotFoundError(name)

    monkeypatch.setattr(pyro, "version", missing)
    assert PyroSession.installed_backend() is None
    with pytest.raises(MissingDependencyError, match="kurigram"):
        session.pyrogram_client()
    monkeypatch.setattr(pyro, "version", lambda name: "1.0")
    with pytest.raises(MissingDependencyError, match="share"):
        session.pyrogram_client()


def test_missing_telethon(monkeypatch, session):
    import sys

    monkeypatch.setitem(sys.modules, "telethon", None)
    with pytest.raises(MissingDependencyError, match="telethon"):
        session.telethon_client()
