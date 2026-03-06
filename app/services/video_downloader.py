from __future__ import annotations

import logging
from pathlib import Path

import yt_dlp

logger = logging.getLogger(__name__)


class VideoDownloader:
    def download_douyin_video(self, url: str, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        target_template = str(output_dir / "%(id)s.%(ext)s")
        options = {
            "outtmpl": target_template,
            "quiet": True,
            "noplaylist": True,
            "format": "mp4/best",
        }
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=True)
                downloaded = Path(ydl.prepare_filename(info))
                return downloaded
        except Exception as exc:  # pragma: no cover
            logger.warning("Douyin download failed: %s", exc)
            raise RuntimeError("Douyin download failed; use raw_text or uploaded_video fallback.") from exc
