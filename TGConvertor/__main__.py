import asyncio
from enum import Enum
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .manager import SessionManager
from .exceptions import ValidationError
from opentele.api import API


console = Console()
app = typer.Typer(
    name="tgconvertor",
    help="[bold green]Telegram Session Converter[/bold green] - Convert between different Telegram session formats",
    add_completion=False,
)


def is_source_file_check(s: str) -> bool:
    try:
        p = Path(s)
        # проверяем, есть ли имя файла и расширение
        return bool(p.name and p.suffix)
    except Exception:
        return False


class SessionFormat(str, Enum):
    """Supported session formats"""

    TELETHON = "telethon"
    PYROGRAM = "pyrogram"
    TDATA = "tdata"


class InputType(str, Enum):
    """Type of input: file or string"""

    FILE = "file"
    STRING = "string"


class APIType(str, Enum):
    """Available Telegram API types"""

    DESKTOP = "desktop"
    ANDROID = "android"
    IOS = "ios"
    MACOS = "macos"


def get_api_type(api: APIType) -> API:
    """Convert string API type to opentele.API type"""
    return {
        APIType.DESKTOP: API.TelegramDesktop,
        APIType.ANDROID: API.TelegramAndroid,
        APIType.IOS: API.TelegramIOS,
        APIType.MACOS: API.TelegramMacOS,
    }[api]


def validate_session_path(value: Path) -> Path:
    """Validate that the session file/directory exists"""
    if value and not value.exists():
        raise typer.BadParameter(f"Session path does not exist: {value}")
    return value


@app.command()
def convert(
    source: str = typer.Argument(
        ...,
        help="Source session (file path or session string)",
    ),
    from_format: SessionFormat = typer.Option(
        ...,
        "--from",
        "-f",
        help="Source session format",
        show_default=False,
    ),
    to_format: SessionFormat = typer.Option(
        ...,
        "--to",
        "-t",
        help="Target session format",
        show_default=False,
    ),
    output: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output destination (file path or 'string' for string output)",
        show_default=False,
    ),
    api_type: APIType = typer.Option(
        APIType.DESKTOP,
        "--api",
        "-a",
        help="Telegram API type to use for the conversion",
    ),
):
    """
    Convert Telegram session between different formats. Supports both files and strings.

    Examples:
        • Convert file to file:
          $ tgconvertor convert session.session -f telethon -t pyrogram -o new_session.session

        • Convert string to file:
          $ tgconvertor convert "1:AAFqwer..." -f telethon -t pyrogram -o session.session

        • Convert file to string:
          $ tgconvertor convert session.session -f telethon -t pyrogram -o string

        • Convert string to string:
          $ tgconvertor convert "1:AAFqwer..." -f telethon -t pyrogram -o string

        • Convert using specific API type:
          $ tgconvertor convert session.session -f telethon -t pyrogram --api android
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Converting session...", total=None)

            # Process input and output
            api = get_api_type(api_type)

            # Determine if source is a file or string
            is_source_file = is_source_file_check(source)
            # Determine output type
            want_string_output = output == "string" if output else False
            output_path = None if want_string_output else (output or source)

            # Perform conversion
            result = asyncio.run(
                _convert_universal(
                    source=source,
                    is_source_file=is_source_file,
                    from_format=from_format,
                    to_format=to_format,
                    want_string_output=want_string_output,
                    output_path=output_path,
                    api=api,
                )
            )

            progress.update(task, completed=True)

        console.print(f"[green]✓[/green] Session successfully converted!")
        if want_string_output and result:
            console.print("\n[bold]Converted string:[/bold]")
            print(result)
        elif output_path:
            console.print(f"[bold]Output saved to:[/bold] {output_path}")

    except ValidationError as e:
        console.print_exception(show_locals=False)
        raise typer.Exit(1)
    except Exception as e:
        console.print_exception(show_locals=False)
        raise typer.Exit(1)


@app.command()
def info(
    session_path: Path = typer.Argument(
        ...,
        help="Path to the session file/directory",
        callback=validate_session_path,
        show_default=False,
    ),
    format: SessionFormat = typer.Option(
        ...,
        "--format",
        "-f",
        help="Session format",
        show_default=False,
    ),
):
    """
    Display information about a Telegram session.

    Examples:
        • Show Telethon session info:
          $ tgconvertor info session.session -f telethon

        • Show Pyrogram session info:
          $ tgconvertor info my_session.session -f pyrogram
    """
    try:
        # Get session info based on format
        info = asyncio.run(_get_session_info(session_path, format))

        # Create and populate table
        table = Table(title="Session Information")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        for key, value in info.items():
            table.add_row(key, str(value))

        console.print(table)

    except ValidationError as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] An unexpected error occurred: {str(e)}")
        raise typer.Exit(1)


@app.command()
def list_formats():
    """
    List all supported session formats and API types.
    """
    # Session formats table
    formats_table = Table(title="Supported Session Formats")
    formats_table.add_column("Format", style="cyan")
    formats_table.add_column("Description", style="green")

    formats_table.add_row("telethon", "Telethon session format (.session files)")
    formats_table.add_row("pyrogram", "Pyrogram session format (.session files)")
    formats_table.add_row("tdata", "Telegram Desktop tdata format (directory)")

    # API types table
    api_table = Table(title="Available API Types")
    api_table.add_column("Type", style="cyan")
    api_table.add_column("Description", style="green")

    api_table.add_row("desktop", "Telegram Desktop client")
    api_table.add_row("android", "Telegram Android client")
    api_table.add_row("ios", "Telegram iOS client")
    api_table.add_row("macos", "Telegram macOS client")

    console.print(formats_table)
    console.print()
    console.print(api_table)


async def _convert_universal(
    source: str,
    from_format: SessionFormat,
    to_format: SessionFormat,
    api: API,
    is_source_file: bool = False,
    want_string_output: bool = False,
    output_path: Optional[str] = None,
) -> Optional[str]:
    """Universal conversion function that handles both files and strings"""

    # Load session from source
    if is_source_file:
        source_path = Path(source)
        if not source_path.exists():
            raise ValidationError(
                f"Source session file/directory does not exist: {source}"
            )
        if from_format == SessionFormat.TELETHON:
            session = await SessionManager.from_telethon_file(source_path, api)
        elif from_format == SessionFormat.PYROGRAM:
            session = await SessionManager.from_pyrogram_file(source_path, api)
        elif from_format == SessionFormat.TDATA:
            session = await SessionManager.from_tdata_folder(source_path, api)
        else:
            raise ValidationError(f"Unsupported source format: {from_format}")
    else:
        if from_format == SessionFormat.TELETHON:
            session = SessionManager.from_telethon_string(source, api)
        elif from_format == SessionFormat.PYROGRAM:
            session = SessionManager.from_pyrogram_string(source, api)
        elif from_format == SessionFormat.TDATA:
            session = SessionManager.from_tdata_folder(source)
        else:
            raise ValidationError(f"Format {from_format} doesn't support string input")
    # Convert to target format
    if want_string_output:
        if to_format == SessionFormat.TELETHON:
            return session.to_telethon_string()
        elif to_format == SessionFormat.PYROGRAM:
            return session.to_pyrogram_string()
        else:
            raise ValidationError(f"Format {to_format} doesn't support string output")
    else:
        output = Path(output_path) if output_path else Path(source)
        if to_format == SessionFormat.TELETHON:
            await session.to_telethon_file(output)
        elif to_format == SessionFormat.PYROGRAM:
            await session.to_pyrogram_file(output)
        elif to_format == SessionFormat.TDATA:
            await session.to_tdata_folder(output)
        else:
            raise ValidationError(f"Unsupported target format: {to_format}")
        return None


async def _get_session_info(path: Path, format: SessionFormat) -> dict:
    """Get session information based on format"""
    try:
        if format == SessionFormat.TELETHON:
            session = await SessionManager.from_telethon_file(path)
        elif format == SessionFormat.PYROGRAM:
            session = await SessionManager.from_pyrogram_file(path)
        elif format == SessionFormat.TDATA:
            session = await SessionManager.from_tdata_folder(path)
        else:
            raise ValidationError(f"Unsupported format: {format}")

        return {
            "DC ID": session.dc_id,
            "User ID": session.user_id or "Unknown",
            "Phone": session.phone_number or "Unknown",
            "Valid": session.valid or "Unknown",
        }
    except Exception as e:
        raise ValidationError(f"Failed to read session: {str(e)}")


def main():
    """Entry point for the CLI"""
    app()


if __name__ == "__main__":
    app()
