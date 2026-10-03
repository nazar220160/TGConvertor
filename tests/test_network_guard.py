import asyncio
import inspect
import socket
import subprocess
import sys
from contextlib import closing

import pytest


@pytest.mark.parametrize("operation", ["connect", "connect_ex"])
@pytest.mark.parametrize("host", ["127.0.0.1", "149.154.167.50"])
def test_guard_blocks_connections_even_to_loopback(operation, host):
    with closing(socket.socket()) as sock, pytest.raises(AssertionError, match="Offline tests"):
        getattr(sock, operation)((host, 443))


def tcp_socketpair():
    """Reproduce Windows' local TCP wakeup pipe on every supported Python."""
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        client = socket.socket()
        try:
            client.connect(listener.getsockname())
            server, _ = listener.accept()
        except BaseException:
            client.close()
            raise
    return server, client


def test_guard_allows_tcp_socketpair():

    from ._network_guard import install_network_guard

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(socket, "socketpair", tcp_socketpair)
        install_network_guard(patch.setattr)
        first, second = socket.socketpair()
        with closing(first), closing(second):
            first.sendall(b"asyncio wakeup")
            assert second.recv(32) == b"asyncio wakeup"
        with (
            closing(socket.socket()) as sock,
            pytest.raises(AssertionError, match="Offline tests"),
        ):
            sock.connect(("127.0.0.1", 443))


def test_guard_in_asyncio_subprocess(offline_process_env, tmp_path):
    code = (
        "import asyncio\nimport socket\n"
        + inspect.getsource(tcp_socketpair)
        + """
# Simulate Windows before installing a fresh guard around the TCP fallback.
socket.socketpair = tcp_socketpair
from sitecustomize import install_network_guard
install_network_guard()
asyncio.run(asyncio.sleep(0))
for operation in ('connect', 'connect_ex'):
    with socket.socket() as sock:
        try:
            getattr(sock, operation)(('127.0.0.1', 443))
        except AssertionError:
            pass
        else:
            raise AssertionError('Network guard did not block the connection')
"""
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        env=offline_process_env,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr


async def test_guard_allows_asyncio():
    await asyncio.sleep(0)
