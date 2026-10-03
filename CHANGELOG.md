# Changelog

## 0.2.0 — 2026-10-03

### Added

- Offline one-call `convert()` API and public `API`, `APIData`, and exception exports.
- Python 3.10–3.14 compatibility checks, independently installed optional extras, Windows/macOS tests, minimum CLI dependency checks, and wheel/sdist validation.
- Regression tests and upstream client interoperability tests using synthetic authorizations; opt-in local live verification.
- All 49 representation-to-representation combinations through four public interfaces, including the installed CLI, protected tdata, bot/test profiles, and multi-account selection.
- Opt-in live conversion matrix authenticated directly by native Telethon, Pyrogram/Kurigram and OpenTele2 against Telegram, with source baseline checks, rate-limit handling and temporary authorization cleanup.
- CLI stdin input, explicit input type, owner ID, backend selection, tdata account selection, environment credentials/passcodes, and version output.
- Linting, formatting, coverage gate, Dependabot, and release tag/version verification.
- Publish only after checks pass, with Trusted Publishing or the existing `PYPI_TOKEN` fallback.

### Fixed

- Raise all dependency minimums to the current stable releases: Typer 0.27.2, Rich 15.0.0, Telethon 1.45.0, pytest 9.1.1, pytest-asyncio 1.4.0, pytest-cov 7.1.0, Ruff 0.16.10, build 1.6.1, Twine 7.0.0, and setuptools 84.0.0. Kurigram 2.2.26, OpenTele2 1.2.1, and legacy Pyrogram 2.0.106 are already current. CI bootstraps pip 26.2.1+.

- Base installation can read/write Telethon and Pyrogram/Kurigram authorizations without optional clients.
- Preserve Telethon endpoints (including IPv6), ports, test DCs, and file takeout IDs; accept additive SQLite schema columns including Telethon v8 temporary keys.
- Preserve tdata owner IDs. Do not mistake the first cached Telethon contact for the account owner.
- Validate authorization keys, data-center IDs, metadata and session strings; reject empty and ambiguous databases.
- Read source databases without writes or migrations. Refuse existing destinations and clean up failed exports.
- Consolidate Pyrogram/Kurigram codecs while accepting current and legacy formats independently of the installed client.
- Disconnect clients on errors and cache owner information after an explicit lookup.
- Replace the Python 3.13-incompatible OpenTele dependency with OpenTele2; disable its fixed local encryption key optimization.

### Migration from 0.1.x

- `tgconvertor convert` without `--output` now prints a string. File and directory destinations must be explicit and new; there is no overwrite flag.
- Pyrogram and tdata exports require a real owner `user_id`. Provide it explicitly, import a source that stores it, or explicitly call `await session.get_user_id()` with the Telethon extra installed. Fake IDs are no longer substituted and export never silently contacts Telegram.
- `to_tdata_folder(path)` writes directly into `path`, rather than appending `/tdata`. Pass `"export/tdata"` if that is the directory you want.
- `tgconvertor[tdata]` now installs OpenTele2. Importing the package no longer eagerly imports any client or tdata dependency.
- The Desktop compatibility API uses OpenTele's published Desktop identity (2040); API presets have been corrected. Pass a custom `APIData` for your application. Stored Pyrogram API IDs remain preserved.
- `ValidationError` now subclasses `ValueError`. Existing code catching `ValidationError` remains compatible.

## 0.1.4

Previous public release. See the repository's existing tags and GitHub releases for its history.
