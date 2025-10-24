from .. import is_kurigram

if is_kurigram:
    from .kuri import PyroSession  # noqa: F401
else:
    from .pyro import PyroSession  # noqa: F401

__all__ = ["PyroSession"]
