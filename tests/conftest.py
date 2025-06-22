import pytest

# Shared test data (can be expanded)
@pytest.fixture(scope="session")
def common_test_data():
    return {
        "dc_id": 2,
        "auth_key": b'c' * 256,
        "user_id": 112233445,
        "bot_user_id": 998877660,
        "api_id": 12345, # For Pyrogram specific api_id in session
        "default_api_id": 99999, # For manager's default API config
        "default_api_hash": "default_api_hash_string",
        "phone_number": "+15550001122",
        "server_address": "149.154.167.91", # Example DC IP for Telethon
        "port": 443, # Example port for Telethon
    }
