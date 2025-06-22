import pytest
import os
from pathlib import Path
from TGConvertor.sessions.pyro import PyroSession
from TGConvertor.exceptions import ValidationError

# Test data
TEST_DC_ID = 2
TEST_API_ID = 12345
TEST_AUTH_KEY = b'a' * 256 # Must be 256 bytes
TEST_USER_ID = 987654321
TEST_BOT_USER_ID = 1234567890 # Example bot ID
TEST_DATE = 1678886400 # Example timestamp


@pytest.fixture
def pyro_user_session_data():
    return {
        "dc_id": TEST_DC_ID,
        "api_id": TEST_API_ID,
        "auth_key": TEST_AUTH_KEY,
        "user_id": TEST_USER_ID,
        "is_bot": False,
        "test_mode": False
    }

@pytest.fixture
def pyro_bot_session_data():
    return {
        "dc_id": TEST_DC_ID,
        "api_id": TEST_API_ID,
        "auth_key": TEST_AUTH_KEY,
        "user_id": TEST_BOT_USER_ID,
        "is_bot": True,
        "test_mode": False
    }

def test_pyro_session_creation_user(pyro_user_session_data):
    session = PyroSession(**pyro_user_session_data)
    assert session.dc_id == pyro_user_session_data["dc_id"]
    assert session.api_id == pyro_user_session_data["api_id"]
    assert session.auth_key == pyro_user_session_data["auth_key"]
    assert session.user_id == pyro_user_session_data["user_id"]
    assert not session.is_bot
    assert not session.test_mode

def test_pyro_session_creation_bot(pyro_bot_session_data):
    session = PyroSession(**pyro_bot_session_data)
    assert session.dc_id == pyro_bot_session_data["dc_id"]
    assert session.api_id == pyro_bot_session_data["api_id"]
    assert session.auth_key == pyro_bot_session_data["auth_key"]
    assert session.user_id == pyro_bot_session_data["user_id"]
    assert session.is_bot
    assert not session.test_mode

def test_pyro_string_to_pyro_string_user(pyro_user_session_data):
    original_session = PyroSession(**pyro_user_session_data)
    session_str = original_session.to_string()

    new_session = PyroSession.from_string(session_str)

    assert new_session.dc_id == original_session.dc_id
    assert new_session.auth_key == original_session.auth_key
    assert new_session.user_id == original_session.user_id
    assert new_session.is_bot == original_session.is_bot
    assert new_session.test_mode == original_session.test_mode
    # API ID in string can be 0 if original was None, or the value.
    # TGConvertor's STRING_FORMAT always includes api_id.
    # If original_session.api_id was None, to_string() uses 0. from_string() reads it as 0.
    # If original_session.api_id was set, it should match.
    assert new_session.api_id == (original_session.api_id or 0)


def test_pyro_string_to_pyro_string_bot(pyro_bot_session_data):
    original_session = PyroSession(**pyro_bot_session_data)
    session_str = original_session.to_string()

    new_session = PyroSession.from_string(session_str)

    assert new_session.dc_id == original_session.dc_id
    assert new_session.auth_key == original_session.auth_key
    assert new_session.user_id == original_session.user_id
    assert new_session.is_bot == original_session.is_bot
    assert new_session.test_mode == original_session.test_mode
    assert new_session.api_id == (original_session.api_id or 0)

# Test old string formats (assuming they don't have api_id)
# For this, we need to craft such strings if possible, or find examples.
# PyroSession.from_string auto-detects.
# Let's simulate an old string by packing it directly.
import struct
import base64

def test_pyro_from_old_string_format_no_api_id(pyro_user_session_data):
    # Simulate OLD_STRING_FORMAT: >B?256sI? (dc_id, test_mode, auth_key, user_id, is_bot)
    # This format does not include api_id.
    packed_data = struct.pack(
        PyroSession.OLD_STRING_FORMAT,
        pyro_user_session_data["dc_id"],
        pyro_user_session_data["test_mode"],
        pyro_user_session_data["auth_key"],
        pyro_user_session_data["user_id"],
        pyro_user_session_data["is_bot"]
    )
    # Ensure length matches expected size for base64 decoding in from_string
    # The check in from_string is `len(session_string)`, which is the raw string length
    # The actual check should be on the decoded length, but from_string handles that.
    # Forcing length to STRING_SIZE for test:
    # StringSession uses urlsafe_b64decode(session_string + "=" * (-len(session_string) % 4))
    # So, the raw string length doesn't directly map to STRING_SIZE or STRING_SIZE_64
    # The logic in `from_string` is: `if len(session_string) in [cls.STRING_SIZE, cls.STRING_SIZE_64]:`
    # This is incorrect. `len(session_string)` is the length of the *encoded* string.
    # `STRING_SIZE` is the length of the *decoded* string.
    # This test might expose this flaw or pass if my understanding of that check is wrong.

    # Let's assume the check `if len(session_string) in [cls.STRING_SIZE, cls.STRING_SIZE_64]`
    # was intended to be `if len(decoded_bytes) ...`
    # For now, let's craft the string and see. The from_string logic will try to unpack.
    # If api_id is None after from_string, it means it correctly parsed an old format.

    old_session_str = base64.urlsafe_b64encode(packed_data).decode().rstrip("=")

    session = PyroSession.from_string(old_session_str)

    assert session.dc_id == pyro_user_session_data["dc_id"]
    assert session.auth_key == pyro_user_session_data["auth_key"]
    assert session.user_id == pyro_user_session_data["user_id"]
    assert session.is_bot == pyro_user_session_data["is_bot"]
    assert session.test_mode == pyro_user_session_data["test_mode"]
    assert session.api_id is None # Key check for old format

@pytest.mark.asyncio
async def test_pyro_file_read_write_user(pyro_user_session_data, tmp_path):
    session_file = tmp_path / "test_user.session"
    original_session = PyroSession(**pyro_user_session_data)

    await original_session.to_file(session_file)
    assert os.path.exists(session_file)

    new_session = await PyroSession.from_file(session_file)

    assert new_session.dc_id == original_session.dc_id
    assert new_session.api_id == original_session.api_id
    assert new_session.auth_key == original_session.auth_key
    assert new_session.user_id == original_session.user_id
    assert new_session.is_bot == original_session.is_bot
    assert new_session.test_mode == original_session.test_mode
    # Date is written by to_file, so it will exist. We don't need to check its exact value here,
    # just that the other fields are preserved.

@pytest.mark.asyncio
async def test_pyro_from_invalid_file(tmp_path):
    invalid_file = tmp_path / "invalid.session"
    invalid_file.write_text("this is not a database")

    with pytest.raises(ValidationError):
        await PyroSession.from_file(invalid_file)

# TODO: Add tests for the STRING_SIZE/STRING_SIZE_64 logic in from_string if it proves problematic.
# The current from_string logic for choosing format based on *encoded* string length seems suspicious.
# For example, `base64.urlsafe_b64decode(session_string + "=" * (-len(session_string) % 4))`
# The length of `session_string` (encoded) isn't fixed for a given struct.
# `struct.calcsize(PyroSession.OLD_STRING_FORMAT)` is 263. `struct.calcsize(PyroSession.OLD_STRING_FORMAT_64)` is 267.
# `struct.calcsize(PyroSession.STRING_FORMAT)` is 271.
# The check `if len(session_string) in [cls.STRING_SIZE, cls.STRING_SIZE_64]:` where STRING_SIZE = 351
# is almost certainly a bug. It should be checking length of decoded bytes or a different heuristic.
# However, the test `test_pyro_from_old_string_format_no_api_id` will pass if the fallback path (the `else` in `from_string`)
# correctly unpacks the current `STRING_FORMAT` and the old one by luck or if the old format string
# doesn't hit those specific encoded lengths.

# For now, the existing tests cover the main to_string/from_string and to_file/from_file paths.
# The old format test relies on the current string not matching those specific encoded lengths.
# A more robust test for old formats would require knowing what those encoded lengths (351, 356) actually correspond to.
# Pyrogram's own historical session string formats might be needed for that.
# Given Pyrogram is unmaintained, focusing on current format compatibility is higher priority.
# The `api_id is None` check in `test_pyro_from_old_string_format_no_api_id` is the most important part of that test.
# If `from_string` fails to parse it, or parses it into the new format incorrectly, that assertion would fail.
# The fact that `api_id` is `None` when unpacking an old format implies that the `api_id = None` line in `from_string` (old path) is hit.
# `dc_id, test_mode, auth_key, user_id, is_bot = struct.unpack(...)`
# `api_id = None` (this is for the old format path)

# Let's refine the old string format test to be more direct about checking the parsing path.
# To do this, we'd need to know an encoded string length that *does* fall into STRING_SIZE or STRING_SIZE_64.
# This is hard to fabricate without knowing what those specific strings were.
# The current test for old format is okay as a basic check.
# If it fails, it implies the string was parsed as a "new" format string.
# If it passes, it implies it was parsed as an "old" format string (api_id=None).
# The `STRING_FORMAT` (new) has api_id at the second position: `>BI?...`
# The `OLD_STRING_FORMAT` has test_mode at the second position: `>B?...`
# If an old string (no api_id) is parsed via the new format, `test_mode` (a bool, 0 or 1) would be read as `api_id`.
# This would make `session.api_id` either 0 or 1.
# So, if `session.api_id is None`, it strongly suggests the old path was taken.

# The current `test_pyro_from_old_string_format_no_api_id` should correctly verify this.

# Final check of the from_string logic:
# if len(session_string) == 351: -> uses OLD_STRING_FORMAT (api_id = None)
# if len(session_string) == 356: -> uses OLD_STRING_FORMAT_64 (api_id = None)
# else: -> uses STRING_FORMAT (api_id is parsed)

# So, if we provide a string that is NOT 351 or 356 chars long (after b64 encoding & stripping '='),
# it will be parsed by STRING_FORMAT.
# The `test_pyro_from_old_string_format_no_api_id` creates a string from OLD_STRING_FORMAT.
# We need to check its encoded length.
# `packed_data` is 263 bytes. `base64.urlsafe_b64encode(packed_data).decode().rstrip("=")`
# `len(base64.urlsafe_b64encode(b'a'*263).decode().rstrip('='))` is 351.
# So this WILL hit the `len(session_string) == cls.STRING_SIZE` path.
# This means `api_id` will be set to `None` explicitly by that path. Test is correct.

# What if we make one for OLD_STRING_FORMAT_64?
# `packed_data_64 = struct.pack(PyroSession.OLD_STRING_FORMAT_64, ...)`
# `len(struct.pack(">B?256sQ?", False, False, b'a'*256, 123, False))` is 267 bytes.
# `len(base64.urlsafe_b64encode(b'a'*267).decode().rstrip('='))` is 356.
# This also hits the correct path.
# So the length check, while looking odd, seems to be functional for these specific known old formats.

# One final thought: what if api_id is explicitly None in a "new" style session?
# `PyroSession(dc_id=..., api_id=None, ...).to_string()` will result in `api_id=0` in the string.
# `PyroSession.from_string(...)` will then parse this as `api_id=0`.
# This is consistent.
# The `assert new_session.api_id == (original_session.api_id or 0)` covers this.
