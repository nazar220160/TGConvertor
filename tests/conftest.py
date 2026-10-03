import os
from pathlib import Path

import pytest

from TGConvertor import APIData, SessionManager

from ._network_guard import install_network_guard


@pytest.fixture
def auth_key():
    # Synthetic authorization, never associated with a Telegram account.
    return bytes(range(256))


@pytest.fixture
def api():
    return APIData(12345, "0123456789abcdef0123456789abcdef")


@pytest.fixture
def session(auth_key, api):
    return SessionManager(2, auth_key, user_id=2**40 + 17, api=api)


@pytest.fixture(autouse=True)
def no_network(monkeypatch, request):
    if request.node.get_closest_marker("live") and os.getenv("TGCONVERTOR_RUN_LIVE") == "1":
        return
    install_network_guard(monkeypatch.setattr)


@pytest.fixture
def offline_process_env(tmp_path):
    """Apply the network prohibition inside installed CLI subprocesses too."""
    guard = tmp_path / "offline-python"
    guard.mkdir()
    (guard / "sitecustomize.py").write_text(
        Path(__file__).with_name("_network_guard.py").read_text(encoding="utf-8")
        + "\ninstall_network_guard()\n",
        encoding="utf-8",
    )
    # Only the guard is on PYTHONPATH; package imports must resolve to the installed wheel.
    return os.environ | {"PYTHONPATH": str(guard)}
