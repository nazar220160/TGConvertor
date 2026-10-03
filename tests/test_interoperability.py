"""Use upstream clients as independent format readers/writers, without a login."""

import pytest

from TGConvertor import SessionManager, TeleSession

pytestmark = pytest.mark.integration


async def test_telethon_native_interoperability(session, tmp_path):
    pytest.importorskip("telethon")
    from telethon.crypto import AuthKey
    from telethon.sessions import SQLiteSession, StringSession

    session.server_address, session.port, session.takeout_id = "2001:67c:4e8:f002::a", 8443, 12345
    string = StringSession(session.to_telethon_string())
    assert string.auth_key.key == session.auth_key
    assert (string.dc_id, string.server_address, string.port) == (2, session.server_address, 8443)
    assert TeleSession.from_string(string.save()).to_string() == session.to_telethon_string()
    exported = tmp_path / "exported.session"
    await session.to_telethon_file(exported)
    native = SQLiteSession(str(exported))
    try:
        assert native.auth_key.key == session.auth_key
        assert native.takeout_id == session.takeout_id
        assert native.server_address == session.server_address
    finally:
        native.close()
    # Create through the current upstream schema; read it without triggering migrations.
    imported = tmp_path / "native.session"
    native = SQLiteSession(str(imported))
    native.set_dc(2, "149.154.167.51", 443)
    native.auth_key = AuthKey(session.auth_key)
    native.save()
    native.close()
    before = imported.read_bytes()
    result = await SessionManager.from_telethon_file(imported)
    assert result.auth_key == session.auth_key
    assert imported.read_bytes() == before
    client = session.telethon_client()
    assert client.session.auth_key.key == session.auth_key
    assert client.session.server_address == session.server_address
    assert client.session.port == session.port
    await client.disconnect()


async def test_pyrogram_native_interoperability(session, tmp_path):
    pytest.importorskip("pyrogram")
    from pyrogram import Client

    from TGConvertor.sessions.pyro import PyroSession

    backend = PyroSession.installed_backend()
    assert backend in ("pyrogram", "kurigram")
    await session.to_pyrogram_file(tmp_path / "exported.session", backend=backend)
    native = Client(
        "exported", workdir=str(tmp_path), api_id=session.api.api_id, api_hash=session.api.api_hash
    )
    await native.storage.open()
    try:
        assert await native.storage.auth_key() == session.auth_key
        assert await native.storage.user_id() == session.user_id
        assert await native.storage.export_session_string() == session.to_pyrogram_string()
    finally:
        await native.storage.close()
    native = Client(
        "created", workdir=str(tmp_path), api_id=session.api.api_id, api_hash=session.api.api_hash
    )
    await native.storage.open()
    try:
        for field, value in {
            "dc_id": 2,
            "api_id": session.api_id,
            "auth_key": session.auth_key,
            "user_id": session.user_id,
            "test_mode": False,
            "is_bot": False,
        }.items():
            await getattr(native.storage, field)(value)
        await native.storage.save()
    finally:
        await native.storage.close()
    imported = tmp_path / "created.session"
    before = imported.read_bytes()
    result = await SessionManager.from_pyrogram_file(imported)
    assert result.to_pyrogram_string() == session.to_pyrogram_string()
    assert imported.read_bytes() == before
    # Native memory storage must also accept our string and preserve 64-bit owner IDs.
    client = session.pyrogram_client()
    await client.storage.open()
    try:
        assert await client.storage.user_id() == session.user_id
        assert await client.storage.auth_key() == session.auth_key
    finally:
        await client.storage.close()
