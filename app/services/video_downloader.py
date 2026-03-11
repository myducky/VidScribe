from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yt_dlp

from app.core.config import Settings
from app.core.errors import RemoteVideoDownloadError

logger = logging.getLogger(__name__)


@dataclass
class DouyinProbeResult:
    input_url: str
    normalized_url: str
    downloadable: bool
    reason_code: str
    detail: str
    resolved_video_id: str | None = None


@dataclass
class VideoProbeResult:
    platform: str
    input_url: str
    normalized_url: str
    downloadable: bool
    reason_code: str
    detail: str
    resolved_video_id: str | None = None


class VideoDownloader:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings

    def probe_douyin_url(self, url: str) -> DouyinProbeResult:
        normalized_url, resolved_video_id = self.normalize_douyin_url(url)
        options = self._build_options(download=False)
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(normalized_url, download=False)
        except Exception as exc:  # pragma: no cover
            resolved_video_id = resolved_video_id or self._extract_video_id_from_message(str(exc))
            if resolved_video_id:
                normalized_url = self._video_url_for_id(resolved_video_id)
            reason_code = self._classify_probe_error(str(exc))
            return DouyinProbeResult(
                input_url=url,
                normalized_url=normalized_url,
                downloadable=False,
                reason_code=reason_code,
                detail=self._build_probe_detail(reason_code, str(exc)),
                resolved_video_id=resolved_video_id,
            )

        info_video_id = str(info.get("id")) if info.get("id") else resolved_video_id
        result_url = self._video_url_for_id(info_video_id) if info_video_id else (info.get("webpage_url") or normalized_url)
        return DouyinProbeResult(
            input_url=url,
            normalized_url=result_url,
            downloadable=True,
            reason_code="downloadable",
            detail="Douyin video metadata resolved successfully.",
            resolved_video_id=info_video_id,
        )

    def probe_video_url(self, url: str) -> VideoProbeResult:
        platform = self.detect_platform(url)
        if platform == "douyin":
            result = self.probe_douyin_url(url)
            return VideoProbeResult(
                platform=platform,
                input_url=result.input_url,
                normalized_url=result.normalized_url,
                downloadable=result.downloadable,
                reason_code=result.reason_code,
                detail=result.detail,
                resolved_video_id=result.resolved_video_id,
            )

        if platform == "bilibili":
            return self._probe_bilibili_url(url)

        return VideoProbeResult(
            platform="unknown",
            input_url=url,
            normalized_url=url,
            downloadable=False,
            reason_code="unsupported_platform",
            detail="Only Bilibili and Douyin links are currently supported. Prefer public Bilibili video links for the highest success rate.",
            resolved_video_id=None,
        )

    def download_douyin_video(self, url: str, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        options = self._build_options(download=True, output_dir=output_dir)
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(self.normalize_douyin_url(url)[0], download=True)
                downloaded = Path(ydl.prepare_filename(info))
                return downloaded
        except Exception as exc:  # pragma: no cover
            logger.warning("Douyin download failed: %s", exc)
            raise RemoteVideoDownloadError("Douyin download failed; use raw_text or uploaded_video fallback.") from exc

    def download_bilibili_video(self, url: str, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        options = self._build_options(download=True, output_dir=output_dir)
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=True)
                downloaded = Path(ydl.prepare_filename(info))
                return downloaded
        except Exception as exc:  # pragma: no cover
            logger.warning("Bilibili download failed: %s", exc)
            raise RemoteVideoDownloadError("Bilibili download failed; use raw_text or uploaded_video fallback.") from exc

    @staticmethod
    def normalize_douyin_url(url: str) -> tuple[str, str | None]:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        modal_id = query.get("modal_id", [None])[0]
        if modal_id and re.fullmatch(r"\d+", modal_id):
            return f"https://www.douyin.com/video/{modal_id}", modal_id

        match = re.search(r"/video/(\d+)", parsed.path)
        if match:
            return url, match.group(1)
        return url, None

    @staticmethod
    def detect_platform(url: str) -> str:
        host = urlparse(url).netloc.lower()
        if "bilibili.com" in host or "b23.tv" in host:
            return "bilibili"
        if "douyin.com" in host:
            return "douyin"
        return "unknown"

    def _build_options(self, *, download: bool, output_dir: Path | None = None) -> dict:
        options = {
            "quiet": True,
            "noplaylist": True,
        }
        if self.settings:
            options["socket_timeout"] = self.settings.video_download_socket_timeout_sec
            options["retries"] = self.settings.video_download_retries
            options["fragment_retries"] = self.settings.video_download_retries
            if self.settings.video_download_force_ipv4:
                options["source_address"] = "0.0.0.0"
        if download:
            if output_dir is None:
                raise ValueError("output_dir is required when download=True")
            options["format"] = "bv*+ba/b"
            options["merge_output_format"] = "mp4"
            options["outtmpl"] = str(output_dir / "%(id)s.%(ext)s")
        else:
            options["skip_download"] = True

        if self.settings and self.settings.douyin_cookie_file:
            options["cookiefile"] = self.settings.douyin_cookie_file
        elif self.settings and self.settings.douyin_cookies_from_browser:
            options["cookiesfrombrowser"] = (self.settings.douyin_cookies_from_browser,)
        return options

    def _probe_bilibili_url(self, url: str) -> VideoProbeResult:
        options = self._build_options(download=False)
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as exc:  # pragma: no cover
            reason_code = self._classify_probe_error(str(exc))
            return VideoProbeResult(
                platform="bilibili",
                input_url=url,
                normalized_url=url,
                downloadable=False,
                reason_code=reason_code,
                detail=self._build_bilibili_probe_detail(reason_code, str(exc)),
                resolved_video_id=self._extract_bilibili_id_from_message(str(exc)),
            )

        resolved_video_id = str(info.get("id")) if info.get("id") else None
        normalized_url = str(info.get("webpage_url") or url)
        return VideoProbeResult(
            platform="bilibili",
            input_url=url,
            normalized_url=normalized_url,
            downloadable=True,
            reason_code="downloadable",
            detail="Bilibili video metadata resolved successfully.",
            resolved_video_id=resolved_video_id,
        )

    @staticmethod
    def _classify_probe_error(message: str) -> str:
        lowered = message.lower()
        if "fresh cookies" in lowered or "cookies" in lowered:
            return "cookies_required"
        if "unsupported url" in lowered:
            return "unsupported_url"
        if (
            "failed to resolve" in lowered
            or "nodename nor servname provided" in lowered
            or "read timed out" in lowered
            or "ssl:" in lowered
            or "unexpected eof" in lowered
            or "connection reset" in lowered
        ):
            return "network_error"
        return "download_failed"

    @staticmethod
    def _build_probe_detail(reason_code: str, message: str) -> str:
        if reason_code == "cookies_required":
            return "Douyin recognized the video page, but fresh browser cookies are required before download can proceed."
        if reason_code == "unsupported_url":
            return "This Douyin URL shape is not directly supported for download. Try a standard /video/{id} link or provide fallback input."
        if reason_code == "network_error":
            return "The downloader could not reach Douyin. Check network access and retry."
        return f"Douyin probe failed: {message}"

    @staticmethod
    def _build_bilibili_probe_detail(reason_code: str, message: str) -> str:
        if reason_code == "cookies_required":
            return "Bilibili recognized the video page, but cookies are required for this video or quality level."
        if reason_code == "unsupported_url":
            return "This Bilibili URL shape is not directly supported. Prefer a standard public /video/BV... link."
        if reason_code == "network_error":
            return "The downloader could not reach Bilibili. Check network access and retry."
        return f"Bilibili probe failed: {message}"

    @staticmethod
    def _extract_video_id_from_message(message: str) -> str | None:
        match = re.search(r"\[Douyin\]\s+(\d+)", message)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def _video_url_for_id(video_id: str) -> str:
        return f"https://www.douyin.com/video/{video_id}"

    @staticmethod
    def _extract_bilibili_id_from_message(message: str) -> str | None:
        match = re.search(r"(BV[0-9A-Za-z]+)", message)
        if match:
            return match.group(1)
        return None
