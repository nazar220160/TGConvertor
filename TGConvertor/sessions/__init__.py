from importlib.metadata import distribution, PackageNotFoundError

try:
    distribution("kurigram")
    is_kurigram = True
except PackageNotFoundError:
    is_kurigram = False

try:
    distribution("pyrogram")
    is_pyrogram = True
except PackageNotFoundError:
    is_pyrogram = False

if is_kurigram and is_pyrogram:
    raise ImportError(
        "Both 'kurigram' and 'pyrogram' packages are installed. "
        "Please uninstall one of them to avoid conflicts."
    )