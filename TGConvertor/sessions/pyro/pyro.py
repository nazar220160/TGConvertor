"""Offline Pyrogram 2 / Kurigram session codec."""

import asyncio
import base64
import ipaddress
import secrets
import struct
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from ...api import APIData
from ...data_center import DataCenter
from ...exceptions import MissingDependencyError, ValidationError
from .._utils import decode_string, read_session, validate_fields, write_database


class PyroSession:
    OLD_STRING_FORMAT = OLD_FORMAT = ">B?256sI?"
    OLD_STRING_FORMAT_64 = OLD_FORMAT_64 = ">B?256sQ?"
    STRING_FORMAT = ">BI?256sQ?"
    STRING_SIZE = 351
    STRING_SIZE_64 = 356
    REQUIRED_COLUMNS = {"dc_id", "auth_key", "test_mode", "user_id", "is_bot", "date"}

    def __init__(
        self,
        *,
        dc_id: int,
        auth_key: bytes,
        user_id: int | None = None,
        is_bot: bool = False,
        test_mode: bool = False,
        api_id: int | None = None,
        date: int | None = None,
        server_address: str | None = None,
        port: int | None = None,
    ):
        validate_fields(dc_id, auth_key, user_id)
        if api_id is not None and (type(api_id) is not int or not 0 < api_id < 2**32):
            raise ValidationError("api_id must be a positive unsigned 32-bit integer")
        if type(test_mode) not in (bool, int) or test_mode not in (False, True):
            raise ValidationError("test_mode must be a boolean")
        if type(is_bot) not in (bool, int) or is_bot not in (False, True):
            raise ValidationError("is_bot must be a boolean")
        if server_address is not None:
            try:
                server_address = str(ipaddress.ip_address(server_address))
            except ValueError:
                raise ValidationError("server_address must be an IPv4 or IPv6 address") from None
            if port is None:
                port = 80 if test_mode else 443
        if port is not None and (type(port) is not int or not 0 < port <= 65535):
            raise ValidationError("port must be an integer between 1 and 65535")
        if date is not None and (type(date) is not int or date < 0 or date >= 2**63):
            raise ValidationError("date must be a non-negative signed 64-bit integer")
        self.dc_id, self.auth_key, self.user_id = dc_id, auth_key, user_id
        self.is_bot, self.test_mode = bool(is_bot), bool(test_mode)
        self.api_id, self.date = api_id, 0 if date is None else date
        self.server_address, self.port = server_address, port

    @classmethod
    def from_string(cls, session_string: str):
        raw = decode_string(session_string)
        formats = {
            struct.calcsize(fmt): fmt
            for fmt in (cls.OLD_STRING_FORMAT, cls.OLD_STRING_FORMAT_64, cls.STRING_FORMAT)
        }
        fmt = formats.get(len(raw))
        if fmt is None:
            raise ValidationError("Invalid Pyrogram session string length")
        mode_offset = 5 if fmt == cls.STRING_FORMAT else 1
        if raw[mode_offset] not in (0, 1) or raw[-1] not in (0, 1):
            raise ValidationError("Invalid Pyrogram session boolean fields")
        fields = struct.unpack(fmt, raw)
        if fmt == cls.STRING_FORMAT:
            dc_id, api_id, test_mode, auth_key, user_id, is_bot = fields
        else:
            dc_id, test_mode, auth_key, user_id, is_bot = fields
            api_id = None
        return cls(
            dc_id=dc_id,
            api_id=api_id or None,
            auth_key=auth_key,
            user_id=user_id or None,
            is_bot=is_bot,
            test_mode=test_mode,
        )

    @classmethod
    async def from_file(cls, path: str | Path):
        row = await asyncio.to_thread(read_session, path, cls.REQUIRED_COLUMNS)
        keys = cls.REQUIRED_COLUMNS | {"api_id", "server_address", "port"}
        return cls(**{key: row[key] for key in keys if key in row})

    @classmethod
    async def validate(cls, path: str | Path) -> bool:
        try:
            await cls.from_file(path)
        except (ValidationError, OSError):
            return False
        return True

    def _require_identity(self) -> None:
        if self.user_id is None:
            raise ValidationError(
                "Pyrogram output requires user_id; supply it or explicitly await session.get_user_id()"
            )
        if self.api_id is None:
            raise ValidationError("Pyrogram output requires api_id")

    def to_string(self) -> str:
        self._require_identity()
        packed = struct.pack(
            self.STRING_FORMAT,
            self.dc_id,
            self.api_id,
            self.test_mode,
            self.auth_key,
            self.user_id,
            self.is_bot,
        )
        return base64.urlsafe_b64encode(packed).decode("ascii").rstrip("=")

    @staticmethod
    def installed_backend() -> str | None:
        installed = []
        for package in ("pyrogram", "kurigram"):
            try:
                version(package)
                installed.append(package)
            except PackageNotFoundError:
                pass
        if len(installed) > 1:
            raise MissingDependencyError(
                "Pyrogram and Kurigram share the pyrogram namespace; install only one in this environment"
            )
        return installed[0] if installed else None

    async def to_file(self, path: str | Path, *, backend: str = "auto") -> None:
        self._require_identity()
        if backend == "auto":
            backend = self.installed_backend() or "pyrogram"
        if backend not in ("pyrogram", "kurigram"):
            raise ValidationError("backend must be auto, pyrogram, or kurigram")
        extended = backend == "kurigram"
        address, port = self.server_address, self.port
        if extended and address is None:
            address, default_port = DataCenter(self.dc_id, self.test_mode)
            port = default_port if port is None else port

        def populate(db):
            connection_columns = "server_address TEXT, port INTEGER," if extended else ""
            db.executescript(f"""
                CREATE TABLE sessions (dc_id INTEGER PRIMARY KEY, {connection_columns}
                    api_id INTEGER, test_mode INTEGER, auth_key BLOB, date INTEGER NOT NULL,
                    user_id INTEGER, is_bot INTEGER);
                CREATE TABLE peers (id INTEGER PRIMARY KEY, access_hash INTEGER, type INTEGER NOT NULL,
                    {"" if extended else "username TEXT,"} phone_number TEXT,
                    last_update_on INTEGER NOT NULL DEFAULT (CAST(STRFTIME('%s', 'now') AS INTEGER)));
                CREATE TABLE version (number INTEGER PRIMARY KEY);
                CREATE INDEX idx_peers_id ON peers (id);
                CREATE INDEX idx_peers_phone_number ON peers (phone_number);
                CREATE TRIGGER trg_peers_last_update_on AFTER UPDATE ON peers BEGIN
                    UPDATE peers SET last_update_on = CAST(STRFTIME('%s', 'now') AS INTEGER)
                    WHERE id = NEW.id;
                END;
            """)
            if extended:
                db.executescript("""
                    CREATE TABLE usernames (id INTEGER, username TEXT, FOREIGN KEY(id) REFERENCES peers(id));
                    CREATE INDEX idx_usernames_id ON usernames (id);
                    CREATE INDEX idx_usernames_username ON usernames (username);
                    CREATE TABLE update_state (id INTEGER PRIMARY KEY, pts INTEGER, qts INTEGER,
                                               date INTEGER, seq INTEGER);
                """)
            else:
                db.execute("CREATE INDEX idx_peers_username ON peers (username)")
            values = (
                (self.dc_id,)
                + ((address, port) if extended else ())
                + (
                    self.api_id,
                    int(self.test_mode),
                    self.auth_key,
                    self.date,
                    self.user_id,
                    int(self.is_bot),
                )
            )
            db.execute(f"INSERT INTO sessions VALUES ({','.join('?' for _ in values)})", values)
            db.execute("INSERT INTO version VALUES (?)", (7 if extended else 3,))

        await asyncio.to_thread(write_database, path, populate)

    def client(self, api: APIData, proxy: dict | None = None, no_updates: bool = True):
        if self.installed_backend() is None:
            raise MissingDependencyError(
                'Install a client with: pip install "tgconvertor[kurigram]"'
            )
        try:
            from pyrogram import Client
        except ImportError:
            raise MissingDependencyError(
                "Cannot import the installed Pyrogram/Kurigram client"
            ) from None
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
