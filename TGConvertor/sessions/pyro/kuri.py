"""Backward-compatible Kurigram codec import."""

from .pyro import PyroSession as _PyroSession


class PyroSession(_PyroSession):
    async def to_file(self, path, *, backend="kurigram"):
        await super().to_file(path, backend=backend)
