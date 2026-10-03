"""Generate synthetic sessions and independent native cryptography expectations."""

import asyncio
import hashlib
import json
import sys
import warnings
import zipfile
from pathlib import Path

import tgcrypto

from TGConvertor import APIData, SessionManager


async def main():
    destination = Path(sys.argv[1]).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    session = SessionManager(
        2,
        bytes(range(256)),
        user_id=2**40 + 17,
        api=APIData(12345, "0123456789abcdef0123456789abcdef"),
    )
    await session.to_gramjs_file(destination / "gramjs_file.txt")
    await session.to_telethon_file(destination / "telethon_file.session")
    await session.to_pyrogram_file(destination / "pyrogram_file.session", backend="pyrogram")
    await session.to_pyrogram_file(destination / "kurigram_file.session", backend="kurigram")
    for name, passcode in (("tdata_plain", ""), ("tdata_encrypted", "source-local-passcode")):
        folder = destination / name
        await session.to_tdata_folder(folder, passcode=passcode)
        with zipfile.ZipFile(destination / (name + ".zip"), "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(folder.rglob("*")):
                if path.is_file():
                    archive.write(path, "tdata/" + path.relative_to(folder).as_posix())
    (destination / "strings.json").write_text(
        json.dumps(
            {
                "telethon_string": session.to_telethon_string(),
                "pyrogram_string": session.to_pyrogram_string(),
                "gramjs_string": session.to_gramjs_string(),
            }
        )
    )
    key, iv, data = bytes(range(32)), bytes(range(32, 64)), bytes(range(256))
    (destination / "crypto.json").write_text(
        json.dumps(
            {
                "key": list(key),
                "iv": list(iv),
                "data": list(data),
                "encrypted": list(tgcrypto.ige256_encrypt(data, key, iv)),
                "pbkdf2": list(
                    hashlib.pbkdf2_hmac("sha512", b"local-passcode", b"test-salt", 120, 256)
                ),
            }
        )
    )
    (destination / "outputs").mkdir(exist_ok=True)
    invalid = destination / "invalid"
    invalid.mkdir(exist_ok=True)
    for name, entries in {
        "traversal": [("../escape", b"x")],
        "absolute": [("/escape", b"x")],
        "backslash": [("tdata\\escape", b"x")],
        "drive": [("C:/escape", b"x")],
        "duplicate": [("tdata/key_data", b"x"), ("tdata/key_data", b"y")],
        "empty": [],
        "too-many": [(f"folder{i}/", b"") for i in range(257)],
    }.items():
        with warnings.catch_warnings(), zipfile.ZipFile(invalid / (name + ".zip"), "w") as archive:
            warnings.simplefilter("ignore", UserWarning)
            for filename, content in entries:
                archive.writestr(filename, content)
    with zipfile.ZipFile(invalid / "symlink.zip", "w") as archive:
        entry = zipfile.ZipInfo("tdata/key_data")
        entry.create_system = 3
        entry.external_attr = 0o120777 << 16
        archive.writestr(entry, "/escape")
    with (
        zipfile.ZipFile(invalid / "expanded-limit.zip", "w", zipfile.ZIP_DEFLATED) as archive,
        archive.open("tdata/key_data", "w") as member,
    ):
        for _ in range(65 * 16):
            member.write(bytes(65536))
    print("Generated nine synthetic source representations and native crypto vectors")


if __name__ == "__main__":
    asyncio.run(main())
