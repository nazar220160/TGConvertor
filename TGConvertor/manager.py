from pathlib import Path
from typing import Union

from .api import API, APIData
try:
    from .sessions.pyro import PyroSession
except ImportError:
    PyroSession = None
try:
    from .sessions.tele import TeleSession
except ImportError:
    TeleSession = None
try:
    from .sessions.tdata import TDataSession
except ImportError:
    TDataSession = None
from .exceptions import ValidationError


class SessionManager:
    def __init__(
        self,
        dc_id: int,
        auth_key: bytes,
        user_id: None | int = None,
        valid: None | bool = None,
        api: APIData = API.TelegramDesktop,
        phone_number: str | None = None,
        test_mode: bool = False,
        is_bot: bool = False,
        api_id: None | int = None,
    ):
        """
        Initializes a SessionManager instance with the specified parameters.

        Args:
            dc_id (int): Data center ID.
            auth_key (bytes): Authentication key.
            user_id (None|int, optional): User ID, default is None.
            valid (None|bool, optional): Validation status, default is None.
            api (APIData, optional): API data, default is API.TelegramDesktop.
            phone_number (str|None, optional): Phone number, default is None.
            test_mode (bool, optional): Test mode flag, default is False.
            is_bot (bool, optional): Is bot flag, default is False.
            api_id (int|None, optional): API ID from session, default is None.
        """

        self.dc_id = dc_id
        self.auth_key = auth_key
        self.user_id = user_id
        self.valid = valid
        self.api = api.copy()
        self.user = None
        self.client = None
        self.phone_number = phone_number
        self.test_mode = test_mode
        self.is_bot = is_bot
        self.api_id = api_id or api.api_id

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
        await self.client.disconnect() # type: ignore
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
            api (APIData, optional): API data, default is API.TelegramDesktop.

        Returns:
            SessionManager: An instance initialized from the Telethon file.
        """
        if TeleSession is None:
            raise ImportError("Must install telethon to use Telethon sessions.")
        session = await TeleSession.from_file(Path(file))
        return cls(
            dc_id=session.dc_id,
            auth_key=session.auth_key,
            api=api,
            phone_number=session.phone_number, # type: ignore
            user_id=session.user_id,
        )

    @classmethod
    def from_telethon_string(cls, string: str, api=API.TelegramDesktop):
        """
        Creates a SessionManager instance from a Telethon string.

        Args:
            string (str): Telethon session string.
            api (APIData, optional): API data, default is API.TelegramDesktop.

        Returns:
            SessionManager: An instance initialized from the Telethon string.
        """
        if TeleSession is None:
            raise ImportError("Must install telethon to use Telethon sessions.")
        session = TeleSession.from_string(string)
        return cls(dc_id=session.dc_id, auth_key=session.auth_key, api=api)

    @classmethod
    async def from_pyrogram_file(cls, file: Union[Path, str], api=API.TelegramDesktop):
        """
        Creates a SessionManager instance from a Pyrogram file.

        Args:
            file (Union[Path, str]): Path to the Pyrogram file.
            api (APIData, optional): API data, default is API.TelegramDesktop.

        Returns:
            SessionManager: An instance initialized from the Pyrogram file.
        """
        if PyroSession is None:
            raise ImportError("Must install pyrogram or kurigram to use Pyrogram sessions.")
        session = await PyroSession.from_file(file)
        return cls(
            auth_key=session.auth_key,
            dc_id=session.dc_id,
            api=api,
            user_id=session.user_id,
            test_mode=session.test_mode,
            is_bot=session.is_bot,
            api_id=session.api_id,
        )

    @classmethod
    def from_pyrogram_string(cls, string: str, api=API.TelegramDesktop):
        """
        Creates a SessionManager instance from a Pyrogram string.

        Args:
            string (str): Pyrogram session string.
            api (APIData, optional): API data, default is API.TelegramDesktop.

        Returns:
            SessionManager: An instance initialized from the Pyrogram string.
        """
        if PyroSession is None:
            raise ImportError("Must install pyrogram or kurigram to use Pyrogram sessions.")
        session = PyroSession.from_string(string)
        return cls(
            auth_key=session.auth_key,
            dc_id=session.dc_id,
            api=api,
            user_id=session.user_id,
            test_mode=session.test_mode,
            is_bot=session.is_bot,
            api_id=session.api_id,
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
        if not TDataSession:
            raise ImportError(
                "TData support requires opentele package. "
                "Please install it with: pip install tgconvertor[tdata] or pip install opentele"
            )
        session = TDataSession.from_tdata(folder)
        return cls(auth_key=session.auth_key, dc_id=session.dc_id, api=session.api)

    async def to_pyrogram_file(self, path: Union[Path, str]):
        """
        Saves the current session as a Pyrogram file.

        Args:
            path (Union[Path, str]): Path to save the Pyrogram file.
        """
        await self.pyrogram.to_file(Path(path))

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
        await self.telethon.to_file(Path(path))

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

        if PyroSession is None:
            raise ImportError("Must install pyrogram or kurigram to use Pyrogram sessions.")

        return PyroSession(
            dc_id=self.dc_id,
            auth_key=self.auth_key,
            user_id=self.user_id,
            api_id=self.api_id,
            test_mode=self.test_mode,
            is_bot=self.is_bot,
        )

    @property
    def telethon(self) -> TeleSession:
        """
        Returns a TeleSession instance representing the current session.
        """
        if TeleSession is None:
            raise ImportError("Must install telethon to use Telethon sessions.")
        return TeleSession(
            dc_id=self.dc_id,
            auth_key=self.auth_key,
        )

    @property
    def tdata(self) -> TDataSession:
        """
        Returns a TDataSession instance representing the current session.
        """
        if not TDataSession:
            raise ImportError(
                "TData support requires opentele package. "
                "Please install it with: pip install tgconvertor[tdata] or pip install opentele"
            )
        if self.user_id is None:
            raise ValueError("user_id is required for TDataSession")
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

        return user.id # type: ignore

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
                self.user_id = self.user.id # type: ignore
        return self.user
