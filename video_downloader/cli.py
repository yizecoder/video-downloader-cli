"""Command-line and interactive user interface."""

import argparse
import importlib.util
import shutil
import sys
import time
from pathlib import Path

from .config import Settings, load_settings
from .core import download_media
from .models import DownloadResult
from .utils import inspect_cookie_file

VERSION = "2.0.0"


def configure_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")


def print_banner() -> None:
    print("=" * 60)
    print(f"  Video Downloader CLI v{VERSION}")
    print("  支持：高清视频下载 / MP3 音频下载")
    print("=" * 60)
    print()


def _cookie_summary(path: Path) -> str:
    status = inspect_cookie_file(path)
    if not status.exists:
        return "文件不存在"
    return "Netscape" if status.netscape_format else "格式无效"


def check_environment(settings: Settings | None = None) -> bool:
    settings = settings or load_settings()
    js_runtime = shutil.which("deno") or shutil.which("node")
    checks = [
        ("Python >= 3.10", sys.version_info >= (3, 10), sys.version.split()[0]),
        (
            "yt-dlp",
            importlib.util.find_spec("yt_dlp") is not None,
            'pip install -U "yt-dlp[default]"',
        ),
        (
            "yt-dlp-ejs",
            importlib.util.find_spec("yt_dlp_ejs") is not None,
            'pip install -U "yt-dlp[default]"',
        ),
        (
            "YouTube JS runtime",
            js_runtime is not None,
            "安装 Deno 2.3+ 或 Node.js 22+",
        ),
        ("requests", importlib.util.find_spec("requests") is not None, "pip install requests"),
        ("ffmpeg", shutil.which("ffmpeg") is not None, "安装 ffmpeg 并加入 PATH"),
    ]
    print("\n环境自检：")
    required_ok = True
    for name, ok, detail in checks:
        suffix = f"：{detail}" if not ok else ""
        print(f"  [{'OK' if ok else '缺失'}] {name}{suffix}")
        required_ok = required_ok and ok
    if js_runtime:
        print(f"  YouTube JS runtime：{Path(js_runtime).name}")

    bili_status = inspect_cookie_file(settings.bilibili_cookie_file)
    print(f"  下载目录：{settings.download_dir.resolve()}")
    print(f"  B站 Cookie：{settings.bilibili_cookie_file.resolve()}")
    print(f"  B站 Cookie 格式：{_cookie_summary(settings.bilibili_cookie_file)}")
    login = "已登录" if bili_status.has_sessdata else "未登录"
    print(f"  B站登录态：{login}")
    if settings.youtube_cookie_file:
        print(f"  YouTube Cookie：{settings.youtube_cookie_file.resolve()}")
        print(
            "  YouTube Cookie 格式："
            f"{_cookie_summary(settings.youtube_cookie_file)}"
        )
    else:
        print("  YouTube Cookie：未配置")
    print("\n结论：" + ("基础环境可运行" if required_ok else "基础环境不完整"))
    return required_ok


def _print_result(result: DownloadResult, elapsed: int) -> None:
    print()
    print("=" * 60)
    print(f"  下载完成，耗时 {elapsed // 60}分{elapsed % 60}秒")
    print(f"  文件位置：{result.path}")
    print(f"  平台/模式：{result.platform} / {result.mode}")
    if result.quality:
        print(f"  清晰度：{result.quality}")
    if result.resolution:
        print(f"  分辨率：{result.resolution}")
    codecs = " / ".join(
        value for value in (result.video_codec, result.audio_codec) if value
    )
    if codecs:
        print(f"  编码：{codecs}")
    print("=" * 60)


def process_url(
    url: str,
    mode: str = "video",
    min_quality: str = "best",
    settings: Settings | None = None,
) -> DownloadResult:
    settings = settings or load_settings()
    label = "高清视频" if mode == "video" else "MP3 音频"
    print(f"\n[主程序] 开始下载{label}：{url}")
    print("-" * 60)
    started_at = time.time()
    result = download_media(
        url,
        mode=mode,
        output_dir=settings.download_dir,
        min_quality=min_quality,
        settings=settings,
    )
    _print_result(result, int(time.time() - started_at))
    return result


def batch_process(
    urls: list[str],
    mode: str,
    min_quality: str,
    settings: Settings,
) -> None:
    success = 0
    failed: list[tuple[str, str]] = []
    for index, url in enumerate(urls, start=1):
        print(f"\n[批量下载] {index}/{len(urls)}")
        try:
            process_url(url, mode, min_quality, settings)
            success += 1
        except Exception as exc:
            failed.append((url, str(exc)))
            print(f"[失败] {exc}")
    print(f"\n批量结果：成功 {success}/{len(urls)}")
    for url, error in failed:
        print(f"  - {url[:70]}：{error}")


def ask_mode() -> str:
    while True:
        choice = input("下载类型 [1=高清视频，2=仅音频，默认1]：").strip()
        if choice in {"", "1", "video", "v"}:
            return "video"
        if choice in {"2", "audio", "a"}:
            return "audio"
        print("请输入 1 或 2。")


def ask_quality() -> str:
    while True:
        choice = input(
            "画质要求 [1=最高可用，2=至少1080P，3=至少4K，默认1]："
        ).strip()
        if choice in {"", "1", "best"}:
            return "best"
        if choice in {"2", "1080", "1080p"}:
            return "1080p"
        if choice in {"3", "4k", "2160p"}:
            return "4k"
        print("请输入 1、2 或 3。")


def ask_download_options() -> tuple[str, str]:
    mode = ask_mode()
    return mode, ask_quality() if mode == "video" else "best"


def interactive_mode(settings: Settings) -> None:
    print("进入交互模式（输入 q 退出，输入 batch 批量下载）\n")
    while True:
        try:
            source = input("请输入视频链接：").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n再见！")
            return
        if source.lower() == "q":
            print("再见！")
            return
        if source.lower() == "batch":
            mode, min_quality = ask_download_options()
            print("每行输入一个链接，输入空行结束：")
            urls = []
            while True:
                line = input().strip()
                if not line:
                    break
                urls.append(line)
            if urls:
                batch_process(urls, mode, min_quality, settings)
            continue
        if not source:
            continue
        try:
            mode, min_quality = ask_download_options()
            process_url(source, mode, min_quality, settings)
        except Exception as exc:
            print(f"\n[失败] {exc}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="下载最佳画质视频，或提取 MP3 音频",
    )
    parser.add_argument("source", nargs="?", help="在线视频链接")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--video", action="store_true", help="下载最佳画质视频（默认）")
    mode.add_argument("--audio", action="store_true", help="仅下载 MP3 音频")
    parser.add_argument("--batch", nargs="+", metavar="URL", help="批量下载")
    parser.add_argument(
        "--min-quality",
        choices=["best", "720p", "1080p", "4k"],
        default="best",
        help="最低画质；不满足时停止，默认 best",
    )
    parser.add_argument("--check", action="store_true", help="只检查运行环境")
    return parser


def main() -> None:
    configure_console()
    print_banner()
    args = build_parser().parse_args()
    settings = load_settings()
    if args.check:
        raise SystemExit(0 if check_environment(settings) else 1)
    selected_mode = "audio" if args.audio else "video"
    try:
        if args.batch:
            batch_process(args.batch, selected_mode, args.min_quality, settings)
        elif args.source:
            process_url(args.source, selected_mode, args.min_quality, settings)
        else:
            interactive_mode(settings)
    except KeyboardInterrupt:
        print("\n已中断。")
    except Exception as exc:
        print(f"\n[失败] {exc}")
        raise SystemExit(1) from exc
