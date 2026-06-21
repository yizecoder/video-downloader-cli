# Changelog

All notable changes are documented in this file.

## [Unreleased]

### Added

- Support loading URLs from a UTF-8 text file with comments, blank lines, and
  ordered deduplication.
- Remove Bilibili video tracking parameters while preserving the part number.

### Fixed

- Restore authenticated YouTube downloads by installing the yt-dlp EJS
  component and automatically selecting Deno or Node.js for JS challenges.
- Report expired YouTube Cookies and age-verification failures separately
  instead of misclassifying them as unavailable video quality.
- Ignore platform-specific exported Cookie files to prevent accidental commits.
- Detect DRM-protected Bilibili course streams from their MP4 headers and stop
  before downloading the complete encrypted media files.

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
