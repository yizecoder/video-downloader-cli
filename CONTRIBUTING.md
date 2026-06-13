# Contributing

Video Downloader CLI officially supports Windows and Python 3.10 or newer.

## Development setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python main.py --check
```

## Before submitting a change

```powershell
python -m compileall -q main.py video_downloader tests scripts
python -m unittest discover -s tests -v
ruff check .
python scripts\prepublish_check.py
python -m pip check
```

Tests must not access live video sites or contain real Cookie values. Keep
platform behavior in its adapter and return a `DownloadResult` to the core.

## Pull requests

- Explain the user-visible behavior and affected platform.
- Add tests for parsing, configuration, or error mapping changes.
- Do not include downloads, browser profiles, Cookie files, or private URLs.
- Keep unrelated formatting and refactoring out of the same change.
