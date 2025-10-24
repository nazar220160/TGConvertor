# TGConvertor <a href="https://pepy.tech/projects/tgconvertor"><img src="https://static.pepy.tech/personalized-badge/tgconvertor?period=total&units=NONE&left_color=BLACK&right_color=GREEN&left_text=downloads" align="right" alt="PyPI Downloads"></a>

<img src="public/images/poster.png" style="border-radius: 15px;" alt="poster">

This module is small util for easy converting Telegram sessions to various formats (Telethon, Pyrogram, Kurigram, Tdata)
<hr/>

## Installation


##### with Pyrogram support
```bash
$ pip install TGConvertor[pyrogram]
```
##### with Kurigram support
```bash
$ pip install TGConvertor[kurigram]
```
## Using CLI

After installation, you can use the `tgconvertor` command-line tool:

```bash
# Show help and available commands
tgconvertor --help

# List supported formats and API types
tgconvertor list-formats
```

### Converting Sessions

The main `convert` command supports various conversion scenarios:

```bash
# Convert from file to file
tgconvertor convert session.session -f telethon -t pyrogram -o new_session.session

# Convert from string to file
tgconvertor convert "1:AAFqwer..." -f telethon -t pyrogram -o session.session

# Convert from file to string
tgconvertor convert session.session -f telethon -t pyrogram -o string

# Convert from string to string
tgconvertor convert "1:AAFqwer..." -f telethon -t pyrogram -o string

# Convert from string to tdata
tgconvertor convert "1:AAFqwer..." -f telethon -t tdata -o tdata_folder

# Convert from tdata to string
tgconvertor convert tdata_folder/tdata -f tdata -t telethon -o string

# Use specific API type (desktop/android/ios/macos/web)
tgconvertor convert session.session -f telethon -t pyrogram --api android
```

### View Session Information

You can inspect session details using the `info` command:

```bash
# Show Telethon session info
tgconvertor info session.session -f telethon

# Show Pyrogram session info
tgconvertor info my_session.session -f pyrogram
```

### Supported Formats
- `telethon`: Telethon session files (.session)
- `pyrogram`: Pyrogram session files (.session)
- `tdata`: Telegram Desktop format (directory)

### API Types
- `desktop`: Telegram Desktop client (default)
- `android`: Telegram Android client
- `ios`: Telegram iOS client
- `macos`: Telegram macOS client
- `web`: Telegram Web client

## Quickstart (Python API)

```python
from TGConvertor import SessionManager

# Convert from string
session = SessionManager.from_pyrogram_string('session_str')
print(session.to_pyrogram_string())

# Convert from file
session = await SessionManager.from_telethon_file('session.session')
await session.to_pyrogram_file('new_session.session')
```

### How it works

> An authorization session consists of an authorization key and some additional data required to connect. The module
> simply extracts this data and creates an instance of TelegramSession based on it, the methods of which are convenient to
> use to convert to the format you need.

## Donate
**USDT (BEP20):** `0x34412717daaf427efa39c8508db4f62cce0d6d48`
