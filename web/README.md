# Browser workspace

**[Open the free web panel](https://nazar220160.github.io/TGConvertor/)**.

The panel runs the published TGConvertor package pinned in `runtime-lock.json` in a Python 3.14 WebAssembly worker. It supports Telethon files/strings, GramJS strings/UTF-8 text files, Pyrogram and Kurigram SQLite files and their shared string format, and Telegram Desktop tdata ZIP archives with or without a local passcode. Russian and English interfaces, source inspection, synthetic demo sessions, string masking, downloads, account selection and custom API credentials are included.

## Privacy and limits

All runtime assets are hosted alongside the panel. Starting it downloads about 20 MB of Python and library assets; no CDN, analytics or third-party fonts are used. Session bytes, strings and passcodes stay in this tab's memory. They are not uploaded or saved in browser storage. Only the language preference is saved. Python socket connections are blocked; the worker's fetch, WebSocket and XMLHttpRequest transports are disabled after initialization. The production Content Security Policy restricts connections to the same origin.

“Clear workspace” cancels outstanding work, revokes result URLs, clears inputs and replaces the worker. Closing the tab also releases its workspace. This does not erase downloaded files or the system clipboard. A browser cannot promise forensic erasure of every memory copy.

Files are limited to 32 MB; ZIP archives to 256 entries and 64 MB unpacked. ZIP paths, duplicates and symbolic links are checked before extraction. Select a ZIP containing one tdata folder with its `key_data` files. A tdata passcode means the local Desktop passcode, not the Telegram login password. Only the selected account is converted; message history and cache are not transferred.

The panel deliberately does not contact Telegram or verify authorization online. “Try a demo” uses an invented key that cannot authorize an account. Telethon and GramJS lack the owner's user ID; provide the real ID when exporting it to Pyrogram/Kurigram or tdata. Modern browsers with WebAssembly and module workers are required; the interface was manually checked in Chromium at desktop and mobile widths.

## Local development

Requires Node.js 22.12+ (CI uses 24) and Python 3.10+ (CI uses 3.14). From the repository root:

```bash
python -m venv .venv
.venv/bin/python -m pip install '.[dev,tdata]'
npm ci --prefix web
npm run prepare:runtime --prefix web
npm run dev --prefix web
```

On Windows use `.venv\Scripts\python` instead. The runtime preparation command uses `python3`; it needs only Python's standard library and no activated virtual environment.

To test the exact production CSP and assets:

```bash
npm run build --prefix web
npm run preview --prefix web
```

## Tests and deployment

Use a new temporary folder for generated fixtures (these contain only synthetic authorizations):

```bash
.venv/bin/python web/tests/generate_fixtures.py /tmp/tgconvertor-web-fixtures
npm test --prefix web -- /tmp/tgconvertor-web-fixtures
.venv/bin/python web/tests/verify_outputs.py /tmp/tgconvertor-web-fixtures
```

Tests execute the same Python adapter and published package inside the real Pyodide runtime. They cover all 81 directions across nine representations, inspection of each output, all demo format pairs, invalid input, unsafe archives, passcodes, custom API credentials and cleanup. Independent native Telethon/GramJS/OpenTele2/SQLite/string readers validate every exported key, data center, owner and schema. AES-IGE and PBKDF2 are compared with native cryptography vectors.

`.github/workflows/web.yml` tests and builds pull requests. Successful master builds deploy the tested artifact to free GitHub Pages; select **Settings → Pages → Source → GitHub Actions** once. After a successful tag-based Publish workflow, `workflow_run` automatically starts the panel workflow from master, using the published release tag as its library version. This respects the Pages environment's master-only deployment policy; no tag access or protection changes are required. Its build waits briefly if PyPI metadata has not propagated, downloads that published wheel, runs the full browser/native/PWA checks, and deploys only the passing artifact. Updating the library version and pushing its release tag is enough; no manual web pin changes or extra deployment token are needed. The static `web/dist` folder can also be hosted on any static host, including Vercel; no Python backend or paid plan is needed. Relative assets support repository subpaths. Session fixtures are never deployed.

## Browser adaptations and dependencies

The library's public conversion API is unchanged. `browser_engine.py` supplies AES-IGE using PyCryptodome's AES primitive, a PBKDF2 fallback, exclusive file copying where WASM lacks hard links, and direct execution of `asyncio.to_thread` inside the already isolated worker. Tests compare these adaptations with native behavior. Native-only dependencies and unused CLI/scraper dependencies are omitted from the web runtime.

`package-lock.json` pins JavaScript dependencies. Runtime preparation resolves the latest stable TGConvertor release from PyPI by default, verifies the wheel's SHA-256 and records the resolved version in `runtime-lock.json` and the deployed manifest. Other Python dependencies remain pinned. The UI obtains its displayed version from the installed Python package and checks it against that manifest. PyPI requests happen at build time; the browser loads only the tested self-hosted artifact, including when offline. Python wheels retain their upstream license files.

For local development, the normal preparation command already selects the latest stable PyPI release. To reproduce a recorded artifact or explicitly test a release:

```bash
npm run update:library --prefix web -- pinned
npm run update:library --prefix web -- v0.3.0
```

Release publication and panel deployment are connected in CI. Normal compatible library updates require no UI changes; a change to the conversion API or new native dependencies may require a browser adapter update, and failing browser tests prevent deployment. The npm package's own version is not used as the library version.

## Installable PWA and offline reopening

Open the production panel online once and wait for **Available offline**. Its service worker verifies and caches the complete app and Python runtime, so future reopening and conversion work without a network connection. You can install the panel using your browser's **Install app / Add to Home Screen** action. HTTPS is required outside localhost. Dev mode intentionally does not register a service worker; test with `npm run build` and `npm run preview`.

Only the build's allowlisted static files are cached: never uploaded sessions, strings, passcodes, downloads, POST requests or arbitrary URLs. Browser storage eviction or manually clearing site data removes the offline copy; reopen online to restore it. A changed build gets its own cache, and an incomplete/corrupt installation cannot replace the working copy.

Opening or refreshing an untouched panel automatically applies a complete update once its converter finishes initialization, provided this is the only open tab of the panel. Returning to the tab or reconnecting also checks for updates (at most once a minute). Sessions, partially entered options, format choices, demos and results prevent an automatic reload. With an active workspace or additional tabs, **Apply update and clear workspace** remains available; download results before using it. Browser copies installed before this fix need that button once, or all panel tabs must be closed and reopened, to load the new update controller. Old caches belonging to this panel are removed after activation; other applications' caches are preserved.

`npm run test:pwa --prefix web` tests the actual generated service worker and the TypeScript update controller, including offline reopening at a repository subpath, hash failures, partial downloads, automatic and explicit activation, workspace protection, multiple tabs, reconnecting, legacy workers and exclusion of session data. A real Chromium offline reload and tdata conversion were also manually verified. A static host is needed for the first installation and updates; there is no server-side Python execution.

Third-party runtime sources and licenses: [Pyodide](https://github.com/pyodide/pyodide/tree/314.0.7) (MPL-2.0), [CPython](https://github.com/python/cpython) (PSF), [PyCryptodome](https://github.com/Legrandin/pycryptodome) (BSD/public domain), [OpenTele2](https://github.com/DedInc/opentele2) (MIT), [Telethon](https://github.com/LonamiWebs/Telethon) (MIT), [pyaes](https://github.com/ricmoo/pyaes) (MIT), [python-rsa](https://github.com/sybrenstuvel/python-rsa) (Apache-2.0), [pyasn1](https://github.com/pyasn1/pyasn1) (BSD). The application is covered by the repository's MIT license. Upstream runtime files are redistributed unmodified. Full license texts are shipped in `public/licenses` and [third-party notices](public/THIRD-PARTY.txt) identify the sources.

GramJS uses version 1 StringSession strings or `.txt` files in both directions. The same Python codec is used in the browser; the npm SDK is only a native reader/writer for CI checks. GramJS StoreSession folders/localStorage are not imported directly.

For pre-release development, build a wheel and run `python scripts/prepare_runtime.py --development-wheel /absolute/path/to/tgconvertor-version-py3-none-any.whl`. This does not change the published PyPI pin. CI tests the candidate wheel before release and deploys the published wheel automatically after the tag's Publish workflow succeeds.
