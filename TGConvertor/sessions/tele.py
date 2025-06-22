import base64
import ipaddress
import struct
from pathlib import Path
from typing import Type

# import aiosqlite # No longer needed for direct DB manipulation for to_file/from_file
from opentele.api import APIData # Still needed for APIData type hint in client()
from pyrogram.session.internals.data_center import DataCenter # For DataCenter default IP/port
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.sessions.sqlite import SQLiteSession # For reading/writing .session files

from ..exceptions import ValidationError

# SCHEMA variable is no longer needed by to_file or from_file if we use SQLiteSession object
# SCHEMA = """
# CREATE TABLE version (version integer primary key);

# CREATE TABLE sessions (
#     dc_id integer primary key,
#     server_address text,
    port integer,
    auth_key blob,
    takeout_id integer
# );

# CREATE TABLE entities (
#     id integer primary key,
#     hash integer not null,
#     username text,
#     phone integer,
#     name text,
#     date integer
# );

# CREATE TABLE sent_files (
#     md5_digest blob,
#     file_size integer,
#     type integer,
#     id integer,
#     hash integer,
#     primary key(md5_digest, file_size, type)
# );

# CREATE TABLE update_state (
#     id integer primary key,
#     pts integer,
#     qts integer,
#     date integer,
#     seq integer
# );
# """


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
        # The method is async, but SQLiteSession loads synchronously.
        # Consider making this synchronous if Telethon's session loading is purely sync.
        # For now, keeping async to match existing signature.

        session_file = SQLiteSession(str(path))

        # session_file.load() is called implicitly by property access if not loaded.
        # We can check for auth_key to see if it's a valid-looking session.
        if not session_file.auth_key:
            # This check might not be foolproof if a session can legitimately have no auth_key
            # temporarily, but for a saved session, it should exist.
            # Telethon's own load() method doesn't raise error on empty/new session files.
            # It might be better to let it load what it can and fail later if auth_key is truly missing.
            # However, for TGConvertor's purpose, a session without auth_key is not convertible.
             raise ValidationError(f"Session file {path} might be empty or invalid (no auth_key).")

        # user_id and phone_number are not directly part of the core session data
        # loaded by SQLiteSession properties. They are typically populated by client interactions
        # and stored in other tables (e.g. 'entities') by the Telethon client.
        # We will not attempt to read them directly here to maintain compatibility
        # with Telethon's own session file management.
        return cls(
            dc_id=session_file.dc_id,
            server_address=session_file.server_address,
            port=session_file.port,
            auth_key=session_file.auth_key,
            takeout_id=session_file.takeout_id,
            user_id=None,
            phone_number=None
        )

    # @classmethod
    # async def validate(cls, path: Path) -> bool: # No longer needed, Telethon's SQLiteSession handles file structure.
    #     pass

    @staticmethod
    def encode(x: bytes) -> str:
        return base64.urlsafe_b64encode(x).decode('ascii')

    @staticmethod
    def decode(x: str) -> bytes:
        return base64.urlsafe_b64decode(x)

    def client(
            self,
            api: Type[APIData],
            proxy: None | dict = None,
            no_updates: bool = True
    ):
        client = TelegramClient(
            session=StringSession(self.to_string()),
            api_id=api.api_id,
            api_hash=api.api_hash,
            proxy=proxy,
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
            self.server_address, self.port = DataCenter(
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
        if self.server_address is None or self.port is None:
            # DataCenter is from pyrogram.session.internals.data_center
            # It might be better to use Telethon's own way if available,
            # but this was pre-existing.
            dc_info = DataCenter(self.dc_id, False, False, False)
            self.server_address = dc_info.ip_address
            self.port = dc_info.port

        new_session = SQLiteSession(str(path))
        new_session.set_dc(self.dc_id, self.server_address, self.port)
        new_session.auth_key = self.auth_key
        if self.takeout_id is not None:
            new_session.takeout_id = self.takeout_id

        # SQLiteSession.save() is synchronous in Telethon's source
        # but since this method is async, we should ideally use async file ops
        # However, SQLiteSession itself doesn't offer async save.
        # For now, direct call. If it blocks significantly, it's an issue for async context.
        new_session.save()
        # Note: user_id and phone_number are not saved this way, as Telethon's
        # SQLiteSession primarily handles connection auth data.
        # Entities are managed by the client during runtime.
