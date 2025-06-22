import pytest
import os
from pathlib import Path
from TGConvertor.sessions.tele import TeleSession
from TGConvertor.exceptions import ValidationError

# Test data
TEST_DC_ID = 2
TEST_AUTH_KEY = b'b' * 256  # Must be 256 bytes
TEST_SERVER_ADDRESS = "149.154.167.91" # Example DC IP
TEST_PORT = 443
TEST_TAKEOUT_ID = 12345 # Example takeout ID

# Note: user_id and phone_number are not part of TeleSession's core string/file data
# They are typically obtained via client.get_me() and stored by SessionManager or live client.

@pytest.fixture
def tele_session_data():
    return {
        "dc_id": TEST_DC_ID,
        "auth_key": TEST_AUTH_KEY,
        "server_address": TEST_SERVER_ADDRESS,
        "port": TEST_PORT,
        "takeout_id": TEST_TAKEOUT_ID
        # user_id and phone_number are intentionally omitted here
        # as TeleSession init defaults them to None and they are not in string/core file session
    }

def test_tele_session_creation(tele_session_data):
    session = TeleSession(**tele_session_data)
    assert session.dc_id == tele_session_data["dc_id"]
    assert session.auth_key == tele_session_data["auth_key"]
    assert session.server_address == tele_session_data["server_address"]
    assert session.port == tele_session_data["port"]
    assert session.takeout_id == tele_session_data["takeout_id"]
    assert session.user_id is None
    assert session.phone_number is None

def test_tele_string_to_tele_string(tele_session_data):
    original_session = TeleSession(**tele_session_data)
    session_str = original_session.to_string()

    new_session = TeleSession.from_string(session_str)

    assert new_session.dc_id == original_session.dc_id
    assert new_session.auth_key == original_session.auth_key
    assert new_session.server_address == original_session.server_address
    assert new_session.port == original_session.port
    # takeout_id is not part of the string session format for Telethon
    assert new_session.takeout_id is None

def test_tele_string_default_dc_info(tele_session_data):
    # Create session without server_address and port, to_string should populate them
    data_minimal = {
        "dc_id": tele_session_data["dc_id"],
        "auth_key": tele_session_data["auth_key"]
    }
    session = TeleSession(**data_minimal)
    session_str = session.to_string() # This will call DataCenter to get default IP/port

    assert session.server_address is not None
    assert session.port is not None

    new_session = TeleSession.from_string(session_str)
    assert new_session.dc_id == data_minimal["dc_id"]
    assert new_session.auth_key == data_minimal["auth_key"]
    assert new_session.server_address == session.server_address # Should match the populated one
    assert new_session.port == session.port


@pytest.mark.asyncio
async def test_tele_file_read_write(tele_session_data, tmp_path):
    session_file = tmp_path / "test_tele.session"
    original_session = TeleSession(**tele_session_data)

    # Ensure server_address and port are set before to_file, as to_file now expects them
    # (though it has a fallback, good to be explicit for test)
    if original_session.server_address is None or original_session.port is None:
         original_session.to_string() # This populates server_address and port as a side effect

    await original_session.to_file(session_file)
    assert os.path.exists(session_file)

    new_session = await TeleSession.from_file(session_file)

    assert new_session.dc_id == original_session.dc_id
    assert new_session.auth_key == original_session.auth_key
    assert new_session.server_address == original_session.server_address
    assert new_session.port == original_session.port
    assert new_session.takeout_id == original_session.takeout_id # takeout_id is in SQLiteSession

    # user_id and phone_number should be None as per new from_file logic
    assert new_session.user_id is None
    assert new_session.phone_number is None


@pytest.mark.asyncio
async def test_tele_from_empty_file(tmp_path):
    empty_file = tmp_path / "empty.session"
    # Create an empty SQLite file, or a file that SQLiteSession would consider invalid/empty
    from telethon.sessions.sqlite import SQLiteSession
    empty_db = SQLiteSession(str(empty_file))
    empty_db.save() # Creates the schema but no session data

    with pytest.raises(ValidationError, match="might be empty or invalid (no auth_key)"):
        await TeleSession.from_file(empty_file)

@pytest.mark.asyncio
async def test_tele_from_non_db_file(tmp_path):
    invalid_file = tmp_path / "invalid.session"
    invalid_file.write_text("this is not a database")

    # This should raise an error from within Telethon's SQLiteSession,
    # likely a sqlite3.DatabaseError or similar, which from_file might not catch as ValidationError.
    # Let's see what Telethon's SQLiteSession does.
    # Accessing a property like .auth_key on a non-db file will trigger its _load()
    # which will fail to connect or query.
    # The ValidationError is raised if auth_key is None after attempting to load.
    # If telethon raises DatabaseError earlier, that's also a valid failure.
    with pytest.raises(Exception): # More general to catch underlying DB error too
        await TeleSession.from_file(invalid_file)

# Test that takeout_id=None is handled correctly in to_file/from_file
@pytest.mark.asyncio
async def test_tele_file_read_write_no_takeout(tele_session_data, tmp_path):
    session_file = tmp_path / "test_tele_no_takeout.session"
    data_no_takeout = tele_session_data.copy()
    data_no_takeout["takeout_id"] = None
    original_session = TeleSession(**data_no_takeout)

    if original_session.server_address is None or original_session.port is None:
         original_session.to_string()

    await original_session.to_file(session_file)
    assert os.path.exists(session_file)

    new_session = await TeleSession.from_file(session_file)

    assert new_session.dc_id == original_session.dc_id
    assert new_session.auth_key == original_session.auth_key
    assert new_session.server_address == original_session.server_address
    assert new_session.port == original_session.port
    assert new_session.takeout_id is None # Should be None
    assert new_session.user_id is None
    assert new_session.phone_number is None
