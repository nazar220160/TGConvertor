"""Block network connections while allowing asyncio's Windows socketpair."""

import socket
import threading

_state = threading.local()


def install_network_guard(patch=setattr):
    original_pair = socket.socketpair

    def guard(original):
        def connect(sock, address):
            if sock.family in (socket.AF_INET, socket.AF_INET6) and not getattr(
                _state, "creating_socketpair", False
            ):
                raise AssertionError("Offline tests must not connect to the network")
            return original(sock, address)

        return connect

    def socketpair(*args, **kwargs):
        # Windows implements socketpair through a loopback TCP connection.
        # Only that synchronous stdlib operation is exempt, in its own thread.
        previous = getattr(_state, "creating_socketpair", False)
        _state.creating_socketpair = True
        try:
            return original_pair(*args, **kwargs)
        finally:
            _state.creating_socketpair = previous

    patch(socket.socket, "connect", guard(socket.socket.connect))
    patch(socket.socket, "connect_ex", guard(socket.socket.connect_ex))
    patch(socket, "socketpair", socketpair)
