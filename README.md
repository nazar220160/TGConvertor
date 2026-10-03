# TGConvertor

[![CI](https://github.com/nazar220160/TGConvertor/actions/workflows/ci.yml/badge.svg)](https://github.com/nazar220160/TGConvertor/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/tgconvertor)](https://pypi.org/project/tgconvertor/)
[![Python](https://img.shields.io/pypi/pyversions/tgconvertor)](https://pypi.org/project/tgconvertor/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/nazar220160/TGConvertor/blob/master/LICENSE)

Convert Telegram authorizations between **Telethon**, **Pyrogram / Kurigram**, and **Telegram Desktop tdata**. File reads and conversions are offline. Telegram clients are optional and only needed for explicit network operations.

> Session files and strings grant access to an account. Keep them private, use only accounts you own or are authorized to manage, and never commit them or paste them into issue reports.

## Installation

Requires **Python 3.10+**. CI tests Python **3.10–3.14**, with additional Windows and macOS checks.

```bash
python -m pip install --upgrade tgconvertor
```

The base package converts Telethon and Pyrogram/Kurigram files and strings without either client installed. Install extras only for the features you need:

```bash
python -m pip install --upgrade 'tgconvertor[telethon]'  # Telethon client / network validation
python -m pip install --upgrade 'tgconvertor[kurigram]'  # Kurigram client
python -m pip install --upgrade 'tgconvertor[pyrogram]'  # Legacy Pyrogram 2 client
python -m pip install --upgrade 'tgconvertor[tdata]'     # tdata via OpenTele2 (no PyQt5)
```

Telethon and Kurigram can be installed together: `pip install 'tgconvertor[telethon,kurigram,tdata]'`.
**Do not install Pyrogram and Kurigram together**: both provide the `pyrogram` import namespace. Use separate virtual environments when testing both.

## Quick start

```bash
# Pyrogram or Kurigram file → Telethon file
# Choose a new output path; existing files/directories are never overwritten.
tgconvertor convert original.session -f pyrogram -t telethon -o converted.session

# File → string (only the string is written to stdout)
tgconvertor convert original.session -f pyrogram -t telethon > converted-string.txt

# String → file, without putting the authorization in shell history
cat private-session-string.txt | tgconvertor convert - -f pyrogram -t telethon -o converted.session

# Inspect local metadata without connecting to Telegram or displaying the key
tgconvertor info original.session -f pyrogram

tgconvertor --help
tgconvertor convert --help
tgconvertor list-formats
python -m TGConvertor --version
```

`--output string` also selects stdout. Omitting `--output` never writes over the input. Diagnostics and file-save messages go to stderr. `--input-type file` or `--input-type string` overrides automatic detection, including for unusual filenames.

### Telethon → Pyrogram / Kurigram

Telethon strings and SQLite files do **not** reliably store the owner's user ID. A cached contact is not the owner. Supply the real ID explicitly:

```bash
tgconvertor convert telethon.session -f telethon -t pyrogram \
  --user-id 123456789 -o kurigram.session --backend kurigram
```

`--backend pyrogram` writes Pyrogram 2's SQLite schema. `--backend kurigram` writes Kurigram's schema. The default `auto` selects the installed client; with neither installed, it writes Pyrogram 2's schema. Both use the same current string-session format. Reading either schema never requires the corresponding client.

Pyrogram output preserves a source Pyrogram API ID. Sources without an API ID use the selected API configuration (Desktop compatibility preset by default). For a custom application, set both `TGCONVERTOR_API_ID` and `TGCONVERTOR_API_HASH` in your environment, or pass `APIData` through the Python API. Obtain your application credentials from [my.telegram.org](https://my.telegram.org).

### Telegram Desktop tdata

Install the `tdata` extra. Pass the **actual tdata directory**, not its parent:

```bash
# tdata already contains the owner ID
tgconvertor convert ./desktop/tdata -f tdata -t pyrogram -o account.session

# Writes directly into ./export/tdata, without adding another tdata level
tgconvertor convert account.session -f pyrogram -t tdata -o ./export/tdata

# Choose another account from a multi-account directory (zero-based loaded-account index)
tgconvertor convert ./desktop/tdata -f tdata -t telethon --account-index 1 -o second.session
```

The main account is selected by default. For directories protected by a local passcode, set `TGCONVERTOR_TDATA_PASSCODE` for input and `TGCONVERTOR_OUTPUT_PASSCODE` for output. These are **local Desktop passcodes**, not your Telegram two-step verification password. The current adapter supports ASCII passcodes.

Export to tdata requires the real user ID and a production user account; bots and Telegram test-server sessions are rejected. Each export uses a fresh local encryption key. Converting a Telethon source to tdata also requires `--user-id`.

## Python API

### One-call conversion

```python
import asyncio
from TGConvertor import convert


async def main():
    output = await convert("original.session", "pyrogram", "telethon", "converted.session")
    print(f"Saved to {output}")


asyncio.run(main())
```

`convert(source, from_format, to_format, output=None, *, user_id=None, api=..., input_type="auto", backend="auto", passcode="", output_passcode="", account_index=None)` returns a `Path` for file/directory output or a session string when `output` is omitted. tdata always requires an output path. This function never connects to Telegram.

### Work with a session

```python
import asyncio
from TGConvertor import SessionManager


async def main():
    session = await SessionManager.from_pyrogram_file("original.session")
    await session.to_telethon_file("converted.session")
    await session.to_pyrogram_file("kurigram.session", backend="kurigram")
    await session.to_tdata_folder("export/tdata")  # requires the tdata extra


asyncio.run(main())
```

| Source | Loader |
| --- | --- |
| Telethon SQLite | `await SessionManager.from_telethon_file(path, api=...)` |
| Telethon string | `SessionManager.from_telethon_string(value, api=...)` |
| Pyrogram / Kurigram SQLite | `await SessionManager.from_pyrogram_file(path, api=...)` |
| Pyrogram / Kurigram string | `SessionManager.from_pyrogram_string(value, api=...)` |
| Desktop tdata | `SessionManager.from_tdata_folder(path, passcode="", account_index=None, api=...)` |

String exports are synchronous: `session.to_telethon_string()` and `session.to_pyrogram_string()`. File exports are asynchronous. The tdata loader is synchronous; use `await asyncio.to_thread(SessionManager.from_tdata_folder, path)` in an application where blocking the event loop matters.

### Explicit network validation and owner lookup

Install the `telethon` extra, then use your own API credentials:

```python
import asyncio
import os
from TGConvertor import APIData, SessionManager


async def main():
    api = APIData(
        api_id=int(os.environ["TGCONVERTOR_API_ID"]),
        api_hash=os.environ["TGCONVERTOR_API_HASH"],
    )
    session = await SessionManager.from_telethon_file("original.session", api=api)
    await session.get_user_id()  # explicit network request; caches the actual owner and bot flag
    await session.to_pyrogram_file("converted.session")


asyncio.run(main())
```

`await session.validate()` contacts Telegram and returns whether it can obtain the account. Connection/RPC errors propagate to the caller. Local `TeleSession.validate(path)` and `PyroSession.validate(path)` only check whether the local authorization can be parsed; they cannot prove it remains authorized on Telegram.

`session.telethon_client()` and `session.pyrogram_client()` create in-memory clients. Create and use them inside your asynchronous application, then disconnect them. `async with session as client:` connects a Telethon client and disconnects it on exit, including on errors. Conversion itself neither logs in nor creates a new Telegram authorization.

Compatibility presets remain available through `API.TelegramDesktop`, `API.TelegramAndroid`, `API.TelegramIOS`, and `API.TelegramMacOS`, or CLI `--api desktop|android|ios|macos`. They are fixed compatibility identities, not a promise to track the latest official client version.

## Supported formats and limits

| Format | Files | Strings | Notes |
| --- | --- | --- | --- |
| Telethon 1.x | SQLite authorization schema v7/v8 | Version 1, IPv4 and IPv6 | Stored endpoint, port and file takeout ID are retained |
| Pyrogram 2 | SQLite v3 (also reads the legacy schema without API ID) | Current format and legacy 32/64-bit user-ID formats | API ID, owner, bot flag and test mode are retained where representable |
| Kurigram 2 | SQLite v7 | Same session strings as Pyrogram | Select `backend="kurigram"` for Kurigram file output |
| Desktop tdata | Directory via OpenTele2 | — | One selected account; local ASCII passcodes supported |

The package converts **authorization data**, not a complete client backup. Entity/peer caches, usernames, update states, temporary keys, media-DC keys, and Desktop settings are not copied. Telethon strings cannot carry user IDs, bot flags, API IDs or takeout IDs; Pyrogram strings cannot carry custom server addresses. A conversion through those strings cannot retain the missing fields. Telethon 2's experimental session format is not supported.

Reading uses read-only SQLite connections and never migrates the input. Close the original client before copying or converting its database. Writers reject existing destinations and create private files (`0600`) and tdata directories (`0700`) on POSIX. SQLite output is published only after it is complete. Filesystem permissions on Windows follow the platform's ACLs.

Malformed/incomplete authorizations raise `ValidationError`; missing optional dependencies raise `MissingDependencyError`; missing input and existing output paths raise `FileNotFoundError` and `FileExistsError`. CLI failures return a non-zero exit code without a traceback or printing the supplied session string.

## Development and releases

See [CONTRIBUTING.md](https://github.com/nazar220160/TGConvertor/blob/master/CONTRIBUTING.md) for test commands, optional live verification, the CI matrix, and PyPI publishing setup. See [CHANGELOG.md](https://github.com/nazar220160/TGConvertor/blob/master/CHANGELOG.md) for migration from 0.1.x.

The offline suite uses synthetic authorizations and blocks outgoing network connections, including inside CLI subprocesses. It tests all 49 input/output representation combinations through `convert()`, `SessionManager`, the CLI, and the installed console command. CI verifies the base install, each extra independently, combined clients/tdata, lint/format checks, minimum CLI dependencies, package metadata, and installation of the built wheel. The publish workflow runs the same checks on the exact tagged commit before publishing the tested distributions. Live verification is a separate opt-in local test.

## Donate

**USDT (BEP20):** `0x34412717daaf427efa39c8508db4f62cce0d6d48`

## License

[MIT](https://github.com/nazar220160/TGConvertor/blob/master/LICENSE).
