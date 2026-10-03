"""Telethon 1.x StringSession and SQLite authorization codec."""

import asyncio
import base64
import ipaddress
import struct
from pathlib import Path

from ..api import APIData
from ..data_center import DataCenter
from ..exceptions import MissingDependencyError, ValidationError
from ._utils import decode_string, read_session, validate_fields, write_database

# Version 7 is readable by older 1.x clients and upgraded by newer clients.
SCHEMA = """
CREATE TABLE version (version INTEGER PRIMARY KEY);
CREATE TABLE sessions (dc_id INTEGER PRIMARY KEY, server_address TEXT, port INTEGER,
                       auth_key BLOB, takeout_id INTEGER);
CREATE TABLE entities (id INTEGER PRIMARY KEY, hash INTEGER NOT NULL, username TEXT,
                       phone INTEGER, name TEXT, date INTEGER);
CREATE TABLE sent_files (md5_digest BLOB, file_size INTEGER, type INTEGER, id INTEGER,
                         hash INTEGER, PRIMARY KEY(md5_digest, file_size, type));
CREATE TABLE update_state (id INTEGER PRIMARY KEY, pts INTEGER, qts INTEGER, date INTEGER, seq INTEGER);
"""


class TeleSession:
    CURRENT_VERSION = "1"
    _STRUCT_PREFORMAT = ">B{}sH256s"
    REQUIRED_COLUMNS = {"dc_id", "server_address", "port", "auth_key", "takeout_id"}

    def __init__(
        self,
        *,
        dc_id: int,
        auth_key: bytes,
        server_address: str | None = None,
        port: int | None = None,
        takeout_id: int | None = None,
        user_id: int | None = None,
        phone_number: str | int | None = None,
        test_mode: bool = False,
    ):
        validate_fields(dc_id, auth_key, user_id)
        if type(test_mode) not in (bool, int) or test_mode not in (False, True):
            raise ValidationError("test_mode must be a boolean")
        if takeout_id is not None and (
            type(takeout_id) is not int or not -(2**63) <= takeout_id < 2**63
        ):
            raise ValidationError("takeout_id must be a signed 64-bit integer")
        if server_address is None:
            server_address, default_port = DataCenter(dc_id, test_mode)
        else:
            default_port = 80 if test_mode else 443
        try:
            self.server_address = str(ipaddress.ip_address(server_address))
        except ValueError:
            raise ValidationError("server_address must be an IPv4 or IPv6 address") from None
        self.port = default_port if port is None else port
        if type(self.port) is not int or not 0 < self.port <= 65535:
            raise ValidationError("port must be an integer between 1 and 65535")
        self.dc_id, self.auth_key = dc_id, auth_key
        self.takeout_id, self.user_id, self.phone_number = takeout_id, user_id, phone_number
        self.test_mode = test_mode or self.server_address in (
            set(DataCenter.TEST.values()) | set(DataCenter.TEST_IPV6.values())
        )

    @classmethod
    def from_string(cls, string: str):
        if not isinstance(string, str) or not string.startswith(cls.CURRENT_VERSION):
            raise ValidationError("Unsupported Telethon string version (expected 1)")
        raw = decode_string(string[1:])
        ip_len = len(raw) - 259
        if ip_len not in (4, 16):
            raise ValidationError("Invalid Telethon session string length")
        dc_id, address, port, key = struct.unpack(cls._STRUCT_PREFORMAT.format(ip_len), raw)
        return cls(
            dc_id=dc_id, auth_key=key, server_address=str(ipaddress.ip_address(address)), port=port
        )

    @classmethod
    async def from_file(cls, path: str | Path):
        row = await asyncio.to_thread(read_session, path, cls.REQUIRED_COLUMNS)
        # Cached entities include contacts, so none is a reliable owner identifier.
        return cls(**{key: row[key] for key in cls.REQUIRED_COLUMNS})

    @classmethod
    async def validate(cls, path: str | Path) -> bool:
        try:
            await cls.from_file(path)
        except (ValidationError, OSError):
            return False
        return True

    @staticmethod
    def encode(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).decode("ascii")

    @staticmethod
    def decode(value: str) -> bytes:
        return decode_string(value)

    def to_string(self) -> str:
        address = ipaddress.ip_address(self.server_address).packed
        return self.CURRENT_VERSION + self.encode(
            struct.pack(
                self._STRUCT_PREFORMAT.format(len(address)),
                self.dc_id,
                address,
                self.port,
                self.auth_key,
            )
        )

    async def to_file(self, path: str | Path) -> None:
        def populate(db):
            db.executescript(SCHEMA)
            db.execute("INSERT INTO version VALUES (7)")
            db.execute(
                "INSERT INTO sessions VALUES (?, ?, ?, ?, ?)",
                (self.dc_id, self.server_address, self.port, self.auth_key, self.takeout_id),
            )

        await asyncio.to_thread(write_database, path, populate)

    def client(self, api: APIData, proxy: dict | None = None, no_updates: bool = True):
        try:
            from telethon import TelegramClient
            from telethon.sessions import StringSession
        except ImportError:
            raise MissingDependencyError(
                'Install the client with: pip install "tgconvertor[telethon]"'
            ) from None
        return TelegramClient(
            StringSession(self.to_string()),
            api.api_id,
            api.api_hash,
            proxy=proxy,
            device_model=api.device_model,
            system_version=api.system_version,
            app_version=api.app_version,
            lang_code=api.lang_code,
            system_lang_code=api.system_lang_code,
            receive_updates=not no_updates,
            use_ipv6=":" in self.server_address,
        )
