"""Invoke the native npm SDK over stdin, keeping real credentials out of argv/logs."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def gramjs(request):
    if not shutil.which("node") or not (ROOT / "web/node_modules/telegram").is_dir():
        if os.getenv("TGCONVERTOR_GRAMJS_REQUIRED") == "1":
            pytest.fail("Install the pinned native SDK with npm ci --prefix web", pytrace=False)
        pytest.skip("Native GramJS interoperability requires npm ci --prefix web and Node.js")
    result = subprocess.run(
        ["node", str(ROOT / "web/tests/gramjs_bridge.mjs")],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        timeout=170 if request.get("action") == "live" else 20,
    )
    if result.returncode:
        raise RuntimeError("Native GramJS verification failed")
    return json.loads(result.stdout)
