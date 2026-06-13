"""Video Downloader CLI package."""

from .core import download_media
from .models import DownloadResult

__all__ = ["DownloadResult", "download_media"]
