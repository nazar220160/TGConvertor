"""Native SDK adapters for opt-in live checks; no login or authorization creation."""

import asyncio
import hmac
from contextlib import suppress
from pathlib import Path

from TGConvertor import SessionManager, convert
from TGConvertor.__main__ import app

from .test_conversion_matrix import (
    OUTPUT_PASSCODE,
    SOURCE_PASSCODE,
    STRING_KINDS,
    cli_args,
    destination_for,
    format_backend,
    format_of,
)


async def native_client(kind, value, api, *, passcode=""):
    """Open the actual output with its upstream SDK, independently of our readers."""
    if kind.startswith("telethon"):
        from telethon import TelegramClient
        from telethon.sessions import SQLiteSession, StringSession

        storage = StringSession(value) if kind in STRING_KINDS else SQLiteSession(str(value))
        client = TelegramClient(
            storage,
            api.api_id,
            api.api_hash,
            device_model=api.device_model,
            system_version=api.system_version,
            app_version=api.app_version,
            use_ipv6=":" in storage.server_address,
            receive_updates=False,
            connection_retries=1,
            request_retries=0,
            flood_sleep_threshold=0,
        )
        return client, "telethon"
    if kind.startswith("tdata"):
        from opentele2.api import APIData as NativeAPI
        from opentele2.api import UseCurrentSession
        from opentele2.td import TDesktop
        from telethon.sessions import MemorySession

        desktop = TDesktop(str(value), passcode=passcode, api=NativeAPI(**vars(api)))
        client = await desktop.ToTelethon(
            session=MemorySession(),
            flag=UseCurrentSession,
            receive_updates=False,
            connection_retries=1,
            request_retries=0,
            flood_sleep_threshold=0,
        )
        return client, "telethon"
    from pyrogram import Client

    path = Path(value) if kind not in STRING_KINDS else None
    client = Client(
        name=path.stem if path else "live-memory",
        workdir=str(path.parent) if path else ".",
        session_string=value if path is None else None,
        in_memory=path is None,
        api_id=api.api_id,
        api_hash=api.api_hash,
        device_model=api.device_model,
        system_version=api.system_version,
        app_version=api.app_version,
        no_updates=True,
        workers=1,
        sleep_threshold=0,
    )
    return client, "pyrogram"


async def close_native(client, family):
    if family == "pyrogram":
        if client.is_connected:
            await client.disconnect()
        else:
            # Storage may not have been opened if connect() failed immediately.
            with suppress(RuntimeError, AttributeError):
                await client.storage.close()
    else:
        try:
            await client.disconnect()
        finally:
            client.session.close()


async def native_identity(client, family, *, expected_key=None):
    """Require a server response, preserving the original authorization key."""
    try:
        await client.connect()
        key = (
            await client.storage.auth_key() if family == "pyrogram" else client.session.auth_key.key
        )
        if expected_key is not None and not hmac.compare_digest(key, expected_key):
            raise RuntimeError("Native client replaced the authorization key")
        user = await rate_limited_get_me(client)
        if user is None:
            raise RuntimeError("The supplied Telegram session is not authorized")
        return user
    finally:
        await asyncio.wait_for(close_native(client, family), timeout=10)


async def rate_limited_get_me(client):
    """Respect explicit Telegram FloodWait responses; never retry auth/RPC failures."""
    for attempt in range(3):
        try:
            return await client.get_me()
        except Exception as exc:
            seconds = getattr(exc, "value", getattr(exc, "seconds", None))
            if (
                type(exc).__name__ not in ("FloodWait", "FloodWaitError")
                or type(seconds) is not int
                or not 0 < seconds <= 60
                or attempt == 2
            ):
                raise
            await asyncio.sleep(seconds + 1)


async def manager_load(source, kind, api):
    if kind.startswith("tdata"):
        return await asyncio.to_thread(
            SessionManager.from_tdata_folder,
            source,
            api=api,
            passcode=SOURCE_PASSCODE if kind == "tdata_encrypted" else "",
        )
    if kind in STRING_KINDS:
        return getattr(SessionManager, f"from_{format_of(kind)}_string")(source, api)
    return await getattr(SessionManager, f"from_{format_of(kind)}_file")(source, api)


async def perform_conversion(
    interface, source, source_kind, target_kind, seed, directory, *, process_env=None
):
    """Exercise each public interface without putting real strings in argv."""
    destination = destination_for(target_kind, directory)
    if interface == "api":
        return await convert(
            source,
            format_of(source_kind),
            format_of(target_kind),
            destination,
            api=seed.api,
            user_id=seed.user_id,
            backend=format_backend(target_kind),
            passcode=SOURCE_PASSCODE if source_kind == "tdata_encrypted" else "",
            output_passcode=OUTPUT_PASSCODE if target_kind == "tdata_encrypted" else "",
        )
    if interface == "manager":
        loaded = await manager_load(source, source_kind, seed.api)
        if source_kind.startswith("telethon"):
            loaded.user_id = seed.user_id
        if destination is None:
            return getattr(loaded, f"to_{format_of(target_kind)}_string")()
        if target_kind.startswith("tdata"):
            await loaded.to_tdata_folder(
                destination,
                passcode=OUTPUT_PASSCODE if target_kind == "tdata_encrypted" else "",
            )
        elif target_kind.startswith("telethon"):
            await loaded.to_telethon_file(destination)
        else:
            await loaded.to_pyrogram_file(destination, backend=format_backend(target_kind))
        return destination
    stdin = source_kind in STRING_KINDS
    args, env, destination = cli_args(
        source, source_kind, target_kind, seed, directory, stdin=stdin
    )
    if interface == "cli":
        from typer.testing import CliRunner

        result = await asyncio.to_thread(
            CliRunner().invoke, app, args, env=env, input=str(source) + "\n" if stdin else None
        )
        if result.exit_code:
            raise RuntimeError(f"CLI failed with exit code {result.exit_code}")
    else:
        import os
        import subprocess
        import sysconfig

        executable = Path(sysconfig.get_path("scripts")) / (
            "tgconvertor.exe" if os.name == "nt" else "tgconvertor"
        )
        result = await asyncio.to_thread(
            subprocess.run,
            [str(executable), *args],
            input=str(source) + "\n" if stdin else None,
            cwd=directory,
            env=(os.environ if process_env is None else process_env) | env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode:
            raise RuntimeError(f"Installed CLI failed with exit code {result.returncode}")
    return destination if destination is not None else result.stdout.strip()
