"""Test pre-release wheels locally; deploy only a verified published PyPI release."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import tomllib
from prepare_runtime import get

root = Path(__file__).resolve().parents[2]
requested = os.getenv("LIBRARY_VERSION", "")
version = tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]
if requested:
    published = True
elif os.getenv("GITHUB_EVENT_NAME") == "pull_request":
    published = False
else:
    published = (
        json.loads(get("https://pypi.org/pypi/tgconvertor/json"))["info"]["version"] == version
    )
prepare = [sys.executable, str(root / "web/scripts/prepare_runtime.py")]
if published:
    subprocess.run([*prepare, "--tgconvertor-version", requested or "latest"], check=True)
else:
    with tempfile.TemporaryDirectory(prefix="tgconvertor-wheel-") as temporary:
        subprocess.run(
            [sys.executable, "-m", "build", "--wheel", "--outdir", temporary, str(root)], check=True
        )
        wheel = next(Path(temporary).glob("*.whl"))
        subprocess.run([*prepare, "--development-wheel", str(wheel)], check=True)
    print("Pre-release library verified locally; Pages deployment waits for PyPI publication.")
if output := os.getenv("GITHUB_OUTPUT"):
    with Path(output).open("a") as stream:
        stream.write(f"published={'true' if published else 'false'}\n")
