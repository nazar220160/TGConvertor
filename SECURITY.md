# Security policy

## Supported versions

Security fixes target the latest stable release on [PyPI](https://pypi.org/project/tgconvertor/) and the current [web panel](https://nazar220160.github.io/TGConvertor/). Older releases may require an upgrade; there is no separate long-term support branch.

## Private reports

Use [GitHub private vulnerability reporting](https://github.com/nazar220160/TGConvertor/security/advisories/new) to report a vulnerability to the maintainer. Do not post vulnerability details in public issues or discussions before coordinated disclosure.

Include the affected version, API/CLI/panel entry point, expected impact and reproducible steps using synthetic data. Useful examples include unsafe archive extraction, unexpected network requests, disclosure of session data or unintended modification of source files. Reports are reviewed by the maintainer; no fixed response deadline is promised.

Never attach real session files, session strings, tdata folders, auth keys, API hashes or passcodes, including to a private report. A synthetic reproduction is sufficient. If an authorization has already been exposed, revoke that affected authorization using Telegram's active-session controls.

## Scope and handling

The package transfers Telegram authorization data. Treat input and output as credentials. Conversion runs offline; explicitly requested client validation contacts Telegram. The panel processes sessions in memory on the user's device, and its offline cache contains only static application/runtime assets. Downloaded outputs and copied strings remain the user's responsibility.

Issues in upstream clients or the Python/WebAssembly runtime may require an upstream fix. Include the dependency version when relevant so the maintainer can coordinate the report.
