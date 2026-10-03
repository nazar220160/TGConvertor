"""Every supported input representation to every output, through each public interface."""

import asyncio
import importlib.util
import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path

import pytest
from typer.testing import CliRunner

from TGConvertor import SessionManager, convert
from TGConvertor.__main__ import app
from TGConvertor.converter import load_session
from TGConvertor.sessions.pyro import PyroSession

# Kurigram and Pyrogram share the exact same string representation.
KINDS = (
    "telethon_file",
    "telethon_string",
    "pyrogram_file",
    "kurigram_file",
    "pyrogram_string",
    "tdata_plain",
    "tdata_encrypted",
)
STRING_KINDS = ("telethon_string", "pyrogram_string")
SOURCE_PASSCODE = "source-local-passcode"
OUTPUT_PASSCODE = "different-output-passcode"


def format_of(kind):
    if kind.startswith("telethon"):
        return "telethon"
    return "tdata" if kind.startswith("tdata") else "pyrogram"


def snapshot(path):
    # Include sidecars/new files as well as the original authorization.
    return {str(p.relative_to(path)): p.read_bytes() for p in path.rglob("*") if p.is_file()}


@pytest.fixture
async def matrix_source(source_kind, target_kind, session, tmp_path):
    if any(kind.startswith("tdata") for kind in (source_kind, target_kind)):
        pytest.importorskip("opentele2")
    session.takeout_id = 98765
    directory = tmp_path / "source with spaces"
    directory.mkdir()
    if source_kind in STRING_KINDS:
        source = getattr(session, f"to_{format_of(source_kind)}_string")()
    elif source_kind.startswith("tdata"):
        source = directory / "tdata"
        await session.to_tdata_folder(
            source, passcode=SOURCE_PASSCODE if source_kind == "tdata_encrypted" else ""
        )
    else:
        source = directory / "original.session"
        if source_kind == "telethon_file":
            await session.to_telethon_file(source)
        else:
            await session.to_pyrogram_file(source, backend=format_backend(source_kind))
    return source, directory, snapshot(directory)


def format_backend(kind):
    return "kurigram" if kind == "kurigram_file" else "pyrogram"


def destination_for(kind, tmp_path):
    if kind in STRING_KINDS:
        return None
    return (
        tmp_path
        / "output with spaces"
        / ("tdata" if kind.startswith("tdata") else "converted.session")
    )


async def assert_output(result, source_kind, target_kind, session):
    target_format = format_of(target_kind)
    passcode = OUTPUT_PASSCODE if target_kind == "tdata_encrypted" else ""
    restored = await load_session(
        result,
        target_format,
        api=session.api,
        input_type="string" if target_kind in STRING_KINDS else "file",
        passcode=passcode,
    )
    assert restored.auth_key == session.auth_key
    assert restored.dc_id == session.dc_id
    assert restored.test_mode is False
    if target_format == "telethon":
        assert restored.user_id is None
        assert restored.server_address == session.telethon.server_address
        assert restored.port == session.telethon.port
        assert restored.takeout_id == (
            session.takeout_id if source_kind == target_kind == "telethon_file" else None
        )
    else:
        assert restored.user_id == session.user_id
        assert restored.is_bot is False
    if target_format == "pyrogram":
        assert restored.api_id == session.api_id
    if target_kind in ("pyrogram_file", "kurigram_file"):
        with closing(sqlite3.connect(result)) as db:
            assert db.execute("SELECT number FROM version").fetchone()[0] == (
                7 if target_kind == "kurigram_file" else 3
            )
            cols = {row[1] for row in db.execute("PRAGMA table_info(sessions)")}
            assert ("server_address" in cols) == (target_kind == "kurigram_file")
    # Independently open every output with its native client when that extra is present.
    if target_format == "telethon" and importlib.util.find_spec("telethon"):
        from telethon.sessions import SQLiteSession, StringSession

        native = (
            StringSession(result) if target_kind in STRING_KINDS else SQLiteSession(str(result))
        )
        try:
            assert native.auth_key.key == session.auth_key
            assert native.dc_id == session.dc_id
            assert native.server_address == restored.server_address
            assert native.port == restored.port
        finally:
            native.close()
    elif target_format == "pyrogram":
        backend = PyroSession.installed_backend()
        if backend and (target_kind in STRING_KINDS or backend == format_backend(target_kind)):
            from pyrogram import Client

            native = Client(
                "converted",
                api_id=session.api_id,
                api_hash=session.api.api_hash,
                session_string=result if target_kind in STRING_KINDS else None,
                workdir=str(result.parent) if isinstance(result, Path) else ".",
            )
            await native.storage.open()
            try:
                assert await native.storage.auth_key() == session.auth_key
                assert await native.storage.user_id() == session.user_id
                assert await native.storage.dc_id() == session.dc_id
                assert await native.storage.api_id() == session.api_id
                assert await native.storage.test_mode() == 0  # SQLite exposes 0/1.
                assert await native.storage.is_bot() == 0  # SQLite exposes 0/1.
            finally:
                await native.storage.close()
    elif target_format == "tdata":
        from opentele2.td import TDesktop

        native = TDesktop(str(result), passcode=passcode)
        assert native.isLoaded()
        assert native.mainAccount.authKey.key == session.auth_key
        assert native.mainAccount.UserId == session.user_id
        assert native.mainAccount.MainDcId == session.dc_id
        assert not (result / "tdata").exists()


@pytest.mark.parametrize("source_kind", KINDS)
@pytest.mark.parametrize("target_kind", KINDS)
async def test_convert_api_every_direction(
    source_kind, target_kind, matrix_source, session, tmp_path
):
    source, directory, before = matrix_source
    destination = destination_for(target_kind, tmp_path)
    result = await convert(
        source,
        format_of(source_kind),
        format_of(target_kind),
        destination,
        api=session.api,
        user_id=session.user_id,
        backend=format_backend(target_kind),
        passcode=SOURCE_PASSCODE if source_kind == "tdata_encrypted" else "",
        output_passcode=OUTPUT_PASSCODE if target_kind == "tdata_encrypted" else "",
    )
    assert result == destination if destination is not None else isinstance(result, str)
    await assert_output(result, source_kind, target_kind, session)
    assert snapshot(directory) == before


@pytest.mark.parametrize("source_kind", KINDS)
@pytest.mark.parametrize("target_kind", KINDS)
async def test_manager_every_direction(source_kind, target_kind, matrix_source, session, tmp_path):
    source, directory, before = matrix_source
    source_format = format_of(source_kind)
    if source_format == "tdata":
        loaded = await asyncio.to_thread(
            SessionManager.from_tdata_folder,
            source,
            api=session.api,
            passcode=SOURCE_PASSCODE if source_kind == "tdata_encrypted" else "",
        )
    elif source_kind in STRING_KINDS:
        loaded = getattr(SessionManager, f"from_{source_format}_string")(source, session.api)
    else:
        loaded = await getattr(SessionManager, f"from_{source_format}_file")(source, session.api)
    if source_format == "telethon":
        loaded.user_id = session.user_id  # Required owner metadata, supplied explicitly.
    destination = destination_for(target_kind, tmp_path)
    target_format = format_of(target_kind)
    if destination is None:
        result = getattr(loaded, f"to_{target_format}_string")()
    else:
        if target_format == "tdata":
            await loaded.to_tdata_folder(
                destination, passcode=OUTPUT_PASSCODE if target_kind == "tdata_encrypted" else ""
            )
        elif target_format == "pyrogram":
            await loaded.to_pyrogram_file(destination, backend=format_backend(target_kind))
        else:
            await loaded.to_telethon_file(destination)
        result = destination
    await assert_output(result, source_kind, target_kind, session)
    assert snapshot(directory) == before


def cli_args(source, source_kind, target_kind, session, tmp_path, *, stdin=False):
    destination = destination_for(target_kind, tmp_path)
    args = [
        "convert",
        "-" if stdin else str(source),
        "-f",
        format_of(source_kind),
        "-t",
        format_of(target_kind),
        "--user-id",
        str(session.user_id),
        "--backend",
        format_backend(target_kind),
    ]
    if destination is not None:
        args += ["-o", str(destination)]
    env = {
        "TGCONVERTOR_API_ID": str(session.api.api_id),
        "TGCONVERTOR_API_HASH": session.api.api_hash,
        "TGCONVERTOR_TDATA_PASSCODE": SOURCE_PASSCODE if source_kind == "tdata_encrypted" else "",
        "TGCONVERTOR_OUTPUT_PASSCODE": OUTPUT_PASSCODE if target_kind == "tdata_encrypted" else "",
    }
    return args, env, destination


@pytest.mark.parametrize("source_kind", KINDS)
@pytest.mark.parametrize("target_kind", KINDS)
async def test_cli_every_direction(source_kind, target_kind, matrix_source, session, tmp_path):
    source, directory, before = matrix_source
    args, env, destination = cli_args(source, source_kind, target_kind, session, tmp_path)
    result = await asyncio.to_thread(CliRunner().invoke, app, args, env=env)
    assert result.exit_code == 0, result.output
    if destination is None:
        assert result.stderr == ""
        output = result.stdout.strip()
    else:
        assert result.stdout == ""
        assert "Saved to:" in result.stderr
        output = destination
    await assert_output(output, source_kind, target_kind, session)
    assert snapshot(directory) == before


@pytest.mark.parametrize("source_kind", KINDS)
@pytest.mark.parametrize("target_kind", KINDS)
async def test_real_cli_process_every_direction(
    source_kind, target_kind, matrix_source, session, tmp_path, offline_process_env
):
    source, directory, before = matrix_source
    stdin = source_kind in STRING_KINDS
    args, env, destination = cli_args(
        source, source_kind, target_kind, session, tmp_path, stdin=stdin
    )
    # Run the actual installed entry point outside the checkout, with piped strings.
    executable = Path(sys.executable).parent / (
        "tgconvertor.exe" if os.name == "nt" else "tgconvertor"
    )
    assert executable.is_file(), "The distribution's console entry point must be installed"
    result = await asyncio.to_thread(
        subprocess.run,
        [str(executable), *args],
        input=str(source) + "\n" if stdin else None,
        cwd=tmp_path,
        env=offline_process_env | env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    output = destination if destination is not None else result.stdout.strip()
    if destination is None:
        assert result.stderr == ""
    else:
        assert result.stdout == ""
        assert "Saved to:" in result.stderr
    await assert_output(output, source_kind, target_kind, session)
    assert snapshot(directory) == before


def test_subprocess_network_guard(offline_process_env, tmp_path):
    result = subprocess.run(
        [sys.executable, "-c", "import socket; socket.socket().connect(('127.0.0.1', 9))"],
        cwd=tmp_path,
        env=offline_process_env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert "AssertionError: Offline tests must not connect to the network" in result.stderr


@pytest.mark.parametrize("source_kind", [kind for kind in KINDS if kind not in STRING_KINDS])
@pytest.mark.parametrize("target_kind", ["telethon_string"])
async def test_info_every_file_representation(source_kind, target_kind, matrix_source, session):
    source, directory, before = matrix_source
    result = await asyncio.to_thread(
        CliRunner().invoke,
        app,
        ["info", str(source), "-f", format_of(source_kind)],
        env={
            "TGCONVERTOR_TDATA_PASSCODE": SOURCE_PASSCODE
            if source_kind == "tdata_encrypted"
            else ""
        },
    )
    assert result.exit_code == 0, result.output
    assert "Not checked" in result.output
    assert session.auth_key.hex() not in result.output
    assert session.to_telethon_string() not in result.output
    assert session.to_pyrogram_string() not in result.output
    if source_kind != "telethon_file":
        assert str(session.user_id) in result.output
    assert snapshot(directory) == before
