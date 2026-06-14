import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_downloader.adapters.bilibili import (
    BILIBILI_QUALITY_LABELS,
    extract_bilibili_bvid,
)
from video_downloader.adapters.ytdlp import (
    build_network_args,
    build_video_format,
    format_error,
    has_mp4_drm_markers,
    reject_bilibili_course_drm,
)
from video_downloader.config import (
    DEFAULT_BILIBILI_COOKIE_FILE,
    Settings,
)
from video_downloader.core import download_media
from video_downloader.models import DownloadResult
from video_downloader.utils import (
    detect_platform,
    finalize_filename,
    format_resolution_label,
    inspect_cookie_file,
    is_http_url,
    normalize_media_url,
    normalize_quality,
    sanitize_filename,
    validate_minimum_quality,
)


class CoreTests(unittest.TestCase):
    def make_settings(
        self,
        directory: str,
        *,
        bilibili_cookie: str = "missing.txt",
        youtube_cookie: Path | None = None,
        browser: str = "",
    ) -> Settings:
        base = Path(directory)
        return Settings(
            base_dir=base,
            download_dir=base / "downloads",
            proxy="",
            bilibili_cookie_file=base / bilibili_cookie,
            youtube_cookie_file=youtube_cookie,
            bilibili_cookie_browser=browser,
        )

    def test_detect_platform(self):
        cases = {
            "https://www.bilibili.com/video/BV1": "bilibili",
            "https://youtu.be/example": "youtube",
            "https://xhslink.com/example": "xiaohongshu",
            "https://v.douyin.com/example": "douyin",
            "https://example.com/video": "unknown",
        }
        for url, expected in cases.items():
            with self.subTest(url=url):
                self.assertEqual(detect_platform(url), expected)

    def test_extract_bilibili_bvid(self):
        self.assertEqual(
            extract_bilibili_bvid("https://www.bilibili.com/video/BV1fKXCBQEeq?p=1"),
            "BV1fKXCBQEeq",
        )

    def test_bilibili_quality_labels(self):
        self.assertEqual(BILIBILI_QUALITY_LABELS[64], "720P")
        self.assertEqual(BILIBILI_QUALITY_LABELS[80], "1080P")

    def test_url_validation(self):
        self.assertTrue(is_http_url("https://example.com/video"))
        self.assertFalse(is_http_url("local-video.mp4"))

    def test_douyin_jingxuan_url_is_normalized(self):
        self.assertEqual(
            normalize_media_url(
                "https://www.douyin.com/jingxuan?modal_id=7649636894703095081"
            ),
            "https://www.douyin.com/video/7649636894703095081",
        )

    def test_filename_sanitizing(self):
        self.assertEqual(sanitize_filename('a:b/c*?'), "a_b_c__")

    def test_ytdlp_file_is_renamed_after_download(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "video-id.mp4"
            source.write_bytes(b"media")
            output = finalize_filename(
                source,
                {
                    "id": "video-id",
                    "title": "中文:标题",
                    "width": 2560,
                    "height": 1440,
                },
            )
            self.assertEqual(output.name, "中文_标题_video-id_1440P.mp4")
            self.assertTrue(output.is_file())
            self.assertFalse(source.exists())

    def test_audio_filename_does_not_include_video_quality(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "video-id.mp3"
            source.write_bytes(b"audio")
            output = finalize_filename(
                source,
                {
                    "id": "video-id",
                    "title": "Audio",
                    "width": 3840,
                    "height": 2160,
                },
                mode="audio",
            )
            self.assertEqual(output.name, "Audio_video-id.mp3")

    def test_resolution_labels_support_landscape_and_portrait(self):
        self.assertEqual(
            format_resolution_label({"width": 2560, "height": 1440}),
            "1440P",
        )
        self.assertEqual(
            format_resolution_label({"width": 1080, "height": 1920}),
            "1080P",
        )
        self.assertEqual(
            format_resolution_label({"width": 3840, "height": 2160}),
            "4K",
        )

    def test_strict_quality_rejects_lower_resolution_before_download(self):
        with self.assertRaisesRegex(RuntimeError, "最高实际可下载画质为 720P"):
            validate_minimum_quality(
                {"width": 1280, "height": 720, "resolution": "1280x720"},
                "1080p",
            )
        validate_minimum_quality(
            {"width": 2560, "height": 1440, "resolution": "2560x1440"},
            "1080p",
        )

    def test_requested_format_error_is_actionable(self):
        message = format_error(
            "douyin",
            "ERROR: Requested format is not available",
        )
        self.assertIn("最高可用", message)

    def test_quality_normalization(self):
        self.assertEqual(normalize_quality("1080"), "1080p")
        self.assertEqual(normalize_quality("2160p"), "4k")
        with self.assertRaises(ValueError):
            normalize_quality("8k")

    def test_youtube_highest_quality_format(self):
        self.assertEqual(
            build_video_format("best"),
            "bestvideo*+bestaudio/best",
        )
        strict = build_video_format("1080p")
        self.assertIn("height>=1080", strict)
        self.assertNotIn("bestvideo*+bestaudio/best", strict)

    def test_mp4_drm_markers_require_encryption_boxes(self):
        encrypted = b"ftyp....moov....pssh....sinf....tenc....encv"
        self.assertTrue(has_mp4_drm_markers(encrypted))
        self.assertFalse(has_mp4_drm_markers(b"ftyp....moov....sinf"))
        self.assertFalse(has_mp4_drm_markers(b"ftyp....moov....pssh....sinf"))

    @patch("video_downloader.adapters.ytdlp.requests.Session")
    def test_bilibili_course_drm_stops_before_download(self, mocked_session):
        response = mocked_session.return_value.get.return_value
        response.__enter__.return_value = response
        response.__exit__.return_value = None
        response.raw.read.return_value = (
            b"ftyp....moov....pssh....sinf....tenc....encv"
        )
        metadata = {
            "extractor_key": "BilibiliCheese",
            "requested_formats": [{"url": "https://media.example/video.m4s"}],
        }

        with self.assertRaisesRegex(RuntimeError, "DRM 加密媒体流"):
            reject_bilibili_course_drm(
                "https://www.bilibili.com/cheese/play/ep1",
                metadata,
            )

        response.raw.read.assert_called_once()

    @patch("video_downloader.adapters.ytdlp.requests.Session")
    def test_regular_bilibili_video_skips_drm_probe(self, mocked_session):
        reject_bilibili_course_drm(
            "https://www.bilibili.com/video/BV1example",
            {"extractor_key": "Bilibili"},
        )
        mocked_session.assert_not_called()

    @patch("video_downloader.adapters.ytdlp.shutil.which")
    def test_youtube_uses_installed_node_runtime(self, mocked_which):
        mocked_which.side_effect = lambda name: "C:/node.exe" if name == "node" else None
        with tempfile.TemporaryDirectory() as directory:
            args = build_network_args(
                "youtube",
                self.make_settings(directory),
            )
        self.assertIn("--js-runtimes", args)
        self.assertEqual(args[args.index("--js-runtimes") + 1], "node")

    def test_cookie_login_detection(self):
        content = (
            "# Netscape HTTP Cookie File\n"
            ".bilibili.com\tTRUE\t/\tTRUE\t2147483647\tSESSDATA\ttest-value\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            encoding="utf-8",
            delete=False,
        ) as cookie_file:
            cookie_file.write(content)
            cookie_path = cookie_file.name
        try:
            status = inspect_cookie_file(Path(cookie_path))
            self.assertTrue(status.netscape_format)
            self.assertTrue(status.has_sessdata)
        finally:
            Path(cookie_path).unlink(missing_ok=True)

    def test_default_bilibili_cookie_filename(self):
        self.assertEqual(
            DEFAULT_BILIBILI_COOKIE_FILE.name,
            "space.bilibili.com_cookies.txt",
        )

    def test_bilibili_disables_inherited_proxy(self):
        with tempfile.TemporaryDirectory() as directory:
            args = build_network_args(
                "bilibili",
                self.make_settings(directory),
            )
            self.assertIn("--proxy", args)
            self.assertEqual(args[args.index("--proxy") + 1], "")

    def test_default_bilibili_cookie_is_not_used_for_youtube(self):
        with tempfile.TemporaryDirectory() as directory:
            args = build_network_args(
                "youtube",
                self.make_settings(directory),
            )
            self.assertNotIn("--cookies", args)

    def test_browser_cookie_is_not_used_for_youtube(self):
        with tempfile.TemporaryDirectory() as directory:
            args = build_network_args(
                "youtube",
                self.make_settings(directory, browser="chrome"),
            )
            self.assertNotIn("--cookies-from-browser", args)

    def test_browser_cookie_can_still_be_used_for_bilibili(self):
        with tempfile.TemporaryDirectory() as directory:
            args = build_network_args(
                "bilibili",
                self.make_settings(directory, browser="edge"),
            )
            self.assertIn("--cookies-from-browser", args)
            self.assertIn("edge", args)

    def test_youtube_unavailable_error_is_actionable(self):
        message = format_error(
            "youtube",
            "ERROR: [youtube] abc: Video unavailable",
        )
        self.assertIn("视频 ID", message)

    def test_rotated_youtube_cookie_error_is_actionable(self):
        message = format_error(
            "youtube",
            "WARNING: The provided YouTube account cookies are no longer valid.",
        )
        self.assertIn("无痕窗口", message)
        self.assertIn("robots.txt", message)

    def test_youtube_js_challenge_error_is_actionable(self):
        message = format_error(
            "youtube",
            "WARNING: n challenge solving failed",
        )
        self.assertIn("Node.js 22+", message)
        self.assertIn("yt-dlp[default]", message)

    def test_dpapi_error_has_actionable_message(self):
        message = format_error(
            "bilibili",
            "ERROR: Failed to decrypt with DPAPI.",
        )
        self.assertIn("Cookie 文件", message)

    def test_invalid_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            download_media("https://example.com/video", mode="invalid")

    @patch("video_downloader.core.download_with_ytdlp")
    def test_unknown_platform_uses_ytdlp(self, mocked_download):
        mocked_download.return_value = DownloadResult(
            path=Path("output.mp4"),
            platform="unknown",
            mode="video",
        )
        output = download_media("https://example.com/video", mode="video")
        self.assertEqual(output.path, Path("output.mp4"))
        mocked_download.assert_called_once()


if __name__ == "__main__":
    unittest.main()
