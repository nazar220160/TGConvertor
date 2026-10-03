import base64
import hashlib
import os
import struct
from unittest.mock import patch

import pytest

from TGConvertor import GramSession, SessionManager, ValidationError, convert
from TGConvertor.converter import load_session

from ._gramjs_helpers import gramjs


@pytest.mark.parametrize(
    "address", ["149.154.167.51", "2001:67c:4e8:f002::a", "::1", "localhost", "dc.example.org"]
)
@pytest.mark.parametrize("port", [80, 443, 8080, 32767])
def test_native_gramjs_both_directions(auth_key, address, port):
    native = gramjs(
        {"action": "write", "dc": 2, "key": list(auth_key), "address": address, "port": port}
    )
    codec = GramSession.from_string(native["session"])
    assert codec.auth_key == auth_key
    assert codec.port == port
    restored = gramjs({"session": codec.to_string()})
    assert restored["keyHash"] == hashlib.sha256(auth_key).hexdigest()
    assert restored["port"] == port and restored["dc"] == 2
    assert GramSession.from_string(restored["session"]).server_address == codec.server_address


@pytest.mark.parametrize(
    "address", ["149.154.167.51", "2001:67c:4e8:f002::a", "::1", "dc.example.org"]
)
def test_codec_roundtrip(auth_key, address):
    session = GramSession(dc_id=2, auth_key=auth_key, server_address=address)
    restored = GramSession.from_string(session.to_string())
    assert restored.auth_key == auth_key
    assert restored.server_address == session.server_address
    assert restored.port == 443
    assert not restored.test_mode


@pytest.mark.parametrize(
    "change",
    [
        {"port": 0},
        {"port": -1},
        {"port": 32768},
        {"port": True},
        {"dc_id": 0},
        {"dc_id": True},
        {"auth_key": bytes(256)},
        {"auth_key": b"short"},
        {"server_address": ""},
        {"server_address": "a.b"},
        {"server_address": "x" * 101},
        {"server_address": "bad host"},
        {"server_address": "-bad.example"},
        {"server_address": "é.example"},
        {"server_address": 123},
        {"test_mode": "yes"},
    ],
)
def test_invalid_fields(auth_key, change):
    with pytest.raises(ValidationError):
        GramSession(**({"dc_id": 2, "auth_key": auth_key} | change))


@pytest.mark.parametrize(
    "string",
    [
        None,
        "",
        "2abc",
        "1!",
        "1" + "a" * 513,
        "1" + base64.b64encode(b"\x02\x00\x04host\x01\xbb" + bytes(256)).decode(),
        "1" + base64.b64encode(b"\x02\xff\xff" + bytes(range(256))).decode(),
        "1" + base64.b64encode(b"\x02\x00\x04\xffabc\x01\xbb" + bytes(range(256))).decode(),
    ],
)
def test_invalid_strings(string):
    with pytest.raises(ValidationError):
        GramSession.from_string(string)


def test_wrong_length_and_trailing_data(auth_key):
    value = GramSession(dc_id=2, auth_key=auth_key).to_string()
    raw = base64.b64decode(value[1:])
    for changed in (raw[:-1], raw + b"x", raw[:1] + struct.pack(">h", 99) + raw[3:]):
        with pytest.raises(ValidationError):
            GramSession.from_string("1" + base64.b64encode(changed).decode())


async def test_standard_base64_auto_detection(session):
    value = session.to_gramjs_string()
    assert "/" in value
    assert (await load_session(value, "gramjs")).auth_key == session.auth_key
    assert (await convert(value.rstrip("="), "gramjs", "telethon")).startswith("1")


async def test_text_file_safety(session, tmp_path):
    path = tmp_path / "nested/session.txt"
    await session.to_gramjs_file(path)
    before = path.read_bytes()
    if os.name != "nt":
        assert path.stat().st_mode & 0o777 == 0o600
    assert (await SessionManager.from_gramjs_file(path)).auth_key == session.auth_key
    with pytest.raises(FileExistsError):
        await session.to_gramjs_file(path)
    assert path.read_bytes() == before
    alias = tmp_path / "alias.txt"
    try:
        alias.symlink_to(tmp_path / "missing")
    except OSError:
        return  # Windows may not grant symlink privileges.
    with pytest.raises(FileExistsError):
        await session.to_gramjs_file(alias)


async def test_failed_publish_removes_temporary_file(session, tmp_path):
    with (
        patch("TGConvertor.sessions.gramjs.os.link", side_effect=OSError("disk failure")),
        pytest.raises(OSError),
    ):
        await session.to_gramjs_file(tmp_path / "out.txt")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("content", [b"x" * 1025, b"\xff\xfe", b"", b"SQLite format 3\x00"])
async def test_bad_text_file(content, tmp_path):
    path = tmp_path / "bad.txt"
    path.write_bytes(content)
    with pytest.raises(ValidationError):
        await GramSession.from_file(path)
    assert path.read_bytes() == content


async def test_bom_whitespace_missing_file(session, tmp_path):
    path = tmp_path / "bom.txt"
    path.write_text("\ufeff\n" + session.to_gramjs_string() + "\r\n", encoding="utf-8")
    assert (await load_session(path, "gramjs")).auth_key == session.auth_key
    with pytest.raises(FileNotFoundError):
        await GramSession.from_file(tmp_path / "missing")


@pytest.mark.parametrize("ipv6", [False, True])
def test_legacy_telethon_strings(session, ipv6):
    if ipv6:
        session.server_address = "2001:67c:4e8:f002::a"
    value = session.to_telethon_string()
    gram = GramSession.from_string(value)
    assert gram.auth_key == session.auth_key
    assert gram.server_address == session.telethon.server_address
    assert (
        gramjs({"session": gram.to_string()})["keyHash"]
        == hashlib.sha256(session.auth_key).hexdigest()
    )


async def test_owner_required_only_for_pyrogram_and_tdata(session):
    value = session.to_gramjs_string()
    assert isinstance(await convert(value, "gramjs", "telethon"), str)
    assert isinstance(await convert(session.to_telethon_string(), "telethon", "gramjs"), str)
    with pytest.raises(ValidationError, match="user_id"):
        await convert(value, "gramjs", "pyrogram")


def test_hostname_manager_preserves_endpoint(auth_key):
    gram = GramSession(dc_id=2, auth_key=auth_key, server_address="dc.example.org", port=8080)
    manager = SessionManager.from_gramjs_string(gram.to_string())
    assert manager.gramjs.server_address == "dc.example.org"
    assert manager.to_gramjs_string() == gram.to_string()
    with pytest.raises(ValidationError, match="IPv4 or IPv6"):
        manager.to_telethon_string()


def test_test_dc_detection(auth_key):
    gram = GramSession(dc_id=2, auth_key=auth_key, test_mode=True)
    assert gram.port == 80
    assert GramSession.from_string(gram.to_string()).test_mode is True


async def test_auto_invalid_version_does_not_echo_credentials():
    from typer.testing import CliRunner

    from TGConvertor.__main__ import app

    secret = "2" + "A" * 360
    result = CliRunner().invoke(app, ["convert", secret, "-f", "gramjs", "-t", "telethon"])
    assert result.exit_code == 1
    assert secret not in result.output
    assert "Unsupported GramJS string version" in result.output
