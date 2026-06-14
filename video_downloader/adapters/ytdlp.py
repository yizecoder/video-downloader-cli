"""yt-dlp adapter for YouTube, Douyin, Xiaohongshu, and generic sites."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

from ..config import Settings
from ..models import DownloadResult
from ..utils import (
    BROWSER_USER_AGENT,
    QUALITY_MINIMUMS,
    detect_platform,
    ensure_dir,
    finalize_filename,
    format_resolution_label,
    normalize_quality,
    validate_minimum_quality,
)


def build_network_args(platform: str, settings: Settings) -> list[str]:
    args: list[str] = []
    if platform == "youtube" and settings.proxy:
        args += ["--proxy", settings.proxy]
    elif platform == "bilibili":
        args += ["--proxy", ""]

    if platform == "youtube":
        if shutil.which("deno"):
            args += ["--js-runtimes", "deno"]
        elif shutil.which("node"):
            args += ["--js-runtimes", "node"]

    if platform == "bilibili":
        if settings.bilibili_cookie_file.is_file():
            args += ["--cookies", str(settings.bilibili_cookie_file)]
        elif settings.bilibili_cookie_browser:
            args += [
                "--cookies-from-browser",
                settings.bilibili_cookie_browser,
            ]
        args += [
            "--referer",
            "https://www.bilibili.com/",
            "--user-agent",
            BROWSER_USER_AGENT,
        ]
    elif platform == "youtube" and settings.youtube_cookie_file:
        args += ["--cookies", str(settings.youtube_cookie_file)]
    elif platform == "douyin":
        args += [
            "--referer",
            "https://www.douyin.com/",
            "--user-agent",
            BROWSER_USER_AGENT,
        ]
    elif platform == "xiaohongshu":
        args += ["--user-agent", BROWSER_USER_AGENT]
    return args


def build_video_format(min_quality: str) -> str:
    _, minimum_height = QUALITY_MINIMUMS[normalize_quality(min_quality)]
    if minimum_height:
        return (
            f"bestvideo*[height>={minimum_height}]+bestaudio/"
            f"best[height>={minimum_height}]"
        )
    return "bestvideo*+bestaudio/best"


def format_error(platform: str, stderr: str) -> str:
    if platform == "youtube" and (
        "n challenge solving failed" in stderr
        or "No supported JavaScript runtime" in stderr
    ):
        return (
            "YouTube JS 挑战解析失败。请安装 Deno，或安装 Node.js 22+，"
            "并通过 pip install -U \"yt-dlp[default]\" 安装 EJS 组件。"
        )
    if platform == "youtube" and "cookies are no longer valid" in stderr:
        return (
            "YouTube Cookie 已失效或被浏览器轮换。请在无痕窗口登录 YouTube，"
            "同一标签页打开 https://www.youtube.com/robots.txt 后重新导出 Cookie，"
            "导出后立即关闭整个无痕窗口。"
        )
    if platform == "youtube" and "Sign in to confirm your age" in stderr:
        return (
            "该视频有年龄限制，当前 YouTube Cookie 未通过账号验证。"
            "请重新导出有效的登录 Cookie 后重试。"
        )
    if "Failed to decrypt with DPAPI" in stderr:
        return (
            "浏览器 Cookie 使用新版应用绑定加密，yt-dlp 无法解密。"
            "请为对应平台改用 Netscape 格式 Cookie 文件。"
        )
    if "Could not copy" in stderr and "cookie database" in stderr:
        return "浏览器仍在占用 Cookie 数据库，请完全退出浏览器后重试。"
    if platform == "bilibili" and (
        "HTTP Error 412" in stderr or "Precondition Failed" in stderr
    ):
        return "B站请求被风控拦截，请配置有效 B站 Cookie 文件后重试。"
    if platform == "youtube" and "Video unavailable" in stderr:
        return (
            "YouTube 返回 Video unavailable：视频可能已删除、设为私密、"
            "受地区限制，或视频 ID 不正确。请先确认浏览器中可以播放。"
        )
    if platform == "youtube" and "Sign in to confirm" in stderr:
        return (
            "YouTube 要求登录或人机验证。请导出 YouTube 的 Netscape Cookie，"
            "并通过 YOUTUBE_COOKIES_FILE 单独配置。"
        )
    if "Requested format is not available" in stderr:
        return "所要求的画质不可用。请选择“最高可用”或降低画质要求后重试。"
    return f"yt-dlp 下载失败：{stderr.strip()}"


def get_metadata(url: str, platform: str, settings: Settings) -> dict:
    command = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--no-playlist",
        "--no-warnings",
        "--skip-download",
        "--dump-single-json",
        *build_network_args(platform, settings),
        url,
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return {}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}


def _codec(metadata: dict, key: str) -> str:
    direct = str(metadata.get(key) or "")
    if direct and direct != "none":
        return direct
    requested = metadata.get("requested_downloads") or []
    for item in requested:
        value = str(item.get(key) or "")
        if value and value != "none":
            return value
    return ""


def download_with_ytdlp(
    url: str,
    mode: str,
    output_dir: Path,
    min_quality: str,
    settings: Settings,
) -> DownloadResult:
    output_dir = ensure_dir(output_dir)
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("未找到 ffmpeg，请安装后加入 PATH")
    try:
        import yt_dlp  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("未安装 yt-dlp，请运行：pip install yt-dlp") from exc

    platform = detect_platform(url)
    metadata = get_metadata(url, platform, settings)
    output_template = str(output_dir / "%(id)s.%(ext)s")
    command = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--no-playlist",
        "--no-warnings",
        "--print",
        "after_move:filepath",
        "-o",
        output_template,
    ]
    if mode == "audio":
        command += ["-x", "--audio-format", "mp3", "--audio-quality", "0"]
    else:
        validate_minimum_quality(metadata, min_quality)
        quality = format_resolution_label(metadata)
        resolution = metadata.get("resolution") or "分辨率未知"
        if quality:
            print(f"[下载器] 选择视频画质：{quality}（{resolution}）")
        command += [
            "-f",
            build_video_format(min_quality),
            "--merge-output-format",
            "mp4",
            "--remux-video",
            "mp4",
        ]
    command += build_network_args(platform, settings)
    command.append(url)

    print(f"[下载器] 平台：{platform}，模式：{'视频' if mode == 'video' else '音频'}")
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(format_error(platform, result.stderr))

    for line in reversed(result.stdout.splitlines()):
        candidate = Path(line.strip().strip('"'))
        if candidate.is_file():
            final_path = finalize_filename(candidate, metadata, mode)
            return DownloadResult(
                path=final_path,
                platform=platform,
                mode=mode,
                width=int(metadata.get("width") or 0),
                height=int(metadata.get("height") or 0),
                quality=(
                    "MP3"
                    if mode == "audio"
                    else format_resolution_label(metadata)
                ),
                video_codec="" if mode == "audio" else _codec(metadata, "vcodec"),
                audio_codec="mp3" if mode == "audio" else _codec(metadata, "acodec"),
            )
    raise RuntimeError("下载命令执行完成，但没有找到输出文件")
