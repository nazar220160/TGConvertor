<img src="https://cdn4.iconfinder.com/data/icons/social-media-and-logos-12/32/Logo_telegram_Airplane_Air_plane_paper_airplane-33-256.png" align="right" width="131" />

# TGConvertor

[![PyPI Version](https://img.shields.io/pypi/v/TGConvertor)](https://pypi.org/project/TGConvertor/)
[![License](https://img.shields.io/pypi/l/TGConvertor)](https://github.com/nazar220160/TGConvertor/blob/master/LICENSE)
<!-- Add other badges if available, e.g., build status, downloads -->

TGConvertor is a utility for converting Telegram session files and strings between different formats, including Telethon, Pyrogram, and TData (Telegram Desktop).

<hr/>

## Important Notice - Library Status

*   **TData Conversions:** The underlying library (`opentele`) used for TData conversions is currently **unmaintained**. This means that conversions involving TData formats may be unreliable or may not work correctly with recent versions of Telegram Desktop. Use TData conversion features with caution.
*   **Pyrogram Support:** The Pyrogram library itself is also **unmaintained** as of its v2.0 release. While TGConvertor aims to support Pyrogram v2.0 session formats, future compatibility is not guaranteed.
*   **Telethon Support:** TGConvertor has been updated to use Telethon's recommended methods for handling `.session` files, improving reliability for Telethon conversions.

## Installation

```bash
pip install TGConvertor
```

## Usage

TGConvertor can be used as a Python library or as a command-line interface (CLI) tool.

### As a Library

The core functionality is provided by the `SessionManager` class.

```python
from TGConvertor import SessionManager
from opentele.api import API # For specifying custom API credentials

# Example: Convert a Pyrogram session string to a Telethon session string
pyro_session_string = "your_pyrogram_session_string_here"
manager = SessionManager.from_pyrogram_string(pyro_session_string)
telethon_session_string = manager.to_telethon_string()
print(telethon_session_string)

# Example: Convert a Telethon file to a Pyrogram file
# manager = await SessionManager.from_telethon_file("my_telethon.session")
# await manager.to_pyrogram_file("my_pyrogram.session")

# Example: Using a custom API (e.g., for Android)
# my_api = API.Custom(api_id=12345, api_hash="your_api_hash")
# manager_with_custom_api = SessionManager.from_pyrogram_string(pyro_session_string, api=my_api)
```

Refer to the source code for `SessionManager` for all available `from_...` and `to_...` methods.

### As a CLI Tool

TGConvertor provides a command-line interface for quick conversions.

```bash
tgconvertor <input_type> <input_value> <output_type> [output_location] [--api_id ID] [--api_hash HASH]
```

**Arguments:**

*   `input_type`: Type of the input session.
    *   Choices: `pyro_str`, `pyro_file`, `tele_str`, `tele_file`, `tdata_folder`
*   `input_value`: The session string itself, or the path to the session file/folder.
*   `output_type`: Desired type for the output session.
    *   Choices: `pyro_str`, `pyro_file`, `tele_str`, `tele_file`, `tdata_folder`
*   `output_location` (optional):
    *   Path to save the output file or folder.
    *   If `output_type` is a string format (e.g., `pyro_str`, `tele_str`) and `output_location` is omitted or set to `stdout`, the session string will be printed to the standard output.
    *   Required if `output_type` is a file or folder format.
*   `--api_id ID` (optional): Custom API ID to use for the session.
*   `--api_hash HASH` (optional): Custom API Hash to use with the custom API ID.

**CLI Examples:**

1.  Convert a Pyrogram string to a Telethon session file:
    ```bash
    tgconvertor pyro_str "your_pyrogram_string" tele_file my_telethon.session
    ```

2.  Convert a Telethon file to a Pyrogram string and print to console:
    ```bash
    tgconvertor tele_file path/to/my.session pyro_str stdout
    # or simply:
    # tgconvertor tele_file path/to/my.session pyro_str
    ```

3.  Convert a TData folder to a Pyrogram session file using custom API credentials:
    ```bash
    tgconvertor tdata_folder /path/to/TelegramDesktop/tdata pyro_file output.session --api_id 12345 --api_hash yourhash
    ```
    *(Note: TData conversion reliability is limited, see "Important Notice" above.)*


## How it Works (Library)

An authorization session consists of an authorization key (auth_key), data center ID (DC ID), and other parameters like User ID and API credentials. TGConvertor extracts these essential details from the source session and re-packages them into the target format. For file-based sessions, it attempts to replicate the expected structure for each library.

## Contributing

Contributions, issues, and feature requests are welcome. Please check the open issues or open a new one to discuss potential changes. Given the status of underlying libraries like `opentele` and `Pyrogram`, contributions related to improving TData or ensuring robust Pyrogram compatibility would require careful consideration.

## Donate

If you find this tool useful, consider donating:

**USDT (BEP20):** `0x34412717daaf427efa39c8508db4f62cce0d6d48`
