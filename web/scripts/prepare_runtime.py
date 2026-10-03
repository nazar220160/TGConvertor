"""Bundle a pinned, self-hosted Python runtime; verify every downloaded package."""

import argparse
import hashlib
import io
import json
import shutil
import tarfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "public/runtime"
LOCK = ROOT / "runtime-lock.json"
EXPECTED_PACKAGES = {"tgconvertor", "opentele2", "telethon", "pyaes", "rsa", "pyasn1"}


def get(url):
    with urllib.request.urlopen(url, timeout=90) as response:
        return response.read()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tgconvertor-version",
        default="latest",
        help="latest (default), an explicit PyPI release/tag, or pinned for reproduction",
    )
    parser.add_argument(
        "--development-wheel",
        type=Path,
        help="Local wheel for pre-release tests; never updates the PyPI pin",
    )
    args = parser.parse_args()
    DEST.mkdir(parents=True, exist_ok=True)
    packages = json.loads(LOCK.read_text())["packages"]
    if (
        len(packages) != len(EXPECTED_PACKAGES)
        or {p["name"] for p in packages} != EXPECTED_PACKAGES
    ):
        raise ValueError("runtime-lock.json must contain exactly the expected browser packages")
    if args.development_wheel:
        wheel = args.development_wheel.resolve()
        data = wheel.read_bytes()
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            from email.parser import BytesParser

            metadata = BytesParser().parsebytes(
                archive.read(
                    next(
                        name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
                    )
                )
            )
        if metadata["Name"].lower() != "tgconvertor" or not wheel.name.endswith("-none-any.whl"):
            raise ValueError("Development wheel must be a pure Python TGConvertor distribution")
        packages = [
            {
                "name": "tgconvertor",
                "version": metadata["Version"],
                "filename": wheel.name,
                "url": wheel.as_uri(),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
            if p["name"] == "tgconvertor"
            else p
            for p in packages
        ]
    elif args.tgconvertor_version != "pinned":
        version_path = (
            ""
            if args.tgconvertor_version == "latest"
            else (quote(args.tgconvertor_version.removeprefix("v"), safe="") + "/")
        )
        for attempt in range(6):
            try:
                metadata = json.loads(get(f"https://pypi.org/pypi/tgconvertor/{version_path}json"))
                break
            except urllib.error.HTTPError as exc:
                if exc.code != 404 or attempt == 5:
                    raise
                print("Waiting for the published PyPI release to become available…", flush=True)
                time.sleep(5 * (attempt + 1))
        entry = next(
            (
                item
                for item in metadata["urls"]
                if item["filename"].endswith("-none-any.whl") and not item.get("yanked")
            ),
            None,
        )
        if entry is None:
            raise ValueError("This PyPI release has no pure Python wheel for the browser")
        packages = [
            {
                "name": "tgconvertor",
                "version": metadata["info"]["version"],
                "filename": entry["filename"],
                "url": entry["url"],
                "sha256": entry["digests"]["sha256"],
            }
            if package["name"] == "tgconvertor"
            else package
            for package in packages
        ]
    version = next(p["version"] for p in packages if p["name"] == "tgconvertor")
    pyodide = ROOT / "node_modules/pyodide"
    for name in (
        "pyodide.mjs",
        "pyodide.asm.mjs",
        "pyodide.asm.wasm",
        "python_stdlib.zip",
        "pyodide-lock.json",
        "package.json",
        "README.md",
    ):
        shutil.copyfile(pyodide / name, DEST / name)
    crypto = json.loads((pyodide / "pyodide-lock.json").read_text())["packages"]["pycryptodome"]
    crypto_path = DEST / crypto["file_name"]
    crypto_data = (
        crypto_path.read_bytes()
        if crypto_path.exists()
        else get("https://cdn.jsdelivr.net/pyodide/v314.0.7/full/" + crypto["file_name"])
    )
    if hashlib.sha256(crypto_data).hexdigest() != crypto["sha256"]:
        raise ValueError("Pyodide cryptography package checksum mismatch")
    crypto_path.write_bytes(crypto_data)
    wheels = []
    for package in packages:
        destination = DEST / package["filename"]
        data = destination.read_bytes() if destination.exists() else b""
        if hashlib.sha256(data).hexdigest() != package["sha256"]:
            data = get(package["url"])
        if hashlib.sha256(data).hexdigest() != package["sha256"]:
            raise ValueError(f"Package checksum mismatch: {package['name']}")
        destination.write_bytes(data)
        if destination.suffix == ".whl":
            wheels.append(destination.name)
            if package["name"] == "tgconvertor":
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    license_name = next(
                        name for name in archive.namelist() if name.endswith("/LICENSE")
                    )
                    (ROOT / "public/licenses/tgconvertor-LICENSE").write_bytes(
                        archive.read(license_name)
                    )
        else:
            # pyaes publishes only an sdist; its pure Python module needs no compilation.
            bundled = DEST / "pyaes-source.zip"
            with (
                tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as source,
                zipfile.ZipFile(bundled, "w", zipfile.ZIP_DEFLATED) as archive,
            ):
                for member in source.getmembers():
                    relative = "/".join(member.name.split("/")[1:])
                    if member.isfile() and (
                        relative.startswith("pyaes/") or relative in ("LICENSE.txt", "PKG-INFO")
                    ):
                        archive.writestr(relative, source.extractfile(member).read())
            wheels.append(bundled.name)
            destination.unlink()
    (DEST / "manifest.json").write_text(
        json.dumps({"version": version, "pyodide": "314.0.7", "archives": wheels}) + "\n"
    )
    for obsolete in DEST.glob("tgconvertor-*.whl"):
        if obsolete.name not in wheels:
            obsolete.unlink()
    if args.tgconvertor_version != "pinned" and not args.development_wheel:
        # Change the committed pin only after all package downloads are verified.
        LOCK.write_text(json.dumps({"packages": packages}, indent=2) + "\n")
    print(f"Bundled TGConvertor {version}, Pyodide and {len(wheels)} verified packages in {DEST}")


if __name__ == "__main__":
    main()
