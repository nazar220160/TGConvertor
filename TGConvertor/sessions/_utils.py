"""Validation and safe I/O shared by session codecs."""

import base64
import binascii
import os
import sqlite3
import tempfile
from collections.abc import Callable
from contextlib import closing
from pathlib import Path

from ..exceptions import ValidationError


def validate_fields(dc_id: int, auth_key: bytes, user_id: int | None = None) -> None:
    if type(dc_id) is not int or not 1 <= dc_id <= 255:
        raise ValidationError("dc_id must be an integer between 1 and 255")
    if not isinstance(auth_key, bytes) or len(auth_key) != 256 or not any(auth_key):
        raise ValidationError("auth_key must be 256 bytes and must not be all zero")
    if user_id is not None and (type(user_id) is not int or not 0 < user_id < 2**63):
        raise ValidationError("user_id must be a positive signed 64-bit integer")


def decode_string(value: str) -> bytes:
    if not isinstance(value, str) or not value or len(value) > 512:
        raise ValidationError("Invalid session string")
    try:
        return base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
    except (ValueError, binascii.Error):
        raise ValidationError("Invalid session string encoding") from None


def read_session(path: str | Path, required: set[str]) -> dict:
    """Read one authorization from SQLite without modifying the source."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Session file does not exist: {path}")
    try:
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            db.row_factory = sqlite3.Row
            columns = {row["name"] for row in db.execute("PRAGMA table_info(sessions)")}
            if not required.issubset(columns):
                raise ValidationError("Session database has an unsupported schema")
            rows = db.execute("SELECT * FROM sessions LIMIT 2").fetchall()
            if len(rows) != 1:
                raise ValidationError("Session database must contain exactly one authorization")
            return dict(rows[0])
    except sqlite3.Error:
        raise ValidationError(
            "Cannot read session database; close its client and check the format"
        ) from None


def write_database(path: str | Path, populate: Callable[[sqlite3.Connection], None]) -> None:
    """Build privately, then publish exclusively; never replace an existing file."""
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"Output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".tgconvertor-", suffix=".session", dir=path.parent)
    os.close(fd)
    temporary = Path(name)
    try:
        with closing(sqlite3.connect(temporary)) as db:
            populate(db)
            db.commit()
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
