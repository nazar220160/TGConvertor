from .. import is_kurigram, is_pyrogram

if is_kurigram:
    from .kuri import PyroSession  # noqa: F401
elif is_pyrogram:
    from .pyro import PyroSession  # noqa: F401
else:
    raise ImportError("Must install either kurigram or pyrogram to use PyroSession.")
    
__all__ = ["PyroSession"]
