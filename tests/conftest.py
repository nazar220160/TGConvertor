import os
import socket
import textwrap

import pytest

from TGConvertor import APIData, SessionManager


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
    original = socket.socket.connect

    def connect(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            raise AssertionError("Offline tests must not connect to the network")
        return original(sock, address)

    monkeypatch.setattr(socket.socket, "connect", connect)


@pytest.fixture
def offline_process_env(tmp_path):
    """Apply the network prohibition inside installed CLI subprocesses too."""
    guard = tmp_path / "offline-python"
    guard.mkdir()
    (guard / "sitecustomize.py").write_text(
        textwrap.dedent(
            """\
            import socket
            original_connect = socket.socket.connect
            original_connect_ex = socket.socket.connect_ex
            def guard_connect(original):
                def connect(sock, address):
                    if sock.family in (socket.AF_INET, socket.AF_INET6):
                        raise AssertionError("Offline tests must not connect to the network")
                    return original(sock, address)
                return connect
            socket.socket.connect = guard_connect(original_connect)
            socket.socket.connect_ex = guard_connect(original_connect_ex)
            """
        ),
        encoding="utf-8",
    )
    # Only the guard is on PYTHONPATH; package imports must resolve to the installed wheel.
    return os.environ | {"PYTHONPATH": str(guard)}
