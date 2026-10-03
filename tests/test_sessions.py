import base64
import os
import sqlite3
import struct
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

import pytest

from TGConvertor import PyroSession, SessionManager, TeleSession, ValidationError
from TGConvertor.data_center import DataCenter
from TGConvertor.sessions._utils import write_database


@pytest.mark.parametrize(
    "dc_id,key,user_id",
    [
        (0, bytes(range(256)), None),
        (256, bytes(range(256)), None),
        (True, bytes(range(256)), None),
        (2, b"short", None),
        (2, bytes(256), None),
        (2, "not bytes", None),
        (2, bytes(range(256)), 0),
        (2, bytes(range(256)), -1),
        (2, bytes(range(256)), 2**63),
        (2, bytes(range(256)), True),
    ],
)
def test_reject_invalid_authorizations(dc_id, key, user_id):
    with pytest.raises(ValidationError):
        SessionManager(dc_id, key, user_id)


@pytest.mark.parametrize("address,port", [("149.154.167.51", 443), ("2001:67c:4e8:f002::a", 8443)])
def test_telethon_string_round_trip(auth_key, address, port):
    original = TeleSession(dc_id=2, auth_key=auth_key, server_address=address, port=port)
    encoded = original.to_string()
    restored = SessionManager.from_telethon_string(encoded)
    assert restored.to_telethon_string() == encoded
    assert restored.server_address == address
    assert restored.port == port
    assert restored.auth_key == auth_key
    assert restored.user_id is None
    assert TeleSession.decode(encoded[1:]) == base64.urlsafe_b64decode(encoded[1:])


@pytest.mark.parametrize("value", ["", "2invalid", "1!!!", "1AAAA", "1" + "A" * 800, None])
def test_invalid_telethon_strings(value):
    with pytest.raises(ValidationError):
        TeleSession.from_string(value)


@pytest.mark.parametrize("value", ["", "!!!", "AAAA", "A" * 800, None])
def test_invalid_pyrogram_strings(value):
    with pytest.raises(ValidationError):
        PyroSession.from_string(value)


@pytest.mark.parametrize("fmt,user_id", [(">B?256sI?", 123456), (">B?256sQ?", 2**40)])
def test_legacy_pyrogram_strings(auth_key, fmt, user_id):
    encoded = (
        base64.urlsafe_b64encode(struct.pack(fmt, 2, True, auth_key, user_id, True))
        .decode()
        .rstrip("=")
    )
    result = SessionManager.from_pyrogram_string(encoded)
    assert (result.dc_id, result.user_id, result.auth_key) == (2, user_id, auth_key)
    assert result.test_mode and result.is_bot
    assert result.api_id == result.api.api_id
    assert SessionManager.from_pyrogram_string(result.to_pyrogram_string()).user_id == user_id


@pytest.mark.parametrize("test_mode", [False, True])
@pytest.mark.parametrize("is_bot", [False, True])
def test_current_pyrogram_strings(session, test_mode, is_bot):
    session.test_mode, session.is_bot = test_mode, is_bot
    restored = SessionManager.from_pyrogram_string(session.to_pyrogram_string())
    assert restored.auth_key == session.auth_key
    assert restored.user_id == session.user_id
    assert restored.api_id == 12345
    assert restored.test_mode == test_mode
    assert restored.is_bot == is_bot


@pytest.mark.parametrize("factory", [TeleSession, SessionManager])
def test_test_dc_preserved(factory, auth_key):
    original = factory(dc_id=2, auth_key=auth_key, test_mode=True)
    string = original.to_string() if factory is TeleSession else original.to_telethon_string()
    result = SessionManager.from_telethon_string(string)
    assert result.test_mode is True
    assert result.server_address == DataCenter.TEST[2]
    assert result.port == 80


@pytest.mark.parametrize("loader", [TeleSession, PyroSession])
async def test_missing_file_does_not_create_it(tmp_path, loader):
    path = tmp_path / "missing.session"
    assert not await loader.validate(path)
    with pytest.raises(FileNotFoundError):
        await loader.from_file(path)
    assert not path.exists()


@pytest.mark.parametrize("loader", [TeleSession, PyroSession])
async def test_invalid_database(tmp_path, loader):
    path = tmp_path / "invalid.session"
    path.write_bytes(b"not sqlite")
    assert not await loader.validate(path)
    with pytest.raises(ValidationError):
        await loader.from_file(path)
    assert path.read_bytes() == b"not sqlite"


async def test_telethon_file_round_trip_and_contacts_are_not_owner(session, tmp_path):
    path = tmp_path / "tele.session"
    session.server_address, session.port, session.takeout_id = "2001:67c:4e8:f002::a", 8443, 98765
    await session.to_telethon_file(path)
    with closing(sqlite3.connect(path)) as db:
        db.execute("INSERT INTO entities VALUES (123, 42, 'some_contact', 123456, 'Contact', 0)")
        db.execute("CREATE TABLE extra (id INTEGER)")
        db.commit()
    before = path.read_bytes()
    assert await TeleSession.validate(path)
    result = await SessionManager.from_telethon_file(path)
    assert result.user_id is None
    assert result.phone_number is None
    assert result.auth_key == session.auth_key
    assert (result.server_address, result.port, result.takeout_id) == (
        session.server_address,
        8443,
        98765,
    )
    await result.to_telethon_file(tmp_path / "copy.session")
    copy = await SessionManager.from_telethon_file(tmp_path / "copy.session")
    assert copy.takeout_id == 98765
    assert path.read_bytes() == before
    assert not list(tmp_path.glob("*-journal"))


@pytest.mark.parametrize("backend", ["pyrogram", "kurigram", "auto"])
async def test_pyrogram_files_round_trip(session, tmp_path, backend):
    path = tmp_path / "nested" / f"{backend}.session"
    session.is_bot = session.test_mode = True
    await session.to_pyrogram_file(path, backend=backend)
    before = path.read_bytes()
    restored = await SessionManager.from_pyrogram_file(path)
    assert restored.to_pyrogram_string() == session.to_pyrogram_string()
    assert restored.test_mode and restored.is_bot
    assert await PyroSession.validate(path)
    assert path.read_bytes() == before


@pytest.mark.parametrize("backend", ["pyrogram", "kurigram"])
async def test_additive_columns_accepted(session, tmp_path, backend):
    path = tmp_path / "extra.session"
    await session.to_pyrogram_file(path, backend=backend)
    with closing(sqlite3.connect(path)) as db:
        db.execute("ALTER TABLE sessions ADD future_column TEXT")
        db.execute("CREATE TABLE extra (id INTEGER)")
        db.commit()
    restored = await SessionManager.from_pyrogram_file(path)
    assert restored.auth_key == session.auth_key


@pytest.mark.parametrize("format", ["telethon", "pyrogram"])
@pytest.mark.parametrize("rows", [0, 2])
async def test_empty_or_ambiguous_database(session, tmp_path, format, rows):
    path = tmp_path / "bad.session"
    if format == "telethon":
        await session.to_telethon_file(path)
        loader = TeleSession
    else:
        await session.to_pyrogram_file(path, backend="pyrogram")
        loader = PyroSession
    with closing(sqlite3.connect(path)) as db:
        if rows == 0:
            db.execute("DELETE FROM sessions")
        else:
            columns = [row[1] for row in db.execute("PRAGMA table_info(sessions)")]
            query = ",".join("3" if c == "dc_id" else c for c in columns)
            db.execute(f"INSERT INTO sessions SELECT {query} FROM sessions")
        db.commit()
    with pytest.raises(ValidationError, match="exactly one"):
        await loader.from_file(path)


@pytest.mark.parametrize("format", ["telethon", "pyrogram"])
async def test_overwrite_refused(session, tmp_path, format):
    path = tmp_path / "valuable.session"
    path.write_bytes(b"keep this")
    with pytest.raises(FileExistsError):
        await getattr(session, f"to_{format}_file")(path)
    assert path.read_bytes() == b"keep this"


@pytest.mark.skipif(os.name == "nt", reason="POSIX permissions")
async def test_private_output_and_symlink_refusal(session, tmp_path):
    path = tmp_path / "private.session"
    await session.to_telethon_file(path)
    assert path.stat().st_mode & 0o777 == 0o600
    link = tmp_path / "link.session"
    link.symlink_to(tmp_path / "missing-target")
    with pytest.raises(FileExistsError):
        await session.to_telethon_file(link)
    assert not (tmp_path / "missing-target").exists()


def test_failed_write_cleans_temporary_files(tmp_path):
    def fail(db):
        db.execute("CREATE TABLE sessions (id INTEGER)")
        raise RuntimeError("test failure")

    with pytest.raises(RuntimeError):
        write_database(tmp_path / "out.session", fail)
    assert list(tmp_path.iterdir()) == []


def test_concurrent_writers_cannot_replace_each_other(tmp_path):
    def create(value):
        def populate(db):
            db.execute("CREATE TABLE result (value INTEGER)")
            db.execute("INSERT INTO result VALUES (?)", (value,))

        try:
            write_database(tmp_path / "out.session", populate)
            return value
        except FileExistsError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(create, [1, 2]))
    assert sum(value is not None for value in results) == 1
    with closing(sqlite3.connect(tmp_path / "out.session")) as db:
        assert db.execute("SELECT value FROM result").fetchone()[0] in results
    assert [p.name for p in tmp_path.iterdir()] == ["out.session"]


def test_identity_required_and_bad_backend(auth_key):
    session = SessionManager(2, auth_key)
    with pytest.raises(ValidationError, match="user_id"):
        session.to_pyrogram_string()
    with pytest.raises(ValidationError, match="user_id"):
        _ = session.tdata
    with pytest.raises(ValidationError, match="api_id"):
        PyroSession(dc_id=2, auth_key=auth_key, user_id=123).to_string()


async def test_bad_backend(session, tmp_path):
    with pytest.raises(ValidationError, match="backend"):
        await session.to_pyrogram_file(tmp_path / "out.session", backend="bad")
    assert not (tmp_path / "out.session").exists()


@pytest.mark.parametrize(
    "kwargs", [{"api_id": 0}, {"api_id": 2**32}, {"test_mode": 2}, {"is_bot": "yes"}]
)
def test_bad_pyrogram_metadata(auth_key, kwargs):
    with pytest.raises(ValidationError):
        PyroSession(dc_id=2, auth_key=auth_key, **kwargs)


@pytest.mark.parametrize(
    "kwargs", [{"server_address": "invalid"}, {"port": 0}, {"port": 65536}, {"port": True}]
)
def test_bad_telethon_metadata(auth_key, kwargs):
    with pytest.raises(ValidationError):
        TeleSession(dc_id=2, auth_key=auth_key, **kwargs)


@pytest.mark.parametrize(
    "test_mode,ipv6,media",
    [
        (False, False, False),
        (True, False, False),
        (False, True, False),
        (True, True, False),
        (False, False, True),
        (False, True, True),
    ],
)
def test_data_centers(test_mode, ipv6, media):
    address, port = DataCenter(2, test_mode, ipv6, media)
    assert bool(":" in address) == ipv6
    assert port == (80 if test_mode else 443)
    with pytest.raises(ValidationError, match="Unknown"):
        DataCenter(200, test_mode, ipv6, media)


@pytest.mark.parametrize("offset", [5, -1])
def test_rejects_non_boolean_string_fields(session, offset):
    raw = bytearray(base64.urlsafe_b64decode(session.to_pyrogram_string() + "=="))
    raw[offset] = 2
    value = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    with pytest.raises(ValidationError, match="boolean"):
        PyroSession.from_string(value)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"date": -1},
        {"date": "now"},
        {"date": 2**63},
        {"server_address": "invalid"},
        {"port": 0},
        {"port": True},
    ],
)
def test_rejects_bad_pyrogram_connection_metadata(auth_key, kwargs):
    with pytest.raises(ValidationError):
        PyroSession(dc_id=2, auth_key=auth_key, **kwargs)


@pytest.mark.parametrize(
    "kwargs", [{"test_mode": "yes"}, {"takeout_id": 2**63}, {"takeout_id": "bad"}]
)
def test_rejects_bad_telethon_connection_metadata(auth_key, kwargs):
    with pytest.raises(ValidationError):
        TeleSession(dc_id=2, auth_key=auth_key, **kwargs)


async def test_kurigram_compatibility_import(session, tmp_path):
    from TGConvertor.sessions.pyro.kuri import PyroSession as KuriSession

    output = tmp_path / "kuri.session"
    await KuriSession(
        dc_id=2,
        auth_key=session.auth_key,
        user_id=session.user_id,
        api_id=session.api_id,
        server_address="149.154.167.51",
    ).to_file(output)
    restored = await SessionManager.from_pyrogram_file(output)
    assert restored.port == 443
    assert restored.server_address == "149.154.167.51"
