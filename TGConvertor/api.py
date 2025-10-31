"""
Telegram API configurations for different platforms.
Replaces opentele.api functionality.
"""


class APIData:
    """Telegram API data class for client configuration."""
    
    def __init__(
        self,
        api_id: int,
        api_hash: str,
        device_model: str,
        system_version: str,
        app_version: str,
        lang_code: str = "en",
        system_lang_code: str = "en-US",
    ):
        self.api_id = api_id
        self.api_hash = api_hash
        self.device_model = device_model
        self.system_version = system_version
        self.app_version = app_version
        self.lang_code = lang_code
        self.system_lang_code = system_lang_code
    
    def copy(self):
        """Create a copy of this APIData instance."""
        return APIData(
            api_id=self.api_id,
            api_hash=self.api_hash,
            device_model=self.device_model,
            system_version=self.system_version,
            app_version=self.app_version,
            lang_code=self.lang_code,
            system_lang_code=self.system_lang_code,
        )


class API:
    """Telegram API configurations for different platforms."""
    
    # Telegram Desktop
    TelegramDesktop = APIData(
        api_id=17349,
        api_hash="344583e45741c457fe1862106095a5eb",
        device_model="Desktop",
        system_version="Windows 10",
        app_version="4.8.0",
        lang_code="en",
        system_lang_code="en-US",
    )
    
    # Telegram Android
    TelegramAndroid = APIData(
        api_id=4,
        api_hash="014b35b6184100b085b0d0572f9b5103",
        device_model="Android",
        system_version="SDK 23",
        app_version="9.7.0",
        lang_code="en",
        system_lang_code="en-US",
    )
    
    # Telegram iOS
    TelegramIOS = APIData(
        api_id=8,
        api_hash="7245de8e747a0d6fbe11f7cc14fcc0bb",
        device_model="iPhone",
        system_version="iOS 15.0",
        app_version="9.7.0",
        lang_code="en",
        system_lang_code="en-US",
    )
    
    # Telegram macOS
    TelegramMacOS = APIData(
        api_id=946,
        api_hash="5f3fb04eac560c6a3d7dd5cacb85e8b0",
        device_model="Mac",
        system_version="macOS 12.0",
        app_version="9.7.0",
        lang_code="en",
        system_lang_code="en-US",
    )

