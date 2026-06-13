"""Platform routing and normalized download API."""

from pathlib import Path

from .adapters.bilibili import download_bilibili
from .adapters.ytdlp import download_with_ytdlp
from .config import Settings, load_settings
from .models import DownloadResult
from .utils import (
    detect_platform,
    is_http_url,
    normalize_media_url,
    normalize_quality,
)


def download_media(
    url: str,
    mode: str = "video",
    output_dir: str | Path | None = None,
    min_quality: str = "best",
    settings: Settings | None = None,
) -> DownloadResult:
    if not is_http_url(url):
        raise ValueError("请输入有效的 http/https 视频链接")
    if mode not in {"video", "audio"}:
        raise ValueError("下载模式必须是 video 或 audio")

    settings = settings or load_settings()
    destination = Path(output_dir) if output_dir else settings.download_dir
    quality = normalize_quality(min_quality)
    normalized_url = normalize_media_url(url)
    platform = detect_platform(normalized_url)

    if platform == "bilibili":
        if (
            settings.bilibili_cookie_browser
            and not settings.bilibili_cookie_file.is_file()
        ):
            return download_with_ytdlp(
                normalized_url,
                mode,
                destination,
                quality,
                settings,
            )
        try:
            return download_bilibili(
                normalized_url,
                mode,
                destination,
                quality,
                settings,
            )
        except Exception as exc:
            if "程序已停止，不会自动降级下载" in str(exc):
                raise
            print(f"[下载器] B站公开接口不可用，回退 yt-dlp：{exc}")
    return download_with_ytdlp(
        normalized_url,
        mode,
        destination,
        quality,
        settings,
    )
