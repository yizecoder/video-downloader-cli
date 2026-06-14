# Repository Guidelines

## Scope

This repository is an independent Python CLI project. Keep changes inside this directory and do
not rely on files from sibling projects. Real Cookie files and downloaded media are local-only.

## Structure

- `video_downloader/`: application package
- `video_downloader/adapters/`: platform-specific integrations
- `tests/`: offline `unittest` tests
- `scripts/`: release and validation helpers

Keep platform behavior in adapters, orchestration in `core.py`, and CLI behavior in `cli.py`.

## Commands

```powershell
python -m pip install -r requirements-dev.txt
python main.py --check
python -m unittest discover -s tests -v
ruff check .
python scripts\prepublish_check.py
```

Target Python 3.10+, four-space indentation, and Ruff's configured 100-character line limit.
Use `snake_case` for functions and modules, `PascalCase` for classes, and Conventional Commit
prefixes such as `fix:`, `docs:`, and `chore:`.

Tests must not access live video sites or contain real Cookie values. Never commit downloads,
browser profiles, API keys, `space.bilibili.com_cookies.txt`, or `www.youtube.com_cookies.txt`.
