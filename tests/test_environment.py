"""CI extras must be present, so missing dependencies cannot silently skip coverage."""

import os
from importlib.metadata import PackageNotFoundError, version

import pytest


def test_selected_ci_extra_is_installed():
    extra = os.getenv("TGCONVERTOR_TEST_EXTRA")
    if extra is None:
        return
    expected = {
        "core": (),
        "telethon": ("telethon",),
        "pyrogram": ("pyrogram",),
        "kurigram": ("kurigram",),
        "tdata": ("opentele2", "telethon"),
        "all": ("telethon", "kurigram", "opentele2"),
    }[extra]
    for package in expected:
        assert version(package)
    if extra == "core":
        for package in ("telethon", "pyrogram", "kurigram", "opentele2"):
            with pytest.raises(PackageNotFoundError):
                version(package)
