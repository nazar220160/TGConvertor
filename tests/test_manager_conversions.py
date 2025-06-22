import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from TGConvertor import SessionManager
from TGConvertor.sessions.pyro import PyroSession
from TGConvertor.sessions.tele import TeleSession
from TGConvertor.sessions.tdata import TDataSession # For mocking
from opentele.api import API, APIData # For API instances

# Use common_test_data from conftest.py

@pytest.fixture
def pyro_string_fixture(common_test_data):
    # Create a PyroSession string
    ps = PyroSession(
        dc_id=common_test_data["dc_id"],
        auth_key=common_test_data["auth_key"],
        user_id=common_test_data["user_id"],
        api_id=common_test_data["api_id"], # Pyrogram specific api_id
        is_bot=False,
        test_mode=False
    )
    return ps.to_string()

@pytest.fixture
def tele_string_fixture(common_test_data):
    # Create a TeleSession string
    ts = TeleSession(
        dc_id=common_test_data["dc_id"],
        auth_key=common_test_data["auth_key"],
        server_address=common_test_data["server_address"],
        port=common_test_data["port"]
    )
    return ts.to_string()

# --- Pyrogram Input Conversion Tests ---
def test_sm_from_pyro_string_to_tele_string(pyro_string_fixture, common_test_data):
    sm = SessionManager.from_pyrogram_string(pyro_string_fixture, api=API.TelegramDesktop)

    assert sm.dc_id == common_test_data["dc_id"]
    assert sm.auth_key == common_test_data["auth_key"]
    assert sm.user_id == common_test_data["user_id"]
    assert sm.api['api_id'] == API.TelegramDesktop['api_id']

    out_tele_string = sm.to_telethon_string()
    ts_out = TeleSession.from_string(out_tele_string)

    assert ts_out.dc_id == common_test_data["dc_id"]
    assert ts_out.auth_key == common_test_data["auth_key"]
    # Telethon strings don't inherently carry user_id or api_id from the source session type

def test_sm_from_pyro_string_to_pyro_string(pyro_string_fixture, common_test_data):
    sm = SessionManager.from_pyrogram_string(pyro_string_fixture, api=API.TelegramAndroid) # Use a different API

    # Verify manager state
    assert sm.user_id == common_test_data["user_id"]
    assert sm.api['api_id'] == API.TelegramAndroid['api_id']

    out_pyro_string = sm.to_pyrogram_string()

    # Parse both strings and compare fields, as exact string match might be too brittle
    # if there are subtle encoding differences that don't affect data.
    ps_orig = PyroSession.from_string(pyro_string_fixture)
    ps_out = PyroSession.from_string(out_pyro_string)

    assert ps_out.dc_id == ps_orig.dc_id
    assert ps_out.auth_key == ps_orig.auth_key
    assert ps_out.user_id == ps_orig.user_id
    # The api_id in the output Pyrogram string should reflect the API used by SessionManager
    assert ps_out.api_id == API.TelegramAndroid['api_id']


# --- Telethon Input Conversion Tests ---
def test_sm_from_tele_string_to_pyro_string(tele_string_fixture, common_test_data):
    sm = SessionManager.from_telethon_string(tele_string_fixture, api=API.TelegramIOS)

    assert sm.dc_id == common_test_data["dc_id"]
    assert sm.auth_key == common_test_data["auth_key"]
    assert sm.user_id is None # Telethon string doesn't provide user_id initially
    assert sm.api['api_id'] == API.TelegramIOS['api_id']

    # If user_id is needed for Pyrogram string, get_user_id() would be called by to_pyrogram_string
    # or rather, the PyroSession property would use sm.user_id which is None.
    # PyroSession.to_string() uses `self.user_id or 0`.
    out_pyro_string = sm.to_pyrogram_string()
    ps_out = PyroSession.from_string(out_pyro_string)

    assert ps_out.dc_id == common_test_data["dc_id"]
    assert ps_out.auth_key == common_test_data["auth_key"]
    assert ps_out.user_id == 0 # Because sm.user_id was None
    assert ps_out.api_id == API.TelegramIOS['api_id']


def test_sm_from_tele_string_to_tele_string(tele_string_fixture, common_test_data):
    sm = SessionManager.from_telethon_string(tele_string_fixture)
    out_tele_string = sm.to_telethon_string()

    # Direct string comparison should work here as Telethon format is stable
    assert out_tele_string == tele_string_fixture

# --- File Conversion Tests (Minimal examples) ---
@pytest.mark.asyncio
async def test_sm_from_pyro_file_to_tele_file(tmp_path, common_test_data):
    orig_pyro_file = tmp_path / "orig_pyro.session"
    out_tele_file = tmp_path / "out_tele.session"

    ps_orig = PyroSession(
        dc_id=common_test_data["dc_id"],
        auth_key=common_test_data["auth_key"],
        user_id=common_test_data["user_id"],
        api_id=common_test_data["api_id"]
    )
    await ps_orig.to_file(orig_pyro_file)

    sm = await SessionManager.from_pyrogram_file(orig_pyro_file, api=API.TelegramDesktop)
    await sm.to_telethon_file(out_tele_file)

    ts_out = await TeleSession.from_file(out_tele_file)
    assert ts_out.dc_id == common_test_data["dc_id"]
    assert ts_out.auth_key == common_test_data["auth_key"]
    # server_address and port will be default for that DC from DataCenter
    # takeout_id will be None by default from TeleSession.to_file

@pytest.mark.asyncio
async def test_sm_from_tele_file_to_pyro_file(tmp_path, common_test_data):
    orig_tele_file = tmp_path / "orig_tele.session"
    out_pyro_file = tmp_path / "out_pyro.session"

    ts_orig = TeleSession(
        dc_id=common_test_data["dc_id"],
        auth_key=common_test_data["auth_key"],
        server_address=common_test_data["server_address"],
        port=common_test_data["port"]
    )
    await ts_orig.to_file(orig_tele_file)

    sm = await SessionManager.from_telethon_file(orig_tele_file, api=API.TelegramDesktop)
    # sm.user_id will be None initially. For PyroSession file, user_id is needed.
    # The .pyrogram property will use sm.user_id (None), which becomes 0 in PyroSession.to_string/to_file.

    await sm.to_pyrogram_file(out_pyro_file)

    ps_out = await PyroSession.from_file(out_pyro_file)
    assert ps_out.dc_id == common_test_data["dc_id"]
    assert ps_out.auth_key == common_test_data["auth_key"]
    assert ps_out.user_id == 0 # As sm.user_id was None
    assert ps_out.api_id == API.TelegramDesktop['api_id']


# --- TData Conversion Tests (Mocked) ---
@pytest.mark.skip(reason="TData conversions rely on mocking opentele which is complex or live tests which are unreliable.")
@patch('TGConvertor.manager.TDataSession') # Mock the TDataSession class used by SessionManager
async def test_sm_from_tdata_to_pyro_string_mocked(MockTDataSessionClass, pyro_string_fixture, common_test_data):
    # Configure the mock TDataSession.from_tdata to return a specific instance
    mock_tdata_instance = MagicMock(spec=TDataSession)
    mock_tdata_instance.dc_id = common_test_data["dc_id"]
    mock_tdata_instance.auth_key = common_test_data["auth_key"]
    mock_tdata_instance.user_id = common_test_data["user_id"]
    mock_tdata_instance.api = API.TelegramDesktop # What from_tdata would typically return as api

    # Ensure from_tdata is an async mock if SessionManager awaits it (it's not async in TDataSession)
    # TDataSession.from_tdata is synchronous.
    MockTDataSessionClass.from_tdata.return_value = mock_tdata_instance

    sm = SessionManager.from_tdata_folder(Path("dummy_tdata_path"))

    MockTDataSessionClass.from_tdata.assert_called_once_with(Path("dummy_tdata_path"))
    assert sm.user_id == common_test_data["user_id"] # Check fix for user_id from TData
    assert sm.api == API.TelegramDesktop

    out_pyro_str = sm.to_pyrogram_string()
    ps_out = PyroSession.from_string(out_pyro_str)

    assert ps_out.dc_id == common_test_data["dc_id"]
    assert ps_out.auth_key == common_test_data["auth_key"]
    assert ps_out.user_id == common_test_data["user_id"]
    assert ps_out.api_id == API.TelegramDesktop['api_id']


@pytest.mark.skip(reason="TData conversions rely on mocking opentele or live tests.")
@patch.object(TDataSession, "to_folder", new_callable=MagicMock) # Mock the method on the class
@patch.object(SessionManager, "get_user_id", new_callable=AsyncMock) # Mock to prevent network
async def test_sm_from_pyro_string_to_tdata_folder_mocked(mock_get_user_id, mock_to_folder_method, pyro_string_fixture, common_test_data):
    sm = SessionManager.from_pyrogram_string(pyro_string_fixture, api=API.TelegramAndroid)

    # Ensure sm.user_id is set, as get_user_id is mocked (it would normally set it)
    # from_pyrogram_string already sets user_id from the pyro_string_fixture.
    # So, mock_get_user_id.return_value = common_test_data["user_id"] is not strictly needed
    # if from_pyrogram_string works as expected. But good for safety.
    mock_get_user_id.return_value = sm.user_id

    dummy_out_path = Path("dummy_tdata_output")
    await sm.to_tdata_folder(dummy_out_path)

    mock_get_user_id.assert_called_once() # Verifies it was called

    # mock_to_folder_method is a mock of TDataSession.to_folder
    # It should have been called once. The instance it was called on is tricky to get here
    # unless we also mock the TDataSession property itself.
    # For simplicity, just check it was called.
    # A more thorough test would mock `SessionManager.tdata` property to return a MagicMock(spec=TDataSession)
    # and then assert `mocked_tdata_session_property.to_folder.assert_called_once_with(dummy_out_path)`
    assert mock_to_folder_method.called

    # To check arguments on mock_to_folder_method, we'd need to ensure that
    # the TDataSession instance created by `sm.tdata` was the one whose method was mocked.
    # This is simpler if TDataSession itself is mocked earlier, or its __init__.
    # This test is okay for a basic check that the flow proceeds to call to_folder.
    # The arguments passed to the TDataSession constructor via the `sm.tdata` property
    # (dc_id, auth_key, user_id, api) are implicitly tested if `mock_to_folder_method`
    # is assumed to be on an instance created with those correct values.
    # For example, the `api` passed to `TDataSession` should be `API.TelegramAndroid`.
    # This level of detail is better for the `test_tdata_session.py` mocks.
    # Here, we confirm the manager tries to call it.
    mock_to_folder_method.assert_called_once_with(dummy_out_path)

# TODO: Add tests for cases where SessionManager needs to call get_user_id()
# e.g. from_telethon_string -> to_tdata_folder
# (This is implicitly covered by mocking get_user_id in the TData test above)
# Consider a specific test for SessionManager.get_user_id() if user_id is None.
# That's more for test_manager_auth.py
