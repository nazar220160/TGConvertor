import argparse
import asyncio
import sys
from pathlib import Path
from TGConvertor import SessionManager
from TGConvertor.exceptions import ValidationError
from opentele.api import API, APIData # For API.Custom

# Helper to choose API
def get_api(api_id_str: str | None, api_hash_str: str | None) -> APIData:
    if api_id_str and api_hash_str:
        try:
            api_id = int(api_id_str)
            return API.Custom(api_id, api_hash_str)
        except ValueError:
            print("Error: api_id must be an integer.", file=sys.stderr)
            sys.exit(1)
    return API.TelegramDesktop # Default if not specified


async def main_async():
    parser = argparse.ArgumentParser(description="Convert Telegram session formats.")
    parser.add_argument("input_type", choices=['pyro_str', 'pyro_file', 'tele_str', 'tele_file', 'tdata_folder'],
                        help="Input session type.")
    parser.add_argument("input_value", help="Input session string or path to session file/folder.")
    parser.add_argument("output_type", choices=['pyro_str', 'pyro_file', 'tele_str', 'tele_file', 'tdata_folder'],
                        help="Output session type.")
    parser.add_argument("output_location", nargs='?', default="stdout",
                        help="Output file/folder path, or 'stdout' to print session string (default: stdout for string types).")

    parser.add_argument("--api_id", help="Custom API ID (integer).")
    parser.add_argument("--api_hash", help="Custom API Hash.")
    # Add other relevant options like proxy if necessary later

    args = parser.parse_args()

    custom_api = get_api(args.api_id, args.api_hash)
    sm = None

    try:
        # Load session
        if args.input_type == 'pyro_str':
            sm = SessionManager.from_pyrogram_string(args.input_value, api=custom_api)
        elif args.input_type == 'pyro_file':
            if not Path(args.input_value).exists():
                print(f"Error: Input file {args.input_value} not found.", file=sys.stderr)
                sys.exit(1)
            sm = await SessionManager.from_pyrogram_file(Path(args.input_value), api=custom_api)
        elif args.input_type == 'tele_str':
            sm = SessionManager.from_telethon_string(args.input_value, api=custom_api)
        elif args.input_type == 'tele_file':
            if not Path(args.input_value).exists():
                print(f"Error: Input file {args.input_value} not found.", file=sys.stderr)
                sys.exit(1)
            sm = await SessionManager.from_telethon_file(Path(args.input_value), api=custom_api)
        elif args.input_type == 'tdata_folder':
            if not Path(args.input_value).is_dir():
                print(f"Error: Input TData folder {args.input_value} not found or not a directory.", file=sys.stderr)
                sys.exit(1)
            sm = SessionManager.from_tdata_folder(Path(args.input_value)) # api is set by from_tdata_folder
            # If custom_api was provided and differs from TData's default, SessionManager will use custom_api for client ops
            if args.api_id and args.api_hash: # If user specified custom API, let it override TData's default for subsequent ops
                sm.api = custom_api


        if not sm:
            print("Error: Could not load session.", file=sys.stderr) # Should not happen if choices are handled
            sys.exit(1)

        # Perform conversion
        output_path = None
        if args.output_location != "stdout":
            output_path = Path(args.output_location)

        if args.output_type == 'pyro_str':
            session_string = sm.to_pyrogram_string()
            if output_path: # Treat as file path to write string into
                 output_path.write_text(session_string)
                 print(f"Pyrogram session string saved to: {output_path}")
            else:
                 print(session_string)
        elif args.output_type == 'pyro_file':
            if not output_path:
                print("Error: Output file path required for pyro_file.", file=sys.stderr)
                sys.exit(1)
            await sm.to_pyrogram_file(output_path)
            print(f"Pyrogram session file saved to: {output_path}")
        elif args.output_type == 'tele_str':
            session_string = sm.to_telethon_string()
            if output_path:
                 output_path.write_text(session_string)
                 print(f"Telethon session string saved to: {output_path}")
            else:
                print(session_string)
        elif args.output_type == 'tele_file':
            if not output_path:
                print("Error: Output file path required for tele_file.", file=sys.stderr)
                sys.exit(1)
            await sm.to_telethon_file(output_path)
            print(f"Telethon session file saved to: {output_path}")
        elif args.output_type == 'tdata_folder':
            if not output_path:
                print("Error: Output folder path required for tdata_folder.", file=sys.stderr)
                sys.exit(1)
            # To convert to TData, user_id is needed. SessionManager's to_tdata_folder calls get_user_id.
            # This might require network and could fail if session is invalid or api keys are bad.
            # The CLI should inform about this.
            print("Notice: Converting to TData may require fetching user info if not already available.")
            print("This might involve a network request using the session's API credentials.")
            try:
                await sm.to_tdata_folder(output_path)
                print(f"TData session folder saved to: {output_path}")
            except ValidationError as e:
                print(f"Error during TData conversion (possibly fetching user info): {e}", file=sys.stderr)
                sys.exit(1)
            except ConnectionError as e:
                 print(f"Connection error during TData conversion (possibly fetching user info): {e}", file=sys.stderr)
                 sys.exit(1)
            except Exception as e: # Catch other potential errors from opentele or client ops
                print(f"An unexpected error occurred during TData conversion: {e}", file=sys.stderr)
                sys.exit(1)

        print("Conversion successful.")

    except FileNotFoundError as e: # Should be caught by specific checks, but as a fallback
        print(f"Error: File not found - {e}", file=sys.stderr)
        sys.exit(1)
    except ValidationError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        # For debugging, one might want to print traceback:
        # import traceback
        # traceback.print_exc()
        sys.exit(1)

def main():
    asyncio.run(main_async())

if __name__ == '__main__':
    main()
