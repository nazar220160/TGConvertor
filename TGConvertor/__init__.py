"""Telegram authorization conversion without implicit network access."""

from importlib.metadata import PackageNotFoundError, version

from .api import API, APIData
from .converter import convert
from .exceptions import MissingDependencyError, ValidationError
from .manager import SessionManager
from .sessions.gramjs import GramSession
from .sessions.pyro import PyroSession
from .sessions.tdata import TDataSession
from .sessions.tele import TeleSession

try:
    __version__ = version("tgconvertor")
except PackageNotFoundError:
    __version__ = "0+unknown"

__all__ = [
    "API",
    "APIData",
    "SessionManager",
    "PyroSession",
    "GramSession",
    "TeleSession",
    "TDataSession",
    "ValidationError",
    "MissingDependencyError",
    "convert",
    "__version__",
]
