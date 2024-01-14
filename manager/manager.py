from pathlib import Path
from typing import Type, Union
from opentele.api import API, APIData
from .sessions.pyro import PyroSession
from .sessions.tele import TeleSession
from .sessions.tdata import TDataSession
from .exceptions import ValidationError

class SessionManager:
    def __init__(
        self,
        dc_id: int,
        auth_key: bytes,
        user_id: None | int = None,
        valid: None | bool = None,
        api: Type[APIData] = API.TelegramDesktop,
    ):
        """
        Initializes a SessionManager instance with the specified parameters.

        Args:
            dc_id (int): Data center ID.
            auth_key (bytes): Authentication key.
            user_id (None|int, optional): User ID, default is None.
            valid (None|bool, optional): Validation status, default is None.
            api (Type[APIData], optional): API type, default is API.TelegramDesktop.
        """

        self.dc_id = dc_id
        self.auth_key = auth_key
        self.user_id = user_id
        self.valid = valid
        self.api = api.copy()
        self.user = None
        self.client = None

    async def __aenter__(self):
        """
        Asynchronous context manager entry method.
        Establishes a connection to the Telethon client.
        """
        self.client = self.telethon_client()
        await self.client.connect()
        return self.client

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Asynchronous context manager exit method.
        Disconnects the Telethon client.
        """
        await self.client.disconnect()
        self.client = None

    @property
    def auth_key_hex(self) -> str:
        """
        Returns the hexadecimal representation of the authentication key.
        """
        return self.auth_key.hex()

    @classmethod
    async def from_telethon_file(cls, file: Union[Path, str], api=API.TelegramDesktop):
        """
        Creates a SessionManager instance from a Telethon file.

        Args:
            file (Union[Path, str]): Path to the Telethon file.
            api (Type[APIData], optional): API type, default is API.TelegramDesktop.

        Returns:
            SessionManager: An instance initialized from the Telethon file.
        """
        session = await TeleSession.from_file(file)
        return cls(
            dc_id=session.dc_id,
            auth_key=session.auth_key,
            api=api
        )

    @classmethod
    def from_telethon_string(cls, string: str, api=API.TelegramDesktop):
        """
        Creates a SessionManager instance from a Telethon string.

        Args:
            string (str): Telethon session string.
            api (Type[APIData], optional): API type, default is API.TelegramDesktop.

        Returns:
            SessionManager: An instance initialized from the Telethon string.
        """
        session = TeleSession.from_string(string)
        return cls(
            dc_id=session.dc_id,
            auth_key=session.auth_key,
            api=api
        )

    @classmethod
    async def from_pyrogram_file(cls, file: Union[Path, str], api=API.TelegramDesktop):
        """
        Creates a SessionManager instance from a Pyrogram file.

        Args:
            file (Union[Path, str]): Path to the Pyrogram file.
            api (Type[APIData], optional): API type, default is API.TelegramDesktop.

        Returns:
            SessionManager: An instance initialized from the Pyrogram file.
        """
        session = await PyroSession.from_file(file)
        return cls(
            auth_key=session.auth_key,
            dc_id=session.dc_id,
            api=api,
            user_id=session.user_id,
        )

    @classmethod
    def from_pyrogram_string(cls, string: str, api=API.TelegramDesktop):
        """
        Creates a SessionManager instance from a Pyrogram string.

        Args:
            string (str): Pyrogram session string.
            api (Type[APIData], optional): API type, default is API.TelegramDesktop.

        Returns:
            SessionManager: An instance initialized from the Pyrogram string.
        """
        session = PyroSession.from_string(string)
        return cls(
            auth_key=session.auth_key,
            dc_id=session.dc_id,
            api=api,
            user_id=session.user_id,
        )

    @classmethod
    def from_tdata_folder(cls, folder: Union[Path, str]):
        """
        Creates a SessionManager instance from a TData session folder.

        Args:
            folder (Union[Path, str]): Path to the TData session folder.

        Returns:
            SessionManager: An instance initialized from the TData session folder.
        """
        session = TDataSession.from_tdata(folder)
        return cls(
            auth_key=session.auth_key,
            dc_id=session.dc_id,
            api=session.api
        )

    async def to_pyrogram_file(self, path: Union[Path, str]):
        """
        Saves the current session as a Pyrogram file.

        Args:
            path (Union[Path, str]): Path to save the Pyrogram file.
        """
        await self.pyrogram.to_file(path)

    def to_pyrogram_string(self) -> str:
        """
        Converts the current session to a Pyrogram session string.

        Returns:
            str: Pyrogram session string.
        """
        return self.pyrogram.to_string()

    async def to_telethon_file(self, path: Union[Path, str]):
        """
        Saves the current session as a Telethon file.

        Args:
            path (Union[Path, str]): Path to save the Telethon file.
        """
        await self.telethon.to_file(path)

    def to_telethon_string(self) -> str:
        """
        Converts the current session to a Telethon session string.

        Returns:
            str: Telethon session string.
        """
        return self.telethon.to_string()

    async def to_tdata_folder(self, path: Union[Path, str]):
        """
        Saves the current session as a TData session folder.

        Args:
            path (Union[Path, str]): Path to save the TData session folder.
        """
        await self.get_user_id()
        self.tdata.to_folder(path)

    @property
    def pyrogram(self) -> PyroSession:
        """
        Returns a PyroSession instance representing the current session.
        """
        return PyroSession(
            dc_id=self.dc_id,
            auth_key=self.auth_key,
            user_id=self.user_id,
        )

    @property
    def telethon(self) -> TeleSession:
        """
        Returns a TeleSession instance representing the current session.
        """
        return TeleSession(
            dc_id=self.dc_id,
            auth_key=self.auth_key,
        )

    @property
    def tdata(self) -> TDataSession:
        """
        Returns a TDataSession instance representing the current session.
        """
        return TDataSession(
            dc_id=self.dc_id,
            auth_key=self.auth_key,
            api=self.api,
            user_id=self.user_id,
        )

    def pyrogram_client(self, proxy=None, no_updates=True):
        """
        Returns a Pyrogram client for the current session.

        Args:
            proxy: Proxy information for the client.
            no_updates (bool): Flag indicating whether to disable updates.

        Returns:
            Pyrogram client instance.
        """
        client = self.pyrogram.client(
            api=self.api,
            proxy=proxy,
            no_updates=no_updates,
        )
        return client

    def telethon_client(self, proxy=None, no_updates=True):
        """
        Returns a Telethon client for the current session.

        Args:
            proxy: Proxy information for the client.
            no_updates (bool): Flag indicating whether to disable updates.

        Returns:
            Telethon client instance.
        """
        client = self.telethon.client(
            api=self.api,
            proxy=proxy,
            no_updates=no_updates,
        )
        return client

    async def validate(self) -> bool:
        """
        Validates the current session.

        Returns:
            bool: Validation status (True if valid, False otherwise).
        """
        user = await self.get_user()
        self.valid = bool(user)
        return self.valid

    async def get_user_id(self) -> int:
        """
        Gets the user ID associated with the current session.

        Returns:
            int: User ID.

        Raises:
            ValidationError: If the user is not available.
        """
        if self.user_id:
            return self.user_id

        user = await self.get_user()

        if user is None:
            raise ValidationError()

        return user.id

    async def get_user(self):
        """
        Gets the user information associated with the current session.

        Returns:
            User: User information.

        Raises:
            ValidationError: If the user is not available.
        """
        async with self as client:
            self.user = await client.get_me()
            if self.user:
                self.user_id = self.user.id
        return self.user
