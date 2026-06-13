"""Bilibili adapter using public web APIs and ffmpeg."""

import http.cookiejar
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from ..config import Settings
from ..models import DownloadResult
from ..utils import (
    BROWSER_USER_AGENT,
    QUALITY_MINIMUMS,
    ensure_dir,
    inspect_cookie_file,
    normalize_quality,
    sanitize_filename,
)

BILIBILI_QUALITY_LABELS = {
    127: "8K",
    126: "杜比视界",
    125: "HDR",
    120: "4K",
    116: "1080P60",
    112: "1080P+",
    80: "1080P",
    74: "720P60",
    64: "720P",
    32: "480P",
    16: "360P",
}


def extract_bilibili_bvid(url: str) -> str:
    match = re.search(r"\b(BV[a-zA-Z0-9]+)\b", url, re.IGNORECASE)
    if not match:
        raise ValueError("未能从链接中识别 B站 BV 号")
    return match.group(1)


def _requests_session(settings: Settings):
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError("缺少 requests，请运行：pip install requests") from exc

    session = requests.Session()
    session.trust_env = False
    cookie_path = settings.bilibili_cookie_file
    if cookie_path.is_file():
        jar = http.cookiejar.MozillaCookieJar(str(cookie_path))
        jar.load(ignore_discard=True, ignore_expires=True)
        session.cookies.update(jar)
    return session


def _headers(bvid: str) -> dict:
    return {
        "User-Agent": BROWSER_USER_AGENT,
        "Referer": f"https://www.bilibili.com/video/{bvid}/",
    }


def get_bilibili_metadata(url: str, settings: Settings) -> dict:
    bvid = extract_bilibili_bvid(url)
    response = _requests_session(settings).get(
        "https://api.bilibili.com/x/web-interface/view",
        params={"bvid": bvid},
        headers=_headers(bvid),
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != 0 or not payload.get("data"):
        raise RuntimeError(f"B站元数据接口失败：{payload.get('message', '未知错误')}")
    return payload["data"]


def _page_context(url: str, settings: Settings) -> tuple[dict, dict, str]:
    metadata = get_bilibili_metadata(url, settings)
    pages = metadata.get("pages") or []
    try:
        page_number = int(parse_qs(urlparse(url).query).get("p", ["1"])[0])
    except ValueError as exc:
        raise ValueError("B站分 P 参数必须是数字") from exc
    if page_number < 1 or page_number > max(1, len(pages)):
        raise ValueError(f"分 P 参数超出范围：p={page_number}")
    page = pages[page_number - 1] if pages else metadata
    title = metadata.get("title") or metadata["bvid"]
    if len(pages) > 1:
        title += f"_P{page_number}_{page.get('part') or page_number}"
    return metadata, page, title


def _get_play_info(url: str, settings: Settings, fnval: int) -> tuple[dict, str]:
    metadata, page, title = _page_context(url, settings)
    bvid = metadata["bvid"]
    response = _requests_session(settings).get(
        "https://api.bilibili.com/x/player/playurl",
        params={
            "bvid": bvid,
            "cid": page.get("cid") or metadata.get("cid"),
            "qn": 127,
            "fnval": fnval,
            "fourk": 1,
        },
        headers=_headers(bvid),
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != 0:
        raise RuntimeError(f"B站播放接口失败：{payload.get('message', '未知错误')}")
    return payload["data"], title


def _stream_urls(stream: dict) -> list[str]:
    urls = [
        stream.get("baseUrl") or stream.get("base_url"),
        *(stream.get("backupUrl") or stream.get("backup_url") or []),
    ]
    return [url for url in urls if url]


def _download_stream(session, urls: list[str], path: Path, headers: dict) -> None:
    last_error = None
    for url in urls:
        try:
            with session.get(
                url,
                headers=headers,
                stream=True,
                timeout=(20, 90),
            ) as response:
                response.raise_for_status()
                with path.open("wb") as output:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            output.write(chunk)
            return
        except Exception as exc:
            last_error = exc
            path.unlink(missing_ok=True)
    raise RuntimeError(f"媒体流下载失败：{last_error}")


def _run_ffmpeg(args: list[str], error_prefix: str) -> None:
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-y", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(f"{error_prefix}：{result.stderr.strip()}")


def _video_rank(item: dict) -> tuple:
    codecs = item.get("codecs", "")
    compatibility = 1 if codecs.startswith("avc") else 0
    return (
        item.get("id", 0),
        item.get("height", 0),
        item.get("width", 0),
        compatibility,
        item.get("bandwidth", 0),
    )


def download_bilibili(
    url: str,
    mode: str,
    output_dir: Path,
    min_quality: str,
    settings: Settings,
) -> DownloadResult:
    output_dir = ensure_dir(output_dir)
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("未找到 ffmpeg，请安装后加入 PATH")

    play_info, title = _get_play_info(url, settings, fnval=4048)
    bvid = extract_bilibili_bvid(url)
    headers = _headers(bvid)
    session = _requests_session(settings)
    safe_title = sanitize_filename(title)

    audio_streams = (play_info.get("dash") or {}).get("audio") or []
    if not audio_streams:
        raise RuntimeError("B站未返回可用音频流，视频可能需要登录或付费")
    audio = max(audio_streams, key=lambda item: item.get("bandwidth", 0))
    raw_audio = output_dir / f".{safe_title}_{bvid}.audio.part"

    if mode == "audio":
        output_path = output_dir / f"{safe_title}_{bvid}.mp3"
        try:
            _download_stream(session, _stream_urls(audio), raw_audio, headers)
            _run_ffmpeg(
                [
                    "-i",
                    str(raw_audio),
                    "-vn",
                    "-codec:a",
                    "libmp3lame",
                    "-q:a",
                    "2",
                    str(output_path),
                ],
                "音频转换失败",
            )
        finally:
            raw_audio.unlink(missing_ok=True)
        return DownloadResult(
            path=output_path,
            platform="bilibili",
            mode="audio",
            quality="MP3",
            audio_codec="mp3",
        )

    video_streams = (play_info.get("dash") or {}).get("video") or []
    if not video_streams:
        raise RuntimeError("B站未返回可用视频流，视频可能需要登录或付费")
    video = max(video_streams, key=_video_rank)
    dash_quality = int(video.get("id") or 0)

    try:
        progressive_info, _ = _get_play_info(url, settings, fnval=0)
    except Exception as exc:
        print(f"[下载器] 传统视频流检查失败，继续使用 DASH：{exc}")
        progressive_info = {}
    progressive_quality = int(progressive_info.get("quality") or 0)
    progressive_parts = progressive_info.get("durl") or []
    available_quality = max(
        dash_quality,
        progressive_quality if progressive_parts else 0,
    )
    minimum_quality_id, _ = QUALITY_MINIMUMS[normalize_quality(min_quality)]
    if available_quality < minimum_quality_id:
        available_label = BILIBILI_QUALITY_LABELS.get(
            available_quality,
            f"Q{available_quality}",
        )
        required_label = BILIBILI_QUALITY_LABELS.get(
            minimum_quality_id,
            min_quality.upper(),
        )
        platform_supports_target = minimum_quality_id in (
            play_info.get("accept_quality") or []
        )
        reason = (
            "平台支持该画质，但当前请求没有获得对应媒体流。"
            if platform_supports_target
            else "该视频或当前账号不提供该画质。"
        )
        login = inspect_cookie_file(settings.bilibili_cookie_file).has_sessdata
        raise RuntimeError(
            f"最高实际可下载画质为 {available_label}，低于要求的 {required_label}。"
            f"{reason} B站 1080P/4K 通常需要包含 SESSDATA 的登录 Cookie 文件；"
            f"当前登录态：{'已检测到 SESSDATA' if login else '未检测到 SESSDATA'}。"
            "程序已停止，不会自动降级下载。"
        )

    if progressive_parts and progressive_quality > dash_quality:
        quality = BILIBILI_QUALITY_LABELS.get(
            progressive_quality,
            f"Q{progressive_quality}",
        )
        dimension = progressive_info.get("dimension") or {}
        width = int(dimension.get("width") or 0)
        height = int(dimension.get("height") or 0)
        print(f"[下载器] 选择视频画质：{quality}")
        output_path = output_dir / f"{safe_title}_{bvid}_{quality}.mp4"
        raw_parts: list[Path] = []
        concat_file = output_dir / f".{safe_title}_{bvid}.concat.txt"
        try:
            for index, part in enumerate(progressive_parts, start=1):
                raw_part = output_dir / f".{safe_title}_{bvid}.{index}.video.part"
                urls = [part.get("url"), *(part.get("backup_url") or [])]
                _download_stream(
                    session,
                    [item for item in urls if item],
                    raw_part,
                    headers,
                )
                raw_parts.append(raw_part)
            if len(raw_parts) == 1:
                _run_ffmpeg(
                    [
                        "-i",
                        str(raw_parts[0]),
                        "-c",
                        "copy",
                        "-movflags",
                        "+faststart",
                        str(output_path),
                    ],
                    "视频封装失败",
                )
            else:
                concat_file.write_text(
                    "".join(f"file '{path.as_posix()}'\n" for path in raw_parts),
                    encoding="utf-8",
                )
                _run_ffmpeg(
                    [
                        "-f",
                        "concat",
                        "-safe",
                        "0",
                        "-i",
                        str(concat_file),
                        "-c",
                        "copy",
                        "-movflags",
                        "+faststart",
                        str(output_path),
                    ],
                    "分段视频合并失败",
                )
        finally:
            for raw_part in raw_parts:
                raw_part.unlink(missing_ok=True)
            concat_file.unlink(missing_ok=True)
        return DownloadResult(
            path=output_path,
            platform="bilibili",
            mode="video",
            width=width,
            height=height,
            quality=quality,
        )

    width = int(video.get("width") or 0)
    height = int(video.get("height") or 0)
    quality = BILIBILI_QUALITY_LABELS.get(dash_quality, f"Q{dash_quality}")
    resolution = f"{width}x{height}" if width and height else "分辨率未知"
    print(f"[下载器] 选择视频画质：{quality}（{resolution}）")
    raw_video = output_dir / f".{safe_title}_{bvid}.video.part"
    output_path = output_dir / f"{safe_title}_{bvid}_{quality}.mp4"
    try:
        _download_stream(session, _stream_urls(video), raw_video, headers)
        _download_stream(session, _stream_urls(audio), raw_audio, headers)
        _run_ffmpeg(
            [
                "-i",
                str(raw_video),
                "-i",
                str(raw_audio),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                str(output_path),
            ],
            "视频和音频合并失败",
        )
    finally:
        raw_video.unlink(missing_ok=True)
        raw_audio.unlink(missing_ok=True)
    return DownloadResult(
        path=output_path,
        platform="bilibili",
        mode="video",
        width=width,
        height=height,
        quality=quality,
        video_codec=str(video.get("codecs") or ""),
        audio_codec=str(audio.get("codecs") or ""),
    )
