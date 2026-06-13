"""Shared data models."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DownloadResult:
    """A normalized result returned by every platform adapter."""

    path: Path
    platform: str
    mode: str
    width: int = 0
    height: int = 0
    quality: str = ""
    video_codec: str = ""
    audio_codec: str = ""

    @property
    def resolution(self) -> str:
        if self.width and self.height:
            return f"{self.width}x{self.height}"
        return ""
