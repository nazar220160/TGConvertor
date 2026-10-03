import pytest
from typer.testing import CliRunner

from TGConvertor import SessionManager, ValidationError, __version__, convert
from TGConvertor.__main__ import app
from TGConvertor.converter import load_session

runner = CliRunner()


async def test_convenience_conversion(session, tmp_path):
    source = tmp_path / "source.session"
    output = tmp_path / "nested" / "output.session"
    await session.to_telethon_file(source)
    result = await convert(source, "telethon", "pyrogram", output, user_id=session.user_id)
    assert result == output
    restored = await load_session(output, "pyrogram")
    assert restored.user_id == session.user_id
    assert restored.auth_key == session.auth_key
    string = await convert(session.to_pyrogram_string(), "pyrogram", "telethon")
    assert SessionManager.from_telethon_string(string).auth_key == session.auth_key
    assert await convert(string, "telethon", "telethon") == string


@pytest.mark.parametrize(
    "kwargs",
    [
        {"from_format": "bad", "to_format": "telethon"},
        {"from_format": "telethon", "to_format": "bad"},
        {"from_format": "telethon", "to_format": "telethon", "input_type": "bad"},
        {"from_format": "tdata", "to_format": "telethon", "input_type": "string"},
        {"from_format": "telethon", "to_format": "tdata"},
    ],
)
async def test_bad_conversion_options(kwargs):
    with pytest.raises(ValidationError):
        await convert("source", **kwargs)


async def test_existing_output_rejected_before_reading_source(tmp_path):
    path = tmp_path / "out.session"
    path.write_bytes(b"keep")
    with pytest.raises(FileExistsError):
        await convert("missing", "telethon", "telethon", path)
    assert path.read_bytes() == b"keep"


async def test_wrong_owner_rejected(session):
    with pytest.raises(ValidationError, match="differs"):
        await convert(session.to_pyrogram_string(), "pyrogram", "telethon", user_id=123)


async def test_explicit_file_type_and_extensionless_source(session, tmp_path):
    path = tmp_path / "extensionless"
    await session.to_telethon_file(path)
    restored = await load_session(str(path), "telethon", input_type="file")
    assert restored.auth_key == session.auth_key
    assert (await load_session(str(path), "telethon")).auth_key == session.auth_key


def test_cli_help_version_and_formats():
    for command in [["--help"], ["convert", "--help"], ["info", "--help"], ["list-formats"]]:
        result = runner.invoke(app, command)
        assert result.exit_code == 0, result.output
    assert runner.invoke(app, ["--version"]).stdout.strip() == __version__


def test_cli_string_stdout_and_stdin(session):
    result = runner.invoke(
        app,
        ["convert", "-", "-f", "pyrogram", "-t", "telethon"],
        input=session.to_pyrogram_string() + "\n",
    )
    assert result.exit_code == 0, result.output
    assert result.stdout.strip() == session.to_telethon_string()
    assert result.stderr == ""
    explicit = runner.invoke(
        app,
        [
            "convert",
            session.to_pyrogram_string(),
            "-f",
            "pyrogram",
            "-t",
            "telethon",
            "-o",
            "string",
        ],
    )
    assert explicit.stdout == result.stdout


def test_cli_invalid_string_does_not_expose_input():
    secret = "sensitive_credential_not_a_session"
    result = runner.invoke(
        app, ["convert", secret, "--input-type", "string", "-f", "telethon", "-t", "pyrogram"]
    )
    assert result.exit_code == 1
    assert secret not in result.output
    assert "Traceback" not in result.output
    assert "Error:" in result.stderr
    assert not result.stdout


def test_cli_file_output_info_and_existing_path(session, tmp_path):
    source, output = tmp_path / "source.session", tmp_path / "target.session"
    import asyncio

    asyncio.run(session.to_telethon_file(source))
    result = runner.invoke(
        app,
        [
            "convert",
            str(source),
            "-f",
            "telethon",
            "-t",
            "pyrogram",
            "--user-id",
            str(session.user_id),
            "-o",
            str(output),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Saved to:" in result.stderr
    assert not result.stdout
    info = runner.invoke(app, ["info", str(output), "-f", "pyrogram"])
    assert info.exit_code == 0, info.output
    assert str(session.user_id) in info.output
    assert "Not checked" in info.output
    assert session.auth_key.hex() not in info.output
    before = output.read_bytes()
    duplicate = runner.invoke(
        app, ["convert", str(source), "-f", "telethon", "-t", "pyrogram", "-o", str(output)]
    )
    assert duplicate.exit_code == 1
    assert output.read_bytes() == before
    same = runner.invoke(
        app, ["convert", str(source), "-f", "telethon", "-t", "pyrogram", "-o", str(source)]
    )
    assert same.exit_code == 1


@pytest.mark.parametrize(
    "args",
    [
        ["convert", "missing.session", "-f", "telethon", "-t", "pyrogram"],
        ["info", "missing.session", "-f", "telethon"],
        ["convert", "source", "-f", "telethon", "-t", "pyrogram", "--backend", "bad"],
    ],
)
def test_cli_errors_are_concise(args):
    result = runner.invoke(app, args)
    assert result.exit_code == 1
    assert "Error:" in result.output
    assert "Traceback" not in result.output


@pytest.mark.parametrize("api_id,api_hash", [("123", None), (None, "hash"), ("bad", "hash")])
def test_cli_bad_credentials_env(monkeypatch, api_id, api_hash):
    for name, value in [("TGCONVERTOR_API_ID", api_id), ("TGCONVERTOR_API_HASH", api_hash)]:
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)
    result = runner.invoke(app, ["convert", "source", "-f", "telethon", "-t", "telethon"])
    assert result.exit_code == 1
    assert "TGCONVERTOR_API" in result.stderr


def test_cli_custom_api(monkeypatch, session):
    monkeypatch.setenv("TGCONVERTOR_API_ID", "54321")
    monkeypatch.setenv("TGCONVERTOR_API_HASH", "hash")
    source = session.to_telethon_string()
    result = runner.invoke(
        app,
        ["convert", source, "-f", "telethon", "-t", "pyrogram", "--user-id", str(session.user_id)],
    )
    assert result.exit_code == 0, result.output
    assert SessionManager.from_pyrogram_string(result.stdout.strip()).api_id == 54321


@pytest.mark.parametrize(
    "options",
    [
        ["-f", "invalid", "-t", "telethon"],
        ["-f", "telethon"],
        ["-f", "telethon", "-t", "pyrogram", "--user-id", "0"],
        ["-f", "telethon", "-t", "pyrogram", "--user-id", "abc"],
        ["-f", "telethon", "-t", "telethon", "--account-index", "-1"],
        ["-f", "telethon", "-t", "telethon", "--input-type", "invalid"],
        ["-f", "telethon", "-t", "telethon", "--api", "invalid"],
        ["-f", "telethon", "-t", "telethon", "--unknown-option"],
    ],
)
def test_cli_parser_errors(options):
    result = runner.invoke(app, ["convert", "source.session", *options])
    assert result.exit_code == 2
    assert "Traceback" not in result.output
    assert result.stdout == ""


def test_cli_rejects_oversized_stdin_without_echoing_it():
    secret = "A" * 2000
    result = runner.invoke(app, ["convert", "-", "-f", "telethon", "-t", "telethon"], input=secret)
    assert result.exit_code == 1
    assert result.stdout == ""
    assert "A" * 100 not in result.output
    assert "Traceback" not in result.output
