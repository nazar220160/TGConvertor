"""Convenience conversion API shared with the CLI."""

import asyncio
from pathlib import Path

from .api import API, APIData
from .exceptions import ValidationError
from .manager import SessionManager
from .sessions._utils import validate_fields

FORMATS = ("telethon", "pyrogram", "gramjs", "tdata")


async def load_session(
    source: str | Path,
    from_format: str,
    *,
    input_type: str = "auto",
    api: APIData = API.TelegramDesktop,
    passcode: str = "",
    account_index: int | None = None,
) -> SessionManager:
    if from_format not in FORMATS:
        raise ValidationError(f"Unsupported source format: {from_format}")
    if input_type not in ("auto", "file", "string"):
        raise ValidationError("input_type must be auto, file, or string")
    if from_format == "tdata":
        if input_type == "string":
            raise ValidationError("tdata does not support string input")
        return await asyncio.to_thread(
            SessionManager.from_tdata_folder,
            source,
            passcode=passcode,
            account_index=account_index,
            api=api,
        )
    if input_type == "auto" and from_format == "gramjs":
        # Standard Base64 may contain '/', so it must not be treated as a path.
        input_type = (
            "string"
            if isinstance(source, str)
            and len(source) >= 128
            and not any(c in source for c in ".\\")
            else "file"
        )
    if input_type == "auto":
        # URL-safe session strings have no path separators or dots.
        input_type = (
            "file"
            if isinstance(source, Path) or any(c in str(source) for c in ".\\/")
            else "string"
        )
        if input_type == "string" and len(str(source)) < 128:
            input_type = "file"
    if input_type == "file":
        loader = getattr(SessionManager, f"from_{from_format}_file")
        return await loader(source, api)
    return getattr(SessionManager, f"from_{from_format}_string")(str(source), api)


async def convert(
    source: str | Path,
    from_format: str,
    to_format: str,
    output: str | Path | None = None,
    *,
    user_id: int | None = None,
    api: APIData = API.TelegramDesktop,
    input_type: str = "auto",
    backend: str = "auto",
    passcode: str = "",
    output_passcode: str = "",
    account_index: int | None = None,
) -> str | Path:
    """Convert offline. Omit output for a string; files/directories must be new."""
    if to_format not in FORMATS:
        raise ValidationError(f"Unsupported target format: {to_format}")
    if output is None and to_format == "tdata":
        raise ValidationError("tdata requires an output directory")
    if output is not None and (Path(output).exists() or Path(output).is_symlink()):
        raise FileExistsError(f"Output already exists: {output}")
    session = await load_session(
        source,
        from_format,
        input_type=input_type,
        api=api,
        passcode=passcode,
        account_index=account_index,
    )
    if user_id is not None:
        validate_fields(session.dc_id, session.auth_key, user_id)
        if session.user_id is not None and session.user_id != user_id:
            raise ValidationError("Supplied user_id differs from the source session owner")
        session.user_id = user_id
    if output is None:
        return getattr(session, f"to_{to_format}_string")()
    path = Path(output)
    if to_format == "tdata":
        await session.to_tdata_folder(path, passcode=output_passcode)
    elif to_format == "pyrogram":
        await session.to_pyrogram_file(path, backend=backend)
    elif to_format == "gramjs":
        await session.to_gramjs_file(path)
    else:
        await session.to_telethon_file(path)
    return path
