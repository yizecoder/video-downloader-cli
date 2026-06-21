"""Platform-neutral URL, filename, quality, and Cookie helpers."""

import http.cookiejar
import os
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/137.0.0.0 Safari/537.36"
)

QUALITY_MINIMUMS = {
    "best": (0, 0),
    "720p": (64, 720),
    "1080p": (80, 1080),
    "4k": (120, 2160),
}


@dataclass(frozen=True)
class CookieStatus:
    path: Path
    exists: bool
    netscape_format: bool
    has_sessdata: bool


def ensure_dir(path: str | Path) -> Path:
    output = Path(path)
    output.mkdir(parents=True, exist_ok=True)
    return output


def is_http_url(source: str) -> bool:
    parsed = urlparse(source)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def normalize_media_url(url: str) -> str:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    if hostname == "douyin.com" or hostname.endswith(".douyin.com"):
        modal_id = parse_qs(parsed.query).get("modal_id", [""])[0]
        if modal_id.isdigit():
            return f"https://www.douyin.com/video/{modal_id}"
    if (
        (hostname == "bilibili.com" or hostname.endswith(".bilibili.com"))
        and parsed.path.startswith("/video/")
    ):
        query = parse_qs(parsed.query)
        clean_query = {"p": query["p"]} if "p" in query else {}
        return urlunparse(parsed._replace(query=urlencode(clean_query, doseq=True), fragment=""))
    return url


def read_url_file(path: str | Path) -> list[str]:
    """读取每行一个 URL 的 UTF-8 文本文件，忽略空行和整行注释。"""
    source = Path(path)
    try:
        lines = source.read_text(encoding="utf-8-sig").splitlines()
    except FileNotFoundError as exc:
        raise ValueError(f"URL 文件不存在：{source}") from exc
    except OSError as exc:
        raise ValueError(f"无法读取 URL 文件：{source}（{exc}）") from exc
    return [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")]


def unique_media_urls(urls: list[str]) -> list[str]:
    """规范化 URL 并按首次出现顺序去重。"""
    return list(dict.fromkeys(normalize_media_url(url) for url in urls))


def detect_platform(url: str) -> str:
    value = url.lower()
    if "bilibili.com" in value or "b23.tv" in value:
        return "bilibili"
    if "xiaohongshu.com" in value or "xhslink.com" in value:
        return "xiaohongshu"
    if "youtube.com" in value or "youtu.be" in value:
        return "youtube"
    if "douyin.com" in value or "iesdouyin.com" in value:
        return "douyin"
    return "unknown"


def sanitize_filename(name: str) -> str:
    value = re.sub(r'[\\/:*?"<>|]', "_", name).strip(" .")
    return value[:100] or "video"


def format_resolution_label(metadata: dict) -> str:
    width = int(metadata.get("width") or 0)
    height = int(metadata.get("height") or 0)
    if not width or not height:
        return ""
    quality = min(width, height)
    labels = {
        2160: "4K",
        1440: "1440P",
        1080: "1080P",
        720: "720P",
        480: "480P",
        360: "360P",
        240: "240P",
        144: "144P",
    }
    return labels.get(quality, f"{quality}P")


def normalize_quality(quality: str) -> str:
    value = quality.strip().lower()
    aliases = {
        "highest": "best",
        "max": "best",
        "720": "720p",
        "1080": "1080p",
        "2160": "4k",
        "2160p": "4k",
    }
    value = aliases.get(value, value)
    if value not in QUALITY_MINIMUMS:
        raise ValueError("画质要求必须是 best、720p、1080p 或 4k")
    return value


def validate_minimum_quality(metadata: dict, min_quality: str) -> None:
    normalized = normalize_quality(min_quality)
    if normalized == "best":
        return
    _, minimum_height = QUALITY_MINIMUMS[normalized]
    actual_height = int(metadata.get("height") or 0)
    actual_label = format_resolution_label(metadata) or "未知画质"
    required_label = "4K" if normalized == "4k" else normalized.upper()
    if actual_height and actual_height < minimum_height:
        resolution = metadata.get("resolution") or f"{actual_height}P"
        raise RuntimeError(
            f"该视频最高实际可下载画质为 {actual_label}（{resolution}），"
            f"低于你选择的至少 {required_label}。"
            "程序已停止，不会自动下载低清版本。请选择“最高可用”后重试。"
        )


def inspect_cookie_file(path: Path) -> CookieStatus:
    if not path.is_file():
        return CookieStatus(path, False, False, False)
    try:
        header = path.read_text(encoding="utf-8", errors="replace")[:256]
        is_netscape = "Netscape HTTP Cookie File" in header
        jar = http.cookiejar.MozillaCookieJar(str(path))
        jar.load(ignore_discard=True, ignore_expires=True)
        has_sessdata = any(cookie.name == "SESSDATA" for cookie in jar)
        return CookieStatus(path, True, is_netscape, has_sessdata)
    except (OSError, http.cookiejar.LoadError):
        return CookieStatus(path, True, False, False)


def finalize_filename(path: Path, metadata: dict, mode: str = "video") -> Path:
    title = sanitize_filename(str(metadata.get("title") or "video"))[:60]
    media_id = sanitize_filename(str(metadata.get("id") or path.stem))
    quality = format_resolution_label(metadata) if mode == "video" else ""
    suffix = f"_{quality}" if quality else ""
    final_path = path.with_name(f"{title}_{media_id}{suffix}{path.suffix}")
    if path != final_path:
        os.replace(path, final_path)
    return final_path
