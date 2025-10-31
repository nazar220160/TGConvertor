from pathlib import Path
from typing import Union

from ..api import API, APIData

try:
    from opentele.td import TDesktop, Account, AuthKeyType, AuthKey # type: ignore
    from opentele.td.configs import DcId # type: ignore
    HAS_OPENTELE_TD = True
except ImportError:
    HAS_OPENTELE_TD = False
    TDesktop = None
    Account = None
    AuthKeyType = None
    AuthKey = None
    DcId = None


class TDataSession:
    def __init__(
            self,
            *,
            dc_id: int,
            auth_key: bytes,
            user_id: int,
            api: APIData = API.TelegramDesktop,
    ):
        self.dc_id = dc_id
        self.auth_key = auth_key
        self.user_id = user_id
        self.api = api

    @classmethod
    def from_tdata(cls, tdata_folder: Union[Path, str]):
        if not HAS_OPENTELE_TD:
            raise ImportError(
                "TData support requires opentele package. "
                "Please install it with: pip install tgconvertor[tdata] or pip install opentele"
            )
        
        tdata_folder = Path(tdata_folder)
        
        if not tdata_folder.exists():
            raise FileNotFoundError(tdata_folder)

        client = TDesktop(basePath=tdata_folder)
        account = client.mainAccount

        return cls(
            auth_key=account.authKey.key,
            user_id=account.UserId,
            dc_id=account.MainDcId
        )

    def to_folder(self, path: Union[Path, str]):
        if not HAS_OPENTELE_TD:
            raise ImportError(
                "TData support requires opentele package. "
                "Please install it with: pip install tgconvertor[tdata] or pip install opentele"
            )
        
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        dc_id = DcId(self.dc_id)
        auth_key = AuthKey(self.auth_key, AuthKeyType.ReadFromFile, dc_id)

        if self.user_id is None:
            raise ValueError("user_id is None")

        client = TDesktop()
        client._TDesktop__generateLocalKey()
        account = Account(owner=client, api=self.api)
        account._setMtpAuthorizationCustom(dc_id, self.user_id, [auth_key])
        client._addSingleAccount(account)

        client.SaveTData(path / "tdata")
        
