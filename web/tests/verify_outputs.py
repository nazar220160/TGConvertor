"""Independently read WASM exports using native SDKs, without contacting Telegram."""

import io
import json
import sqlite3
import struct
import sys
import tempfile
import zipfile
from base64 import urlsafe_b64decode
from pathlib import Path

from opentele2.td import TDesktop
from telethon.sessions import SQLiteSession, StringSession

root = Path(sys.argv[1]) / "outputs"
for item in json.loads((root / "manifest.json").read_text()):
    data = (root / item["file"]).read_bytes()
    kind = item["target"]
    if kind.startswith("gramjs"):
        # Checked with the actual npm StringSession in engine.test.mjs.
        continue
    if kind.startswith("tdata"):
        with tempfile.TemporaryDirectory() as temporary:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                archive.extractall(temporary)
            desktop = TDesktop(str(Path(temporary) / "tdata"), passcode=item["passcode"])
            assert desktop.mainAccount.authKey.key == bytes(range(256))
            assert desktop.mainAccount.UserId == 2**40 + 17
    elif kind.startswith("telethon"):
        if kind.endswith("string"):
            storage = StringSession(data.decode())
        else:
            # Copy to a named .session file: the upstream SDK may migrate its schema.
            with tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary) / "native.session"
                path.write_bytes(data)
                storage = SQLiteSession(str(path))
                assert storage.auth_key.key == bytes(range(256))
                assert storage.dc_id == 2
                storage.close()
            continue
        assert storage.auth_key.key == bytes(range(256))
        assert storage.dc_id == 2
        storage.close()
    elif kind.endswith("string"):
        dc, api, test, key, user, bot = struct.unpack(
            ">BI?256sQ?", urlsafe_b64decode(data + b"=" * (-len(data) % 4))
        )
        assert dc == 2 and key == bytes(range(256)) and user == 2**40 + 17
        assert not test and not bot
    else:
        with sqlite3.connect(root / item["file"]) as connection:
            dc, key, user = connection.execute(
                "SELECT dc_id, auth_key, user_id FROM sessions"
            ).fetchone()
            assert dc == 2 and key == bytes(range(256)) and user == 2**40 + 17
            assert connection.execute("SELECT number FROM version").fetchone()[0] == (
                7 if kind == "kurigram_file" else 3
            )
print("All browser exports accepted by independent native readers; authorization preserved")
