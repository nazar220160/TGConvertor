"""GramJS 2.x StringSession codec; text files contain the same versioned string."""

import asyncio
import base64
import ipaddress
import os
import re
import struct
import tempfile
from pathlib import Path

from ..data_center import DataCenter
from ..exceptions import ValidationError
from ._utils import decode_string, validate_fields
from .tele import TeleSession


class GramSession:
    CURRENT_VERSION = "1"

    def __init__(
        self,
        *,
        dc_id: int,
        auth_key: bytes,
        server_address: str | None = None,
        port: int | None = None,
        test_mode: bool = False,
    ):
        validate_fields(dc_id, auth_key)
        if type(test_mode) not in (bool, int) or test_mode not in (False, True):
            raise ValidationError("test_mode must be a boolean")
        if server_address is None:
            server_address, default_port = DataCenter(dc_id, test_mode)
        else:
            default_port = 80 if test_mode else 443
        if not isinstance(server_address, str):
            raise ValidationError("GramJS server_address must be an IP address or ASCII hostname")
        try:
            address = ipaddress.ip_address(server_address)
            server_address = str(address) if len(str(address)) >= 4 else address.exploded
        except ValueError:
            labels = server_address.removesuffix(".").split(".")
            if not all(
                re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?", label)
                for label in labels
            ):
                raise ValidationError(
                    "GramJS server_address must be an IP address or ASCII hostname"
                ) from None
        # Upstream's loader mistakes a 352-character body for a Telethon IPv4 string.
        if not 4 <= len(server_address.encode("ascii")) <= 100:
            raise ValidationError("GramJS server_address must contain 4 to 100 ASCII bytes")
        self.port = default_port if port is None else port
        # GramJS uses a signed 16-bit port in both its writer and reader.
        if type(self.port) is not int or not 0 < self.port <= 32767:
            raise ValidationError("GramJS port must be an integer between 1 and 32767")
        self.dc_id, self.auth_key, self.server_address = dc_id, auth_key, server_address
        self.test_mode = bool(test_mode) or server_address in (
            set(DataCenter.TEST.values()) | set(DataCenter.TEST_IPV6.values())
        )

    @classmethod
    def from_string(cls, string: str):
        if not isinstance(string, str) or not string.startswith(cls.CURRENT_VERSION):
            raise ValidationError("Unsupported GramJS string version (expected 1)")
        raw = decode_string(string[1:])
        if len(raw) == 263 and len(string[1:]) == 352:
            tele = TeleSession.from_string(string)
            return cls(
                dc_id=tele.dc_id,
                auth_key=tele.auth_key,
                server_address=tele.server_address,
                port=tele.port,
            )
        if len(raw) < 262:
            raise ValidationError("Invalid GramJS session string length")
        size = struct.unpack(">h", raw[1:3])[0]
        if size > 100 and len(raw) == 275:
            tele = TeleSession.from_string(string)
            return cls(
                dc_id=tele.dc_id,
                auth_key=tele.auth_key,
                server_address=tele.server_address,
                port=tele.port,
            )
        if not 1 <= size <= 100 or len(raw) != 261 + size:
            raise ValidationError("Invalid GramJS session string length")
        try:
            address = raw[3 : 3 + size].decode("ascii")
        except UnicodeDecodeError:
            raise ValidationError(
                "GramJS server_address must be an IP address or ASCII hostname"
            ) from None
        return cls(
            dc_id=raw[0],
            server_address=address,
            port=struct.unpack(">h", raw[3 + size : 5 + size])[0],
            auth_key=raw[5 + size :],
        )

    def to_string(self) -> str:
        address = self.server_address.encode("ascii")
        raw = (
            struct.pack(">Bh", self.dc_id, len(address))
            + address
            + struct.pack(">h", self.port)
            + self.auth_key
        )
        return self.CURRENT_VERSION + base64.b64encode(raw).decode("ascii")

    @classmethod
    async def from_file(cls, path: str | Path):
        def read():
            with Path(path).open("rb") as source:
                data = source.read(1025)
            if len(data) > 1024:
                raise ValidationError("GramJS text file exceeds the session string limit")
            try:
                return cls.from_string(data.decode("utf-8-sig").strip())
            except UnicodeDecodeError:
                raise ValidationError(
                    "GramJS text file must contain a UTF-8 StringSession"
                ) from None

        return await asyncio.to_thread(read)

    async def to_file(self, path: str | Path) -> None:
        data = (self.to_string() + "\n").encode("ascii")

        def write():
            destination = Path(path)
            if destination.exists() or destination.is_symlink():
                raise FileExistsError(f"Output already exists: {destination}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            fd, name = tempfile.mkstemp(
                prefix=".tgconvertor-", suffix=".txt", dir=destination.parent
            )
            temporary = Path(name)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(data)
                os.link(temporary, destination)
            finally:
                temporary.unlink(missing_ok=True)

        await asyncio.to_thread(write)
