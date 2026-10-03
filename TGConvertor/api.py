"""Client configuration. Prefer your own credentials for network operations."""

from dataclasses import dataclass, field, replace


@dataclass
class APIData:
    api_id: int
    api_hash: str = field(repr=False)
    device_model: str = "Desktop"
    system_version: str = "Unknown"
    app_version: str = "0.2.0"
    lang_code: str = "en"
    system_lang_code: str = "en-US"

    def __post_init__(self):
        if type(self.api_id) is not int or not 0 < self.api_id < 2**32:
            raise ValueError("api_id must be a positive unsigned 32-bit integer")
        if not isinstance(self.api_hash, str) or not self.api_hash:
            raise ValueError("api_hash must be a non-empty string")

    def copy(self):
        return replace(self)


class API:
    """Compatibility presets matching OpenTele's published Telegram API identities."""

    TelegramDesktop = APIData(
        2040, "b18441a1ff607e10a989891a5462e627", "Desktop", "Windows 10", "4.16.8"
    )
    TelegramAndroid = APIData(6, "eb06d4abfb49dc3eeb1aeb98ae0f581e", "Android", "SDK 23", "8.4.1")
    TelegramIOS = APIData(8, "7245de8e747a0d6fbe11f7cc14fcc0bb", "iPhone", "iOS 15.0", "8.4")
    TelegramMacOS = APIData(2834, "68875f756c9b437a8b916ca3de215815", "Mac", "macOS 12.0", "8.4")
