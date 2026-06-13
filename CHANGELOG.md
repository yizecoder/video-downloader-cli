# Changelog

All notable changes are documented in this file.

## [2.0.0] - 2026-06-14

### Added

- Highest-quality video and optional MP3 downloads.
- Bilibili, YouTube, Douyin, Xiaohongshu, and generic yt-dlp routing.
- Strict `720p`, `1080p`, and `4k` minimum-quality checks.
- Platform-specific Cookie configuration and structured download results.
- Windows launcher, environment diagnostics, tests, Ruff, and Windows CI.

### Removed

- Local Whisper transcription, AI summarization, and Markdown export.
- Shared Cookie environment variables that could leak credentials across sites.
