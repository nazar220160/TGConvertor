"""Browser-only adaptations around the published TGConvertor conversion API."""

import asyncio
import hashlib
import io
import json
import logging
import os
import shutil
import socket
import sys
import tempfile
import types
import zipfile
from pathlib import Path, PurePosixPath

from Crypto.Cipher import AES
from Crypto.Hash import SHA1, SHA256, SHA512
from Crypto.Protocol.KDF import PBKDF2

logging.disable(logging.CRITICAL)


def ige(data, key, iv, decrypt=False):
    """AES-256-IGE using WASM AES primitives (native tgcrypto cannot run in WASM)."""
    data, key, iv = bytes(data), bytes(key), bytes(iv)
    if len(key) != 32 or len(iv) != 32 or len(data) % 16:
        raise ValueError("Invalid AES-IGE parameters")
    aes = AES.new(key, AES.MODE_ECB)
    ciphertext, plaintext = iv[:16], iv[16:]
    result = bytearray()
    for offset in range(0, len(data), 16):
        block = data[offset : offset + 16]
        first, second = (plaintext, ciphertext) if decrypt else (ciphertext, plaintext)
        transformed = (aes.decrypt if decrypt else aes.encrypt)(
            bytes(a ^ b for a, b in zip(block, first, strict=True))
        )
        output = bytes(a ^ b for a, b in zip(transformed, second, strict=True))
        ciphertext, plaintext = (block, output) if decrypt else (output, block)
        result.extend(output)
    return bytes(result)


tgcrypto = types.ModuleType("tgcrypto")
tgcrypto.ige256_encrypt = lambda data, key, iv: ige(data, key, iv)
tgcrypto.ige256_decrypt = lambda data, key, iv: ige(data, key, iv, True)
sys.modules["tgcrypto"] = tgcrypto


def pbkdf2_hmac(hash_name, password, salt, iterations, dklen=None):
    algorithm = {"sha1": SHA1, "sha256": SHA256, "sha512": SHA512}[hash_name]
    if iterations < 1 or (dklen is not None and dklen < 1):
        raise ValueError("Invalid PBKDF2 parameters")
    return PBKDF2(
        password,
        salt,
        dkLen=dklen or algorithm.digest_size,
        count=iterations,
        hmac_hash_module=algorithm,
    )


# Pyodide's hashlib omits the OpenSSL-dependent PBKDF2 implementation.
if not hasattr(hashlib, "pbkdf2_hmac"):
    hashlib.pbkdf2_hmac = pbkdf2_hmac


def exclusive_copy_link(source, destination):
    # MEMFS has no hard links. Preserve exclusive destination creation instead.
    data = Path(source).read_bytes()
    with open(destination, "xb") as output:
        output.write(data)


if not hasattr(os, "link"):
    os.link = exclusive_copy_link


async def worker_thread(function, *args, **kwargs):
    # The entire interpreter already runs in a dedicated Web Worker.
    # Emscripten's Python cannot create a second native Python thread.
    return function(*args, **kwargs)


asyncio.to_thread = worker_thread


def no_network(*args, **kwargs):
    raise OSError("This browser converter works offline")


socket.socket.connect = no_network
socket.socket.connect_ex = no_network

from TGConvertor import API, APIData, SessionManager, ValidationError, convert  # noqa: E402
from TGConvertor.converter import load_session  # noqa: E402

MAX_FILES = 256
MAX_BYTES = 64 * 1024 * 1024
MAX_UPLOAD = 32 * 1024 * 1024


def safe_path(value):
    path = PurePosixPath(value)
    if not value or "\\" in value or path.is_absolute() or ".." in path.parts or ":" in value:
        raise ValidationError("Archive contains an unsafe file path")
    return path


def extract_tdata(data, root):
    count, total = 0, 0
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if len(archive.infolist()) > MAX_FILES:
            raise ValidationError("tdata archive exceeds the 256 file / 64 MB unpacked limit")
        for entry in archive.infolist():
            path = safe_path(entry.filename)
            if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValidationError("ZIP archives containing symbolic links are not supported")
            if entry.is_dir():
                continue
            if entry.flag_bits & 1:
                raise ValidationError("Use a normal ZIP; enter the local tdata passcode separately")
            count += 1
            total += entry.file_size
            if count > MAX_FILES or total > MAX_BYTES:
                raise ValidationError("tdata archive exceeds the 256 file / 64 MB unpacked limit")
            destination = root.joinpath(*path.parts)
            if destination.exists():
                raise ValidationError("Archive contains duplicate file names")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(archive.read(entry))
    candidates = {file.parent for file in root.rglob("key_data*") if file.is_file()}
    if len(candidates) != 1:
        raise ValidationError("ZIP must contain one tdata folder with its key_data files")
    return candidates.pop()


def metadata(session):
    return {
        "dc": session.dc_id,
        "userId": str(session.user_id) if session.user_id else None,
        "apiId": session.api_id,
        "bot": session.is_bot,
        "testMode": session.test_mode,
    }


def configured_api(options):
    api_id, api_hash = options.get("apiId", ""), options.get("apiHash", "")
    if bool(api_id) != bool(api_hash):
        raise ValidationError("Provide both API ID and API hash, or leave both empty")
    return APIData(int(api_id), api_hash) if api_id else API.TelegramDesktop


async def operate(payload_json, file_bytes=None):
    """One temporary in-memory workspace per operation, always cleaned up."""
    payload = json.loads(payload_json)
    root = Path(tempfile.mkdtemp(prefix="tgconvertor-browser-"))
    try:
        source_format = payload["sourceFormat"]
        options = payload.get("options", {})
        api = configured_api(options)
        mode = payload.get("inputMode", "file")
        if mode == "demo":
            session = SessionManager(2, bytes(range(256)), user_id=123456789, api=api)
            # A deliberately synthetic key, never associated with any real account.
            if source_format == "tdata":
                source = root / "demo-tdata"
                await session.to_tdata_folder(source, passcode=options.get("passcode", ""))
            else:
                source = getattr(session, f"to_{source_format}_string")()
            input_type = "file" if source_format == "tdata" else "string"
            options = options | {"userId": "123456789"}
        elif mode == "string":
            source = payload.get("sessionString", "").strip()
            if not source or len(source) > 512:
                raise ValidationError("Provide a valid session string, up to 512 characters")
            input_type = "string"
        else:
            data = bytes(file_bytes)
            if not data or len(data) > MAX_UPLOAD:
                raise ValidationError("Choose a nonempty file smaller than 32 MB")
            source = (
                extract_tdata(data, root / "input")
                if source_format == "tdata"
                else root / "input.session"
            )
            if source_format != "tdata":
                source.write_bytes(data)
            input_type = "file"
        index = int(options["accountIndex"]) if options.get("accountIndex", "") != "" else None
        session = await load_session(
            source,
            source_format,
            input_type=input_type,
            api=api,
            passcode=options.get("passcode", ""),
            account_index=index,
        )
        info = metadata(session)
        if payload.get("action") == "inspect":
            return {"metadata": info}
        target = payload["targetFormat"]
        output_kind = payload["outputMode"]
        destination = (
            None
            if output_kind == "string"
            else root / ("output-tdata" if target == "tdata" else "output.session")
        )
        result = await convert(
            source,
            source_format,
            target,
            destination,
            input_type=input_type,
            api=api,
            user_id=int(options["userId"]) if options.get("userId") else None,
            backend=payload.get("backend", "pyrogram"),
            passcode=options.get("passcode", ""),
            output_passcode=options.get("outputPasscode", ""),
            account_index=index,
        )
        info = metadata(
            await load_session(
                result,
                target,
                input_type="string" if isinstance(result, str) else "file",
                api=api,
                passcode=options.get("outputPasscode", ""),
            )
        )
        if isinstance(result, str):
            return {"metadata": info, "sessionString": result, "filename": f"{target}-session.txt"}
        if target == "tdata":
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
                for file in sorted(result.rglob("*")):
                    if file.is_file():
                        archive.write(file, "tdata/" + file.relative_to(result).as_posix())
            return {"metadata": info, "bytes": buffer.getvalue(), "filename": "tdata.zip"}
        backend = payload.get("backend", "pyrogram") if target == "pyrogram" else target
        return {
            "metadata": info,
            "bytes": result.read_bytes(),
            "filename": f"{backend}.txt" if target == "gramjs" else f"{backend}.session",
        }
    except (ValueError, OSError, ImportError, zipfile.BadZipFile) as exc:
        # Error messages are deliberate library diagnostics, never submitted content.
        return {"error": str(exc)}
    except BaseException:
        return {"error": "Conversion failed. Check the source format, file and local passcode."}
    finally:
        shutil.rmtree(root, ignore_errors=True)
