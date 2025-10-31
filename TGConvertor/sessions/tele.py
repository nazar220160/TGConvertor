import base64
import ipaddress
import struct
from pathlib import Path

import aiosqlite
from telethon import TelegramClient # type: ignore
from telethon.sessions import StringSession # type: ignore

from . import is_kurigram
if is_kurigram:
    from pyrogram.storage.sqlite_storage import PROD # type: ignore
else:
    from pyrogram.session.internals.data_center import DataCenter # type: ignore

from ..api import APIData
from ..exceptions import ValidationError


SCHEMA = """
CREATE TABLE version (version integer primary key);

CREATE TABLE sessions (
    dc_id integer primary key,
    server_address text,
    port integer,
    auth_key blob,
    takeout_id integer
);

CREATE TABLE entities (
    id integer primary key,
    hash integer not null,
    username text,
    phone integer,
    name text,
    date integer
);

CREATE TABLE sent_files (
    md5_digest blob,
    file_size integer,
    type integer,
    id integer,
    hash integer,
    primary key(md5_digest, file_size, type)
);

CREATE TABLE update_state (
    id integer primary key,
    pts integer,
    qts integer,
    date integer,
    seq integer
);
"""


class TeleSession:
    _STRUCT_PREFORMAT = '>B{}sH256s'
    CURRENT_VERSION = '1'
    TABLES = {
        "sessions": {
            "dc_id", "server_address", "port", "auth_key", "takeout_id"
        },
        "entities": {"id", "hash", "username", "phone", "name", "date"},
        "sent_files": {"md5_digest", "file_size", "type", "id", "hash"},
        "update_state": {"id", "pts", "qts", "date", "seq"},
        "version": {"version"},
    }

    def __init__(
            self,
            *,
            dc_id: int,
            auth_key: bytes,
            server_address: None | str = None,
            port: None | int = None,
            takeout_id: None | int = None,
            user_id: None | int = None,
            phone_number: None | int = None
    ):
        self.dc_id = dc_id
        self.auth_key = auth_key
        self.server_address = server_address
        self.port = port
        self.takeout_id = takeout_id
        self.user_id = user_id
        self.phone_number = phone_number

    @classmethod
    def from_string(cls, string: str):
        string = string[1:]
        ip_len = 4 if len(string) == 352 else 16
        dc_id, ip, port, auth_key = struct.unpack(
            cls._STRUCT_PREFORMAT.format(ip_len), cls.decode(string)
        )
        server_address = ipaddress.ip_address(ip).compressed
        return cls(
            auth_key=auth_key,
            dc_id=dc_id,
            port=port,
            server_address=server_address,
        )

    @classmethod
    async def from_file(cls, path: Path):
        if not await cls.validate(path):
            raise ValidationError()

        async with aiosqlite.connect(path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM sessions") as cursor:
                session = await cursor.fetchone()
        async with aiosqlite.connect(path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM entities WHERE id NOT LIKE 0") as cursor:
                row = await cursor.fetchone()
                entities = dict(row) if row else {}
                
        return cls(user_id=entities.get('id'), phone_number=entities.get('phone'), **session) # type: ignore

    @classmethod
    async def validate(cls, path: Path) -> bool:
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
                        if session_columns != columns:
                            return False

        except aiosqlite.DatabaseError:
            return False

        return True

    @staticmethod
    def encode(x: bytes) -> str:
        return base64.urlsafe_b64encode(x).decode('ascii')

    @staticmethod
    def decode(x: str) -> bytes:
        return base64.urlsafe_b64decode(x)

    def client(
            self,
            api: APIData,
            proxy: None | dict = None,
            no_updates: bool = True
    ):
        client = TelegramClient(
            session=StringSession(self.to_string()),
            api_id=api.api_id,
            api_hash=api.api_hash,
            proxy=proxy, # type: ignore
            device_model=api.device_model,
            system_version=api.system_version,
            app_version=api.app_version,
            lang_code=api.lang_code,
            system_lang_code=api.system_lang_code,
            receive_updates=not no_updates,
        )
        return client

    def to_string(self) -> str:
        if self.server_address is None:
            if is_kurigram:
                self.server_address = PROD[self.dc_id] # type: ignore
                self.port = 443
            else:
                self.server_address, self.port = DataCenter( # type: ignore
                    self.dc_id, False, False, False
                )
        ip = ipaddress.ip_address(self.server_address).packed
        return self.CURRENT_VERSION + self.encode(struct.pack(
            self._STRUCT_PREFORMAT.format(len(ip)),
            self.dc_id,
            ip,
            self.port,
            self.auth_key
        ))

    async def to_file(self, path: Path):
        if self.server_address is None:
            if is_kurigram:
                self.server_address = PROD[self.dc_id] # type: ignore
                self.port = 443
            else:
                self.server_address, self.port = DataCenter( # type: ignore
                    self.dc_id, False, False, False
                )
        async with aiosqlite.connect(path) as db:
            await db.executescript(SCHEMA)
            await db.commit()
            await db.execute("INSERT INTO version (version) VALUES (?)", (7,))
            await db.commit()
            sql = "INSERT INTO sessions VALUES (?, ?, ?, ?, ?)"
            params = (
                self.dc_id,
                self.server_address,
                self.port,
                self.auth_key,
                self.takeout_id
            )
            await db.execute(sql, params)
            await db.commit()
