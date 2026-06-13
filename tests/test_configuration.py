import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from video_downloader.adapters.ytdlp import build_network_args, format_error
from video_downloader.cli import check_environment
from video_downloader.config import load_settings
from video_downloader.core import download_media
from video_downloader.models import DownloadResult


class ConfigurationTests(unittest.TestCase):
    def test_platform_cookie_environment_variables_are_isolated(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            bili = base / "bili.txt"
            youtube = base / "youtube.txt"
            bili.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
            youtube.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
            settings = load_settings(
                {
                    "BILIBILI_COOKIES_FILE": str(bili),
                    "YOUTUBE_COOKIES_FILE": str(youtube),
                    "BILIBILI_COOKIE_BROWSER": "edge",
                },
                base,
            )
            bili_args = build_network_args("bilibili", settings)
            youtube_args = build_network_args("youtube", settings)
            self.assertIn(str(bili), bili_args)
            self.assertNotIn(str(youtube), bili_args)
            self.assertIn(str(youtube), youtube_args)
            self.assertNotIn(str(bili), youtube_args)
            self.assertNotIn("--cookies-from-browser", youtube_args)

    def test_legacy_cookie_variables_are_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            settings = load_settings(
                {
                    "YTDLP_COOKIES_FILE": "legacy.txt",
                    "YTDLP_COOKIE_BROWSER": "chrome",
                },
                base,
            )
            self.assertEqual(
                settings.bilibili_cookie_file,
                base / "space.bilibili.com_cookies.txt",
            )
            self.assertIsNone(settings.youtube_cookie_file)
            self.assertEqual(settings.bilibili_cookie_browser, "")

    def test_relative_paths_are_resolved_from_project_root(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            settings = load_settings(
                {
                    "BILIBILI_COOKIES_FILE": "private/bili.txt",
                    "DOWNLOAD_DIR": "media",
                },
                base,
            )
            self.assertEqual(
                settings.bilibili_cookie_file,
                base / "private/bili.txt",
            )
            self.assertEqual(settings.download_dir, base / "media")

    def test_check_does_not_print_cookie_values(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            cookie = base / "bili.txt"
            secret = "VERY_SECRET_COOKIE_VALUE"
            cookie.write_text(
                "# Netscape HTTP Cookie File\n"
                f".bilibili.com\tTRUE\t/\tTRUE\t2147483647\tSESSDATA\t{secret}\n",
                encoding="utf-8",
            )
            settings = load_settings(
                {"BILIBILI_COOKIES_FILE": str(cookie)},
                base,
            )
            output = io.StringIO()
            with redirect_stdout(output):
                check_environment(settings)
            text = output.getvalue()
            self.assertNotIn(secret, text)
            self.assertIn("B站登录态：已登录", text)
            self.assertIn("Netscape", text)

    def test_download_result_exposes_normalized_fields(self):
        result = DownloadResult(
            path=Path("video.mp4"),
            platform="youtube",
            mode="video",
            width=1920,
            height=1080,
            quality="1080P",
            video_codec="avc1",
            audio_codec="opus",
        )
        self.assertEqual(result.resolution, "1920x1080")
        self.assertEqual(result.platform, "youtube")
        self.assertEqual(result.quality, "1080P")

    def test_youtube_login_error_names_platform_specific_variable(self):
        message = format_error(
            "youtube",
            "ERROR: Sign in to confirm you are not a bot",
        )
        self.assertIn("YOUTUBE_COOKIES_FILE", message)
        self.assertNotIn("YTDLP_COOKIES_FILE", message)

    def test_bilibili_browser_cookie_routes_directly_to_ytdlp(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            settings = load_settings(
                {"BILIBILI_COOKIE_BROWSER": "edge"},
                base,
            )
            expected = DownloadResult(
                path=base / "video.mp4",
                platform="bilibili",
                mode="video",
            )
            with patch(
                "video_downloader.core.download_with_ytdlp",
                return_value=expected,
            ) as mocked:
                result = download_media(
                    "https://www.bilibili.com/video/BV1example",
                    settings=settings,
                )
            self.assertEqual(result, expected)
            mocked.assert_called_once()


if __name__ == "__main__":
    unittest.main()
