# Contributing

## Questions, bugs and pull requests

Ask usage questions in [Discussions](https://github.com/nazar220160/TGConvertor/discussions). Use the [issue forms](https://github.com/nazar220160/TGConvertor/issues/new/choose) for bugs and feature requests; include package/Python versions, the conversion direction and a synthetic reproduction. For vulnerabilities, follow [SECURITY.md](SECURITY.md).

Before a pull request, check existing issues and discuss substantial API or format changes. Keep changes focused, document user-visible behavior, and test the affected conversion paths. The pull request template asks for a short explanation and the checks you actually ran. Never include real session files, session strings, passcodes or API hashes in examples, attachments or logs.

## Local checks

Use Python 3.10–3.14 and a virtual environment:

```bash
python -m venv .venv
# POSIX; on Windows use .venv\Scripts\activate
source .venv/bin/activate
python -m pip install -e '.[dev]'
ruff check .
ruff format --check .
python -m pytest --cov=TGConvertor --cov-report=term-missing -m 'not live'
python -m build
python -m twine check --strict dist/*
```

To exercise upstream clients, install `.[dev,telethon,kurigram,tdata]`. Test `.[dev,pyrogram]` in another virtual environment. All ordinary tests use synthetic keys and block network connections. Optional integration tests skip only when the relevant dependency is absent. CI verifies the expected extra is actually installed.

Coverage must remain at least 85%, including branches. Tests should check behavior and upstream compatibility, especially input integrity, failed writes, schema changes, identity handling, and CLI piping.

Dependency minimums in `pyproject.toml` match the latest stable PyPI releases verified on 2026-10-03, including runtime, optional clients, development tools, and the build backend. Future compatible updates remain allowed within the declared ranges. When updating dependencies, check their Python requirements, update the minimum-dependency CI pins, and rerun the Python/extra matrix. The tdata adapter uses `opentele2`; the original `opentele` and PyQt5 are not package dependencies.

`tests/test_conversion_matrix.py` explicitly covers all **81 input/output combinations** across nine representations: Telethon file/string, Pyrogram file, Kurigram file, their shared string, GramJS text/string, and tdata with/without a local passcode. Each combination runs through `convert()`, `SessionManager`, the Typer CLI, and the installed console command in a separate process (**324 conversion cases**). Tests check authorization and representable metadata, source integrity, output schemas, stdout/stderr, paths with spaces, and independent native readers when installed. Network access is blocked inside CLI subprocesses as well.

`tests/test_conversion_profiles.py` additionally checks bot/test-DC conversions and rejected tdata exports, required owner IDs, and main/explicit account selection from native multi-account tdata. Codec tests cover IPv6, custom ports, legacy strings, malformed data, concurrency, and write failures. The `info`, help, version, format listing, argument validation, stdin, and environment options also have tests. Offline tests cannot establish whether a real account is currently authorized or whether Telegram Desktop's GUI accepts a directory.

## CI

`checks.yml` is shared by `ci.yml` and `publish.yml`. Every release runs checks on its tagged commit:

- Python 3.10–3.14 on Ubuntu, for the base package and each of `telethon`, `pyrogram`, `kurigram`, and `tdata` separately.
- Combined Telethon/Kurigram/tdata environments on Python 3.10 and 3.14, with the full conversion matrix and native readers enabled.
- Base package on Windows and macOS with Python 3.10 and 3.14, plus representative tdata checks on both platforms.
- Minimum supported Typer/Rich versions on Python 3.10.
- Ruff lint/format, dependency consistency, unit tests and offline upstream interoperability tests.
- Build the sdist, then the wheel from that sdist; validate metadata and run tests against an installed wheel outside the checkout.

No Telegram credentials are stored in Actions. Dependency and Actions updates arrive through Dependabot. Actions are pinned by commit SHA.

## Optional live verification

Use a separate production user test account and an **already authorized local file**. The live suite reads account identity and checks conversions; it does not send messages, prompt for login, create account authorizations, or log out/revoke an account. It is excluded from CI.

Set these variables locally (keep values out of issue reports and terminal recordings):

- `TGCONVERTOR_RUN_LIVE=1`
- `TGCONVERTOR_LIVE_SESSION`: absolute path to the existing file/directory.
- `TGCONVERTOR_LIVE_FORMAT`: `telethon` (default), `pyrogram`, or `tdata`.
- `TGCONVERTOR_API_ID` and `TGCONVERTOR_API_HASH`: preferably your application's credentials. Set both or neither; when neither is set, the Desktop compatibility preset is used.
- `TGCONVERTOR_TDATA_PASSCODE`: only if reading a protected tdata directory.

```bash
python -m pip install -e '.[dev,telethon,kurigram,tdata]'
python -m pytest tests/test_live.py -m live -q -x --tb=short
# Repeat in another virtual environment with Pyrogram instead of Kurigram:
python -m pip install -e '.[dev,telethon,pyrogram,tdata]'
python -m pytest tests/test_live.py -m live -q -x --tb=short
```

First, a private copy of the original input is opened directly with its native SDK and checked against Telegram. The suite then exercises all 81 input/output combinations through `convert()`, `SessionManager`, CLI and the installed console command (324 conversion cases), plus real `validate()`, owner lookup, async-context cleanup and the public native client builder.

Native Telethon opens Telethon files/strings; native Pyrogram or Kurigram opens its own file schema and the shared strings; OpenTele2 opens tdata and connects through `ToTelethon(flag=UseCurrentSession)`. Each output must retain the original key and receive the original account ID from an actual `get_me()` response. File outputs for the other Pyrogram/Kurigram backend are explicitly skipped; running both environments covers every case, and shared strings are authenticated through both SDKs. All extras are required, so absent SDKs cannot silently hide the live matrix.

Requests run sequentially, with a short pause. Explicit Telegram FloodWait responses up to 60 seconds are respected and retried at most twice; authorization errors fail immediately. Keep `-x` to stop on the first failure. Source files are read only, and private copies and converted outputs are removed even after failures. Session strings travel through stdin rather than command arguments, and logging/assertion expansion is suppressed to avoid exposing credentials. Desktop GUI acceptance still needs a check in Telegram Desktop if required for a release; SDK authentication tests establish server authorization.

## Publishing

1. Update `project.version` in `pyproject.toml`, the custom `APIData.app_version` default if relevant, and the changelog. Run all local checks and inspect CI.
2. Keep the existing repository/environment `PYPI_TOKEN` secret for compatibility, **or** configure [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/adding-a-publisher/) and then remove the token. The Trusted Publisher must identify owner `nazar220160`, repository `TGConvertor`, workflow `publish.yml`, and environment `pypi`.
3. Tag the reviewed commit with exactly `v<project.version>`, for example `v0.3.0`, and push that tag.
4. `publish.yml` runs the entire check workflow, verifies tag/version equality, downloads the tested distributions, and publishes them to PyPI. If `PYPI_TOKEN` is present, the token path is used; otherwise the job uses OIDC Trusted Publishing with attestations.
5. Only after PyPI succeeds, the workflow creates the GitHub release with notes from the changelog and the same wheel/sdist assets.
6. A successful Publish run automatically triggers `web.yml` from master. It bundles that released PyPI version, runs browser/native/PWA checks and updates GitHub Pages. See [web/README.md](web/README.md) for panel development and offline caching.

Configure tag rules and the `pypi` environment according to the repository's maintainer policy. The workflows use read-only permissions for checks, `id-token: write` only for publishing, and `contents: write` only for creating the GitHub release. A failed check or a mismatched tag blocks publication. Published PyPI versions cannot be replaced; use a new version for fixes.

The code changes alone do not configure an external PyPI Trusted Publisher or create/push a release tag. The existing token path continues to work without migrating authentication.

### Native GramJS and browser release checks

```bash
npm ci --prefix web
TGCONVERTOR_GRAMJS_REQUIRED=1 python -m pytest -m 'not live'
python -m build --wheel
python web/scripts/prepare_runtime.py --development-wheel dist/tgconvertor-0.3.0-py3-none-any.whl
python web/tests/generate_fixtures.py /tmp/new-empty-fixture-directory
npm test --prefix web -- /tmp/new-empty-fixture-directory
python web/tests/verify_outputs.py /tmp/new-empty-fixture-directory
npm run build --prefix web
npm run test:pwa --prefix web
```

The pinned `telegram` npm package is a test-only native interoperability dependency. It is not bundled into the web panel. Development wheels do not update `runtime-lock.json`. A master push with an unpublished Python version tests the candidate and waits to deploy until the tag publishes it on PyPI. The Publish follow-up then rebuilds and verifies the released PyPI wheel before deploying Pages.
