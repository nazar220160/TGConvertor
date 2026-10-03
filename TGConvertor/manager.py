"""A common authorization model for all supported session formats."""

import asyncio
from pathlib import Path

from .api import API, APIData
from .exceptions import ValidationError
from .sessions._utils import validate_fields
from .sessions.pyro import PyroSession
from .sessions.tdata import TDataSession
from .sessions.tele import TeleSession


class SessionManager:
    """Convert authorizations offline; network operations are explicit."""

    def __init__(
        self,
        dc_id: int,
        auth_key: bytes,
        user_id: int | None = None,
        valid: bool | None = None,
        api: APIData = API.TelegramDesktop,
        phone_number: str | None = None,
        test_mode: bool = False,
        is_bot: bool = False,
        api_id: int | None = None,
        *,
        server_address: str | None = None,
        port: int | None = None,
        takeout_id: int | None = None,
    ):
        validate_fields(dc_id, auth_key, user_id)
        self.dc_id, self.auth_key, self.user_id = dc_id, auth_key, user_id
        self.valid, self.phone_number = valid, phone_number
        self.api = api.copy()
        self.api_id = api.api_id if api_id is None else api_id
        self.test_mode, self.is_bot = test_mode, is_bot
        self.server_address, self.port, self.takeout_id = server_address, port, takeout_id
        self.user = self.client = None
        # Check the Pyrogram metadata even when the first export is to Telethon.
        _ = self.pyrogram

    def __repr__(self):
        return f"SessionManager(dc_id={self.dc_id}, user_id={self.user_id}, test_mode={self.test_mode})"

    async def __aenter__(self):
        if self.client is not None:
            raise RuntimeError("This SessionManager already has an active client")
        client = self.telethon_client()
        self.client = client
        try:
            await client.connect()
        except BaseException:
            try:
                await client.disconnect()
            finally:
                self.client = None
            raise
        return client

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            await self.client.disconnect()
        finally:
            self.client = None

    @property
    def auth_key_hex(self) -> str:
        return self.auth_key.hex()

    @classmethod
    def _from_telethon(cls, session: TeleSession, api: APIData):
        return cls(
            dc_id=session.dc_id,
            auth_key=session.auth_key,
            api=api,
            server_address=session.server_address,
            port=session.port,
            takeout_id=session.takeout_id,
            test_mode=session.test_mode,
        )

    @classmethod
    async def from_telethon_file(cls, file: str | Path, api: APIData = API.TelegramDesktop):
        return cls._from_telethon(await TeleSession.from_file(file), api)

    @classmethod
    def from_telethon_string(cls, string: str, api: APIData = API.TelegramDesktop):
        return cls._from_telethon(TeleSession.from_string(string), api)

    @classmethod
    def _from_pyrogram(cls, session: PyroSession, api: APIData):
        return cls(
            dc_id=session.dc_id,
            auth_key=session.auth_key,
            api=api,
            user_id=session.user_id,
            test_mode=session.test_mode,
            is_bot=session.is_bot,
            api_id=session.api_id,
            server_address=session.server_address,
            port=session.port,
        )

    @classmethod
    async def from_pyrogram_file(cls, file: str | Path, api: APIData = API.TelegramDesktop):
        return cls._from_pyrogram(await PyroSession.from_file(file), api)

    @classmethod
    def from_pyrogram_string(cls, string: str, api: APIData = API.TelegramDesktop):
        return cls._from_pyrogram(PyroSession.from_string(string), api)

    @classmethod
    def from_tdata_folder(
        cls,
        folder: str | Path,
        *,
        passcode: str = "",
        account_index: int | None = None,
        api: APIData = API.TelegramDesktop,
    ):
        session = TDataSession.from_tdata(folder, passcode=passcode, account_index=account_index)
        return cls(dc_id=session.dc_id, auth_key=session.auth_key, user_id=session.user_id, api=api)

    async def to_pyrogram_file(self, path: str | Path, *, backend: str = "auto") -> None:
        await self.pyrogram.to_file(path, backend=backend)

    def to_pyrogram_string(self) -> str:
        return self.pyrogram.to_string()

    async def to_telethon_file(self, path: str | Path) -> None:
        await self.telethon.to_file(path)

    def to_telethon_string(self) -> str:
        return self.telethon.to_string()

    async def to_tdata_folder(self, path: str | Path, *, passcode: str = "") -> None:
        await asyncio.to_thread(self.tdata.to_folder, path, passcode=passcode)

    @property
    def pyrogram(self) -> PyroSession:
        return PyroSession(
            dc_id=self.dc_id,
            auth_key=self.auth_key,
            user_id=self.user_id,
            api_id=self.api_id,
            test_mode=self.test_mode,
            is_bot=self.is_bot,
            server_address=self.server_address,
            port=self.port,
        )

    @property
    def telethon(self) -> TeleSession:
        return TeleSession(
            dc_id=self.dc_id,
            auth_key=self.auth_key,
            server_address=self.server_address,
            port=self.port,
            takeout_id=self.takeout_id,
            test_mode=self.test_mode,
        )

    @property
    def tdata(self) -> TDataSession:
        if self.test_mode or self.is_bot:
            raise ValidationError("tdata supports production user accounts only")
        if self.user_id is None:
            raise ValidationError(
                "tdata requires user_id; supply it or explicitly await session.get_user_id()"
            )
        return TDataSession(
            dc_id=self.dc_id, auth_key=self.auth_key, api=self.api, user_id=self.user_id
        )

    def pyrogram_client(self, proxy=None, no_updates=True):
        return self.pyrogram.client(api=self.api, proxy=proxy, no_updates=no_updates)

    def telethon_client(self, proxy=None, no_updates=True):
        return self.telethon.client(api=self.api, proxy=proxy, no_updates=no_updates)

    async def validate(self) -> bool:
        """Ask Telegram whether the authorization is valid; may raise network errors."""
        self.valid = bool(await self.get_user())
        return self.valid

    async def get_user_id(self) -> int:
        if self.user_id is None:
            await self.get_user()
        if self.user_id is None:
            raise ValidationError("Telegram authorization is not logged in")
        return self.user_id

    async def get_user(self):
        """Fetch the account from Telegram and cache its identity."""
        async with self as client:
            self.user = await client.get_me()
        self.valid = bool(self.user)
        if self.user is not None:
            self.user_id = self.user.id
            self.is_bot = bool(self.user.bot)
            self.phone_number = self.user.phone
        else:
            self.user_id = self.phone_number = None
        return self.user
