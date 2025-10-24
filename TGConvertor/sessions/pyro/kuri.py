import base64
import secrets
import struct
import time
from typing import Type, Union
from pathlib import Path

import aiosqlite
from opentele.api import APIData
from pyrogram.client import Client

from ...exceptions import ValidationError

# Схема из новой версии Pyrogram
SCHEMA = """
CREATE TABLE sessions
(
    dc_id          INTEGER PRIMARY KEY,
    server_address TEXT,
    port           INTEGER,
    api_id         INTEGER,
    test_mode      INTEGER,
    auth_key       BLOB,
    date           INTEGER NOT NULL,
    user_id        INTEGER,
    is_bot         INTEGER
);

CREATE TABLE peers
(
    id             INTEGER PRIMARY KEY,
    access_hash    INTEGER,
    type           INTEGER NOT NULL,
    phone_number   TEXT,
    last_update_on INTEGER NOT NULL DEFAULT (CAST(STRFTIME('%s', 'now') AS INTEGER))
);

CREATE TABLE usernames
(
    id       INTEGER,
    username TEXT,
    FOREIGN KEY (id) REFERENCES peers(id)
);

CREATE TABLE update_state
(
    id   INTEGER PRIMARY KEY,
    pts  INTEGER,
    qts  INTEGER,
    date INTEGER,
    seq  INTEGER
);

CREATE TABLE version
(
    number INTEGER PRIMARY KEY
);

CREATE INDEX idx_peers_id ON peers (id);
CREATE INDEX idx_peers_phone_number ON peers (phone_number);
CREATE INDEX idx_usernames_id ON usernames (id);
CREATE INDEX idx_usernames_username ON usernames (username);

CREATE TRIGGER trg_peers_last_update_on
    AFTER UPDATE
    ON peers
BEGIN
    UPDATE peers
    SET last_update_on = CAST(STRFTIME('%s', 'now') AS INTEGER)
    WHERE id = NEW.id;
END;
"""

# IP-адреса центров данных Telegram
TEST = {1: "149.154.175.10", 2: "149.154.167.40", 3: "149.154.175.117"}

PROD = {
    1: "149.154.175.53",
    2: "149.154.167.51",
    3: "149.154.175.100",
    4: "149.154.167.91",
    5: "91.108.56.130",
    203: "91.105.192.100",
}


class PyroSession:
    STRING_FORMAT = ">BI?256sQ?"
    OLD_FORMAT = ">B?256sI?"
    OLD_FORMAT_64 = ">B?256sQ?"
    STRING_SIZE = 351
    STRING_SIZE_64 = 356

    TABLES = {"sessions", "peers", "usernames", "update_state", "version"}

    def __init__(
        self,
        *,
        dc_id: int,
        auth_key: bytes,
        api_id: int | None = None,
        user_id: int | None = None,
        is_bot: bool = False,
        test_mode: bool = False,
        server_address: str | None = None,
        port: int | None = None,
        date: int | None = None,
    ):
        self.dc_id = dc_id
        self.auth_key = auth_key
        self.api_id = api_id
        self.user_id = user_id
        self.is_bot = is_bot
        self.test_mode = test_mode
        self.server_address = server_address or (TEST if test_mode else PROD).get(dc_id)
        self.port = port or (80 if test_mode else 443)
        self.date = date or int(time.time())

    @classmethod
    def from_string(cls, session_string: str):
        """Создать объект PyroSession из session_string."""
        s = session_string + "=" * (-len(session_string) % 4)
        raw_bytes = base64.urlsafe_b64decode(s)

        if len(session_string) in [cls.STRING_SIZE, cls.STRING_SIZE_64]:
            fmt = (
                cls.OLD_FORMAT_64
                if len(session_string) == cls.STRING_SIZE_64
                else cls.OLD_FORMAT
            )
            dc_id, test_mode, auth_key, user_id, is_bot = struct.unpack(fmt, raw_bytes)
            api_id = None
        else:
            dc_id, api_id, test_mode, auth_key, user_id, is_bot = struct.unpack(
                cls.STRING_FORMAT, raw_bytes
            )

        server_address = (TEST if test_mode else PROD).get(dc_id)
        port = 80 if test_mode else 443

        return cls(
            dc_id=dc_id,
            api_id=api_id,
            test_mode=test_mode,
            auth_key=auth_key,
            user_id=user_id,
            is_bot=is_bot,
            server_address=server_address,
            port=port,
        )

    def to_string(self) -> str:
        """Экспортирует сессию в session_string (новый формат)."""
        print(self.STRING_FORMAT)
        print(self.dc_id)
        print(self.api_id)
        print(self.test_mode)
        print(self.auth_key)
        print(self.user_id)
        print(self.is_bot)

        packed = struct.pack(
            self.STRING_FORMAT,
            self.dc_id,
            self.api_id or 0,
            self.test_mode,
            self.auth_key,
            self.user_id or 0,
            self.is_bot,
        )
        return base64.urlsafe_b64encode(packed).decode().rstrip("=")

    @classmethod
    async def from_file(cls, path: Union[Path, str]):
        """Загружает сессию из .session файла."""
        if not await cls.validate(path):
            raise ValidationError(f"Invalid session structure: {path}")

        async with aiosqlite.connect(path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM sessions") as cursor:
                session = await cursor.fetchone()

        return cls(**session)

    @classmethod
    async def validate(cls, path: Union[Path, str]) -> bool:
        """Проверка, что база соответствует новой схеме."""
        try:
            async with aiosqlite.connect(path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ) as cur:
                    tables = {row["name"] for row in await cur.fetchall()}

                # должны быть все нужные таблицы
                if not cls.TABLES.issubset(tables):
                    return False

                # минимальная проверка колонок sessions
                async with db.execute("PRAGMA table_info('sessions')") as cur:
                    cols = {r["name"] for r in await cur.fetchall()}
                    expected = {
                        "dc_id",
                        "server_address",
                        "port",
                        "api_id",
                        "test_mode",
                        "auth_key",
                        "date",
                        "user_id",
                        "is_bot",
                    }
                    if not expected.issubset(cols):
                        return False
        except aiosqlite.DatabaseError:
            return False

        return True

    async def to_file(self, path: Union[Path, str]):
        """Создает новый .session файл с текущими данными."""
        async with aiosqlite.connect(path) as db:
            await db.executescript(SCHEMA)
            await db.commit()

            await db.execute(
                "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    self.dc_id,
                    self.server_address,
                    self.port,
                    self.api_id,
                    int(self.test_mode),
                    self.auth_key,
                    self.date,
                    self.user_id,
                    int(self.is_bot),
                ),
            )
            await db.execute("INSERT INTO version VALUES (?)", (7,))
            await db.commit()

    def client(
        self, api: Type[APIData], proxy: dict | None = None, no_updates: bool = True
    ) -> Client:
        """Создает готовый pyrogram.Client на основе этой сессии."""
        return Client(
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
