"""Environment-backed application settings."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_BILIBILI_COOKIE_FILE = BASE_DIR / "space.bilibili.com_cookies.txt"


@dataclass(frozen=True)
class Settings:
    base_dir: Path
    download_dir: Path
    proxy: str
    bilibili_cookie_file: Path
    youtube_cookie_file: Path | None
    bilibili_cookie_browser: str


def _optional_path(value: str, base_dir: Path) -> Path | None:
    if not value.strip():
        return None
    path = Path(value).expanduser()
    return path if path.is_absolute() else base_dir / path


def load_settings(
    environ: Mapping[str, str] | None = None,
    base_dir: Path = BASE_DIR,
) -> Settings:
    env = os.environ if environ is None else environ
    bilibili_cookie = _optional_path(
        env.get("BILIBILI_COOKIES_FILE", ""),
        base_dir,
    ) or (base_dir / "space.bilibili.com_cookies.txt")
    youtube_cookie = _optional_path(
        env.get("YOUTUBE_COOKIES_FILE", ""),
        base_dir,
    )
    download_dir = _optional_path(env.get("DOWNLOAD_DIR", ""), base_dir)
    return Settings(
        base_dir=base_dir,
        download_dir=download_dir or (base_dir / "downloads"),
        proxy=env.get("VIDEO_PROXY", "").strip(),
        bilibili_cookie_file=bilibili_cookie,
        youtube_cookie_file=youtube_cookie,
        bilibili_cookie_browser=env.get(
            "BILIBILI_COOKIE_BROWSER",
            "",
        ).strip(),
    )
