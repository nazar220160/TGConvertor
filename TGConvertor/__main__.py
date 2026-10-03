"""Command-line interface; string output is suitable for piping."""

import asyncio
import os
import sys
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .api import API, APIData
from .converter import convert as convert_session
from .converter import load_session
from .exceptions import ValidationError

console = Console(stderr=True, markup=False)
app = typer.Typer(
    name="tgconvertor",
    help="Convert Telegram session files, strings and tdata offline.",
    add_completion=False,
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)


class SessionFormat(str, Enum):
    TELETHON = "telethon"
    PYROGRAM = "pyrogram"
    GRAMJS = "gramjs"
    TDATA = "tdata"


class InputType(str, Enum):
    AUTO = "auto"
    FILE = "file"
    STRING = "string"


class APIType(str, Enum):
    DESKTOP = "desktop"
    ANDROID = "android"
    IOS = "ios"
    MACOS = "macos"


def get_api_type(api: APIType) -> APIData:
    return {
        APIType.DESKTOP: API.TelegramDesktop,
        APIType.ANDROID: API.TelegramAndroid,
        APIType.IOS: API.TelegramIOS,
        APIType.MACOS: API.TelegramMacOS,
    }[api]


def _configured_api(api: APIType) -> APIData:
    api_id, api_hash = os.getenv("TGCONVERTOR_API_ID"), os.getenv("TGCONVERTOR_API_HASH")
    if api_id is None and api_hash is None:
        return get_api_type(api)
    if not api_id or not api_hash:
        raise ValidationError("Set both TGCONVERTOR_API_ID and TGCONVERTOR_API_HASH")
    try:
        return APIData(api_id=int(api_id), api_hash=api_hash)
    except ValueError:
        raise ValidationError("Invalid TGCONVERTOR_API_ID or TGCONVERTOR_API_HASH") from None


def _version(value: bool):
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def callback(
    version: Annotated[
        bool,
        typer.Option(
            "--version", callback=_version, is_eager=True, help="Print the installed version."
        ),
    ] = False,
):
    pass


@app.command("convert")
def convert(
    source: Annotated[
        str,
        typer.Argument(help="File/directory, session string, or '-' to read a string from stdin."),
    ],
    from_format: Annotated[SessionFormat, typer.Option("--from", "-f", help="Source format.")],
    to_format: Annotated[SessionFormat, typer.Option("--to", "-t", help="Target format.")],
    output: Annotated[
        str | None,
        typer.Option("--output", "-o", help="New file/directory; omit or use 'string' for stdout."),
    ] = None,
    input_type: Annotated[
        InputType, typer.Option("--input-type", help="Override source detection.")
    ] = InputType.AUTO,
    user_id: Annotated[
        int | None,
        typer.Option("--user-id", min=1, help="Owner ID when the source does not store it."),
    ] = None,
    backend: Annotated[
        str, typer.Option("--backend", help="Output SQLite schema: auto, pyrogram, kurigram.")
    ] = "auto",
    api_type: Annotated[
        APIType, typer.Option("--api", "-a", help="Compatibility API preset.")
    ] = APIType.DESKTOP,
    account_index: Annotated[
        int | None,
        typer.Option(
            "--account-index", min=0, help="Zero-based tdata account; defaults to main account."
        ),
    ] = None,
):
    """Convert without contacting Telegram. Existing output paths are refused."""
    try:
        if source == "-":
            source = sys.stdin.read(513).strip()
            input_type = InputType.STRING
        if backend not in ("auto", "pyrogram", "kurigram"):
            raise ValidationError("backend must be auto, pyrogram, or kurigram")
        destination = None if output in (None, "string") else output
        result = asyncio.run(
            convert_session(
                source,
                from_format.value,
                to_format.value,
                destination,
                input_type=input_type.value,
                api=_configured_api(api_type),
                user_id=user_id,
                backend=backend,
                account_index=account_index,
                passcode=os.getenv("TGCONVERTOR_TDATA_PASSCODE", ""),
                output_passcode=os.getenv("TGCONVERTOR_OUTPUT_PASSCODE", ""),
            )
        )
        if isinstance(result, str):
            typer.echo(result)
        else:
            console.print(f"Saved to: {result}")
    except (ValueError, OSError, ImportError) as exc:
        console.print(f"Error: {exc}")
        raise typer.Exit(1) from None


@app.command()
def info(
    session_path: Annotated[Path, typer.Argument(help="Session file or tdata directory.")],
    format: Annotated[SessionFormat, typer.Option("--format", "-f")],
    account_index: Annotated[int | None, typer.Option("--account-index", min=0)] = None,
):
    """Inspect local metadata. Authorization keys and strings are never displayed."""
    try:
        session = asyncio.run(
            load_session(
                session_path,
                format.value,
                input_type="file",
                account_index=account_index,
                passcode=os.getenv("TGCONVERTOR_TDATA_PASSCODE", ""),
            )
        )
        table = Table(title="Session information")
        table.add_column("Property")
        table.add_column("Value")
        for key, value in {
            "DC ID": session.dc_id,
            "User ID": session.user_id if session.user_id is not None else "Unknown",
            "API ID (conversion)": session.api_id,
            "Test mode": session.test_mode,
            "Bot": session.is_bot,
            "Authorization": "Not checked (offline)",
        }.items():
            table.add_row(key, str(value))
        console.print(table)
    except (ValueError, OSError, ImportError) as exc:
        console.print(f"Error: {exc}")
        raise typer.Exit(1) from None


@app.command()
def list_formats():
    """List supported input/output formats."""
    table = Table(title="Supported session formats")
    table.add_column("Format")
    table.add_column("Input / output")
    table.add_row("gramjs", "GramJS 2 StringSession strings and UTF-8 text files")
    table.add_row("telethon", "Telethon 1.x SQLite files and strings")
    table.add_row(
        "pyrogram", "Pyrogram 2 / Kurigram SQLite files and strings (user_id required for output)"
    )
    table.add_row(
        "tdata", "Telegram Desktop directories (optional tdata extra; user accounts only)"
    )
    console.print(table)
    console.print("API presets: desktop, android, ios, macos")


def main():
    app()


if __name__ == "__main__":
    main()
