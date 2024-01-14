import base64
import secrets
import struct
from typing import Type, Union
from pathlib import Path

import aiosqlite
from opentele.api import APIData
from pyrogram.client import Client

from ..exceptions import ValidationError


SCHEMA = """
CREATE TABLE sessions (
    dc_id     INTEGER PRIMARY KEY,
    api_id    INTEGER,
    test_mode INTEGER,
    auth_key  BLOB,
    date      INTEGER NOT NULL,
    user_id   INTEGER,
    is_bot    INTEGER
);

CREATE TABLE peers (
    id             INTEGER PRIMARY KEY,
    access_hash    INTEGER,
    type           INTEGER NOT NULL,
    username       TEXT,
    phone_number   TEXT,
    last_update_on INTEGER NOT NULL DEFAULT (CAST(STRFTIME('%s', 'now') AS INTEGER))
);

CREATE TABLE version (
    number INTEGER PRIMARY KEY
);

CREATE INDEX idx_peers_id ON peers (id);
CREATE INDEX idx_peers_username ON peers (username);
CREATE INDEX idx_peers_phone_number ON peers (phone_number);

CREATE TRIGGER trg_peers_last_update_on
    AFTER UPDATE
    ON peers
BEGIN
    UPDATE peers
    SET last_update_on = CAST(STRFTIME('%s', 'now') AS INTEGER)
    WHERE id = NEW.id;
END;
"""


class PyroSession:
    OLD_STRING_FORMAT = ">B?256sI?"
    OLD_STRING_FORMAT_64 = ">B?256sQ?"
    STRING_SIZE = 351
    STRING_SIZE_64 = 356
    STRING_FORMAT = ">BI?256sQ?"
    TABLES = {
        "sessions": {"dc_id", "test_mode", "auth_key", "date", "user_id", "is_bot"},
        "peers": {"id", "access_hash", "type", "username", "phone_number", "last_update_on"},
        "version": {"number"}
    }

    def __init__(
        self,
        *,
        dc_id: int,
        auth_key: bytes,
        user_id: None | int = None,
        is_bot: bool = False,
        test_mode: bool = False,
        api_id: None | int = None,
    ):
        self.dc_id = dc_id
        self.auth_key = auth_key
        self.user_id = user_id
        self.is_bot = is_bot
        self.test_mode = test_mode
        self.api_id = api_id

    @classmethod
    def from_string(cls, session_string: str):
        if len(session_string) in [cls.STRING_SIZE, cls.STRING_SIZE_64]:
            string_format = cls.OLD_STRING_FORMAT_64

            if len(session_string) == cls.STRING_SIZE:
                string_format = cls.OLD_STRING_FORMAT

            api_id = None
            dc_id, test_mode, auth_key, user_id, is_bot = struct.unpack(
                string_format,
                base64.urlsafe_b64decode(
                    session_string + "=" * (-len(session_string) % 4)
                )
            )
        else:
            dc_id, api_id, test_mode, auth_key, user_id, is_bot = struct.unpack(
                cls.STRING_FORMAT,
                base64.urlsafe_b64decode(
                    session_string + "=" * (-len(session_string) % 4)
                )
            )

        return cls(
            dc_id=dc_id,
            api_id=api_id,
            auth_key=auth_key,
            user_id=user_id,
            is_bot=is_bot,
            test_mode=test_mode,
        )

    @classmethod
    async def from_file(cls, path: Union[Path, str]):
        if not await cls.validate(path):
            raise ValidationError()

        async with aiosqlite.connect(path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM sessions") as cursor:
                session = await cursor.fetchone()

        return cls(**session)

    @classmethod
    async def validate(cls, path: Union[Path, str]) -> bool:
        try:
            async with aiosqlite.connect(path) as db:
                db.row_factory = aiosqlite.Row
                sql = "SELECT name FROM sqlite_master WHERE type='table'"
                async with db.execute(sql) as cursor:
                    tables = {row["name"] for row in await cursor.fetchall()}

                if tables != set(cls.TABLES.keys()):
                    return False

                for table, session_columns in cls.TABLES.items():
                    sql = f'pragma table_info("{table}")'
                    async with db.execute(sql) as cur:
                        columns = {row["name"] for row in await cur.fetchall()}
                        if "api_id" in columns:
                            columns.remove("api_id")
                        if session_columns != columns:
                            return False

        except aiosqlite.DatabaseError:
            return False

        return True

    def client(
        self,
        api: Type[APIData],
        proxy: None | dict = None,
        no_updates: bool = True
    ) -> Client:
        client = Client(
            name=secrets.token_urlsafe(8),
            api_id=api.api_id,
            api_hash=api.api_hash,
            app_version=api.app_version,
            device_model=api.device_model,
            system_version=api.system_version,
            lang_code=api.lang_code,
            proxy=proxy,
            session_string=self.to_string(),
            no_updates=no_updates,
            test_mode=self.test_mode,
        )
        return client

    def to_string(self) -> str:
        packed = struct.pack(
            self.STRING_FORMAT,
            self.dc_id,
            self.api_id or 0,
            self.test_mode,
            self.auth_key,
            self.user_id or 9999,
            self.is_bot
        )
        return base64.urlsafe_b64encode(packed).decode().rstrip("=")

    async def to_file(self, path: Union[Path, str]):
        async with aiosqlite.connect(path) as db:
            await db.executescript(SCHEMA)
            await db.commit()
            sql = "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?)"
            params = (
                self.dc_id,
                self.api_id,
                self.test_mode,
                self.auth_key,
                0,
                self.user_id or 9999,
                self.is_bot
            )
            await db.execute(sql, params)
            await db.commit()
