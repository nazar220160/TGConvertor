import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from TGConvertor import (
    MissingDependencyError,
    SessionManager,
    TDataSession,
    ValidationError,
    convert,
)
from TGConvertor.sessions import tdata


@pytest.mark.parametrize("passcode", ["", "local-test-passcode"])
@pytest.mark.integration
async def test_native_tdata_round_trip(session, tmp_path, passcode):
    pytest.importorskip("opentele2")
    from opentele2.td import TDesktop

    output = tmp_path / "desktop" / "tdata"
    await session.to_tdata_folder(output, passcode=passcode)
    assert (output / "key_datas").is_file()
    assert not (output / "tdata").exists()
    native = TDesktop(str(output), passcode=passcode)
    assert native.isLoaded()
    assert native.mainAccount.authKey.key == session.auth_key
    assert native.mainAccount.UserId == session.user_id
    assert native.mainAccount.MainDcId == session.dc_id
    result = SessionManager.from_tdata_folder(output, passcode=passcode, account_index=0)
    assert result.user_id == session.user_id
    assert result.auth_key == session.auth_key
    assert result.dc_id == session.dc_id
    string = await convert(output, "tdata", "pyrogram", passcode=passcode)
    assert SessionManager.from_pyrogram_string(string).user_id == session.user_id
    copy = tmp_path / "copy"
    await convert(session.to_pyrogram_string(), "pyrogram", "tdata", copy)
    assert SessionManager.from_tdata_folder(copy).auth_key == session.auth_key
    assert (copy / "key_datas").read_bytes() != (output / "key_datas").read_bytes()
    if os.name != "nt":
        assert output.stat().st_mode & 0o777 == 0o700
        assert all(
            item.stat().st_mode & 0o777 == (0o700 if item.is_dir() else 0o600)
            for item in output.rglob("*")
        )
    with pytest.raises(ValidationError, match="account_index"):
        SessionManager.from_tdata_folder(output, passcode=passcode, account_index=99)
    with pytest.raises(ValidationError, match="Cannot read"):
        SessionManager.from_tdata_folder(output, passcode="wrong")
    with pytest.raises(FileExistsError):
        await session.to_tdata_folder(output)


def test_missing_tdata_dependency(session, tmp_path, monkeypatch):
    import sys

    monkeypatch.setitem(sys.modules, "opentele2.api", None)
    with pytest.raises(MissingDependencyError, match="tdata"):
        session.tdata.to_folder(tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_missing_tdata_path(tmp_path):
    with pytest.raises(FileNotFoundError):
        TDataSession.from_tdata(tmp_path / "missing")


def test_tdata_requires_identity(auth_key):
    with pytest.raises(ValidationError, match="user_id"):
        TDataSession(dc_id=2, auth_key=auth_key, user_id=None)


@pytest.fixture
def fake_opentele(monkeypatch, session):
    state = {"save_success": True, "has_accounts": True, "fail_move": False}
    account = SimpleNamespace(
        MainDcId=2, UserId=session.user_id, authKey=SimpleNamespace(key=session.auth_key)
    )

    class FakeOpenTeleError(BaseException):
        pass

    class Desktop:
        def __init__(self, *args, **kwargs):
            self.accounts = [account] if state["has_accounts"] else []
            self.mainAccount = account

        def isLoaded(self):
            return state["has_accounts"]

        def _addSingleAccount(self, value):
            pass

        def SaveTData(self, path, **kwargs):
            Path(path, "key_datas").write_bytes(b"synthetic tdata")
            return state["save_success"]

    class Account:
        def __init__(self, **kwargs):
            pass

        def _setMtpAuthorizationCustom(self, *args):
            pass

    monkeypatch.setattr(
        tdata,
        "_opentele",
        lambda: (
            Desktop,
            Account,
            lambda *args: None,
            SimpleNamespace(ReadFromFile=1),
            int,
            lambda **kwargs: kwargs,
            FakeOpenTeleError,
        ),
    )
    return state


def test_tdata_empty_accounts(tmp_path, fake_opentele):
    fake_opentele["has_accounts"] = False
    with pytest.raises(ValidationError, match="No authorized"):
        TDataSession.from_tdata(tmp_path)


def test_tdata_adapter_fake_success(session, tmp_path, fake_opentele):
    output = tmp_path / "tdata"
    session.tdata.to_folder(output)
    result = SessionManager.from_tdata_folder(output)
    assert result.user_id == session.user_id
    assert (output / "key_datas").read_bytes() == b"synthetic tdata"


def test_tdata_save_failure_cleans_up(session, tmp_path, fake_opentele):
    fake_opentele["save_success"] = False
    with pytest.raises(ValidationError, match="could not write"):
        session.tdata.to_folder(tmp_path / "out")
    assert list(tmp_path.iterdir()) == []


def test_tdata_move_failure_cleans_up(session, tmp_path, fake_opentele, monkeypatch):
    def fail(*args):
        raise OSError("cannot move")

    monkeypatch.setattr(tdata.os, "rename", fail)
    with pytest.raises(OSError, match="cannot move"):
        session.tdata.to_folder(tmp_path / "out")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("passcode", ["пароль", None])
def test_unsupported_passcodes_fail_clearly(session, tmp_path, passcode):
    with pytest.raises(ValidationError, match="ASCII"):
        session.tdata.to_folder(tmp_path / "out", passcode=passcode)
    with pytest.raises(ValidationError, match="ASCII"):
        TDataSession.from_tdata(tmp_path, passcode=passcode)
    assert list(tmp_path.iterdir()) == []
