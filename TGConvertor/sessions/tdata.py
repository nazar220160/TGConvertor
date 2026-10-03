"""Optional OpenTele2 adapter for Telegram Desktop tdata directories."""

import os
import shutil
import tempfile
from pathlib import Path

from ..api import API, APIData
from ..exceptions import MissingDependencyError, ValidationError
from ._utils import validate_fields


def _validate_passcode(passcode: str) -> None:
    if not isinstance(passcode, str) or not passcode.isascii():
        raise ValidationError("tdata passcode must be an ASCII string (OpenTele2 limitation)")


def _opentele():
    try:
        from opentele2.api import APIData as OpenTeleAPIData
        from opentele2.exception import OpenTeleException
        from opentele2.td import Account, AuthKey, AuthKeyType, TDesktop
        from opentele2.td.configs import DcId
    except ImportError:
        raise MissingDependencyError(
            'Install tdata support with: pip install "tgconvertor[tdata]"'
        ) from None
    return TDesktop, Account, AuthKey, AuthKeyType, DcId, OpenTeleAPIData, OpenTeleException


class TDataSession:
    def __init__(
        self, *, dc_id: int, auth_key: bytes, user_id: int, api: APIData = API.TelegramDesktop
    ):
        validate_fields(dc_id, auth_key, user_id)
        if user_id is None:
            raise ValidationError("tdata requires user_id")
        self.dc_id, self.auth_key, self.user_id = dc_id, auth_key, user_id
        self.api = api.copy()

    @classmethod
    def from_tdata(
        cls, tdata_folder: str | Path, *, passcode: str = "", account_index: int | None = None
    ):
        _validate_passcode(passcode)
        path = Path(tdata_folder)
        if not path.is_dir():
            raise FileNotFoundError(f"tdata directory does not exist: {path}")
        TDesktop, *_, OpenTeleException = _opentele()
        try:
            desktop = TDesktop(basePath=str(path), passcode=passcode)
            if not desktop.isLoaded() or not desktop.accounts:
                raise ValidationError("No authorized accounts found in tdata")
            if account_index is None:
                account = desktop.mainAccount
            elif type(account_index) is int and 0 <= account_index < len(desktop.accounts):
                account = desktop.accounts[account_index]
            else:
                raise ValidationError("account_index is out of range")
            return cls(
                dc_id=int(account.MainDcId), auth_key=account.authKey.key, user_id=account.UserId
            )
        except ValidationError:
            raise
        except (Exception, OpenTeleException):
            raise ValidationError(
                "Cannot read tdata; check the folder and local passcode"
            ) from None

    def to_folder(self, path: str | Path, *, passcode: str = "") -> None:
        """Write directly to a new directory (no implicit extra 'tdata' level)."""
        _validate_passcode(passcode)
        path = Path(path)
        if path.exists() or path.is_symlink():
            raise FileExistsError(f"Output already exists: {path}")
        TDesktop, Account, AuthKey, AuthKeyType, DcId, OpenTeleAPIData, OpenTeleException = (
            _opentele()
        )
        api = OpenTeleAPIData(**vars(self.api))
        desktop = TDesktop(api=api)
        # Use a fresh local encryption key instead of OpenTele's fixed performance-mode key.
        desktop.kPerformanceMode = False
        account = Account(owner=desktop, api=api)
        dc_id = DcId(self.dc_id)
        # OpenTele has no public constructor from a raw authorization key.
        account._setMtpAuthorizationCustom(
            dc_id, self.user_id, [AuthKey(self.auth_key, AuthKeyType.ReadFromFile, dc_id)]
        )
        desktop._addSingleAccount(account)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=".tgconvertor-", dir=path.parent))
        reserved = False
        try:
            if not desktop.SaveTData(str(temporary), passcode=passcode):
                raise ValidationError("OpenTele could not write tdata")
            for item in temporary.rglob("*"):
                item.chmod(0o700 if item.is_dir() else 0o600)
            # Reserve exclusively before moving files, so a concurrent writer is never overwritten.
            path.mkdir(mode=0o700)
            reserved = True
            for item in temporary.iterdir():
                os.rename(item, path / item.name)
        except BaseException as exc:
            if reserved:
                shutil.rmtree(path)
            if isinstance(exc, OpenTeleException):
                raise ValidationError("OpenTele2 could not write tdata") from None
            raise
        finally:
            shutil.rmtree(temporary)
