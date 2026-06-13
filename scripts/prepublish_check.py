"""Fail when release candidates contain credentials or downloaded media."""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXCLUDED_DIRS = {
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "downloads",
    "venv",
}
IGNORED_LOCAL_PATHS = {
    Path("space.bilibili.com_cookies.txt"),
}
MEDIA_SUFFIXES = {
    ".avi",
    ".flac",
    ".flv",
    ".m4a",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".opus",
    ".wav",
    ".webm",
}
COOKIE_NAME = "SESS" + "DATA"
COOKIE_PATTERN = re.compile(
    rf"(?m)^[^\r\n\t]+\t(?:TRUE|FALSE)\t[^\t]+\t(?:TRUE|FALSE)"
    rf"\t\d+\t{COOKIE_NAME}\t([^\r\n\t]+)$",
    re.IGNORECASE,
)
PRIVATE_KEY_PATTERN = re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY")
PROXY_CREDENTIAL_PATTERN = re.compile(r"://[^/\s:@]+:[^/\s@]+@")
TOKEN_PATTERNS = [
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
]
SAFE_PLACEHOLDERS = {"REPLACE_ME", "test-value", "example", "placeholder"}


def candidate_files():
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if path.relative_to(ROOT) in IGNORED_LOCAL_PATHS:
            continue
        yield path


def tracked_paths() -> set[Path]:
    if not (ROOT / ".git").exists():
        return set()
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    return {
        Path(value.decode("utf-8"))
        for value in result.stdout.split(b"\0")
        if value
    }


def main() -> int:
    failures: list[str] = []
    tracked = tracked_paths()
    if Path("space.bilibili.com_cookies.txt") in tracked:
        failures.append("真实 Cookie 文件已被 Git 跟踪")
    if any(path.parts and path.parts[0] == "downloads" for path in tracked):
        failures.append("downloads 目录中的文件已被 Git 跟踪")

    for path in candidate_files():
        relative = path.relative_to(ROOT)
        if path.suffix.lower() in MEDIA_SUFFIXES:
            failures.append(f"发现媒体文件：{relative}")
            continue
        if path.stat().st_size > 10 * 1024 * 1024:
            failures.append(f"发现超过 10MB 的文件：{relative}")
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if PRIVATE_KEY_PATTERN.search(text):
            failures.append(f"发现私钥：{relative}")
        if PROXY_CREDENTIAL_PATTERN.search(text):
            failures.append(f"发现代理账号密码：{relative}")
        for pattern in TOKEN_PATTERNS:
            if pattern.search(text):
                failures.append(f"发现疑似访问令牌：{relative}")
        for match in COOKIE_PATTERN.finditer(text):
            if match.group(1) not in SAFE_PLACEHOLDERS:
                failures.append(f"发现疑似 B站登录 Cookie：{relative}")

    if failures:
        print("发布前检查失败：")
        for failure in sorted(set(failures)):
            print(f"  - {failure}")
        return 1
    print("发布前检查通过：未发现凭据、下载媒体或超大文件。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
