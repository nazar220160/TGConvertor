"""Reject tags that do not exactly identify this distribution's version."""

import sys
from pathlib import Path

import tomllib


def main() -> None:
    version = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"][
        "version"
    ]
    if len(sys.argv) != 2 or sys.argv[1] != f"v{version}":
        raise SystemExit(f"Release tag must be v{version}")
    print(f"Release version verified: {version}")


if __name__ == "__main__":
    main()
