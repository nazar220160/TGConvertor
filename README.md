<img src="https://cdn4.iconfinder.com/data/icons/social-media-and-logos-12/32/Logo_telegram_Airplane_Air_plane_paper_airplane-33-256.png" align="right" width="131" />

# TGConvertor

![PyPI](https://img.shields.io/pypi/v/TGSessionsConverter)
![PyPI - License](https://img.shields.io/pypi/l/TGSessionsConverter)

This module is small util for easy converting Telegram sessions to various formats (Telethon, Pyrogram, Tdata)
<hr/>

## Installation

```
$ pip install TGConvertor
```

## Quickstart

```python
from TGConvertor import SessionManager

session = SessionManager.from_pyrogram_string('session_str')
print(session.to_pyrogram_string())
```

### How it works

> An authorization session consists of an authorization key and some additional data required to connect. The module
> simply extracts this data and creates an instance of TelegramSession based on it, the methods of which are convenient to
> use to convert to the format you need.
