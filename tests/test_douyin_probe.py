from app.core.config import Settings
from app.schemas.responses import DouyinProbeResponse, VideoProbeResponse
from app.services.job_service import JobService
from app.services.video_downloader import VideoDownloader


def test_probe_douyin_endpoint_returns_structured_result(client, monkeypatch):
    def fake_probe(_self: JobService, douyin_url: str) -> DouyinProbeResponse:
        return DouyinProbeResponse(
            input_url=douyin_url,
            normalized_url="https://www.douyin.com/video/7602192686975601972",
            downloadable=False,
            reason_code="cookies_required",
            detail="Douyin recognized the video page, but fresh browser cookies are required before download can proceed.",
            resolved_video_id="7602192686975601972",
        )

    monkeypatch.setattr(JobService, "probe_douyin_url", fake_probe)

    response = client.post(
        "/v1/probe-douyin",
        json={"douyin_url": "https://www.douyin.com/jingxuan?modal_id=7602192686975601972"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "input_url": "https://www.douyin.com/jingxuan?modal_id=7602192686975601972",
        "normalized_url": "https://www.douyin.com/video/7602192686975601972",
        "downloadable": False,
        "reason_code": "cookies_required",
        "detail": "Douyin recognized the video page, but fresh browser cookies are required before download can proceed.",
        "resolved_video_id": "7602192686975601972",
    }


def test_probe_video_url_endpoint_returns_bilibili_result(client, monkeypatch):
    def fake_probe(_self: JobService, video_url: str) -> VideoProbeResponse:
        return VideoProbeResponse(
            platform="bilibili",
            input_url=video_url,
            normalized_url="https://www.bilibili.com/video/BV1S5PrzZEzQ",
            downloadable=True,
            reason_code="downloadable",
            detail="Bilibili video metadata resolved successfully.",
            resolved_video_id="BV1S5PrzZEzQ",
        )

    monkeypatch.setattr(JobService, "probe_video_url", fake_probe)

    response = client.post(
        "/v1/probe-video-url",
        json={"video_url": "https://www.bilibili.com/video/BV1S5PrzZEzQ"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "platform": "bilibili",
        "input_url": "https://www.bilibili.com/video/BV1S5PrzZEzQ",
        "normalized_url": "https://www.bilibili.com/video/BV1S5PrzZEzQ",
        "downloadable": True,
        "reason_code": "downloadable",
        "detail": "Bilibili video metadata resolved successfully.",
        "resolved_video_id": "BV1S5PrzZEzQ",
    }


def test_video_downloader_probe_normalizes_modal_id_and_classifies_cookie_requirement(monkeypatch):
    class FakeYoutubeDL:
        def __init__(self, _options):
            self.seen_url: str | None = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, url: str, download: bool):
            self.seen_url = url
            assert download is False
            raise RuntimeError("Fresh cookies (not necessarily logged in) are needed")

    fake_ydl = FakeYoutubeDL({})
    monkeypatch.setattr("app.services.video_downloader.yt_dlp.YoutubeDL", lambda _options: fake_ydl)

    result = VideoDownloader().probe_douyin_url(
        "https://www.douyin.com/jingxuan?modal_id=7602192686975601972"
    )

    assert fake_ydl.seen_url == "https://www.douyin.com/video/7602192686975601972"
    assert result.input_url == "https://www.douyin.com/jingxuan?modal_id=7602192686975601972"
    assert result.normalized_url == "https://www.douyin.com/video/7602192686975601972"
    assert result.downloadable is False
    assert result.reason_code == "cookies_required"
    assert result.resolved_video_id == "7602192686975601972"


def test_video_downloader_probe_returns_downloadable_bilibili_result(monkeypatch):
    class FakeYoutubeDL:
        def __init__(self, _options):
            self.seen_url: str | None = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, url: str, download: bool):
            self.seen_url = url
            assert download is False
            return {"id": "BV1S5PrzZEzQ", "webpage_url": url, "title": "demo"}

    fake_ydl = FakeYoutubeDL({})
    monkeypatch.setattr("app.services.video_downloader.yt_dlp.YoutubeDL", lambda _options: fake_ydl)

    result = VideoDownloader().probe_video_url("https://www.bilibili.com/video/BV1S5PrzZEzQ")

    assert fake_ydl.seen_url == "https://www.bilibili.com/video/BV1S5PrzZEzQ"
    assert result.platform == "bilibili"
    assert result.downloadable is True
    assert result.reason_code == "downloadable"
    assert result.detail == "Bilibili video metadata resolved successfully."
    assert result.resolved_video_id == "BV1S5PrzZEzQ"
    assert result.normalized_url == "https://www.bilibili.com/video/BV1S5PrzZEzQ"


def test_video_downloader_probe_normalizes_share_link_from_error_message(monkeypatch):
    class FakeYoutubeDL:
        def __init__(self, _options):
            self.seen_url: str | None = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, url: str, download: bool):
            self.seen_url = url
            assert download is False
            raise RuntimeError("[Douyin] 7613293357074304307: Fresh cookies (not necessarily logged in) are needed")

    fake_ydl = FakeYoutubeDL({})
    monkeypatch.setattr("app.services.video_downloader.yt_dlp.YoutubeDL", lambda _options: fake_ydl)

    result = VideoDownloader().probe_video_url("https://v.douyin.com/3aoA22_an4o/")

    assert fake_ydl.seen_url == "https://v.douyin.com/3aoA22_an4o/"
    assert result.platform == "douyin"
    assert result.normalized_url == "https://www.douyin.com/video/7613293357074304307"
    assert result.resolved_video_id == "7613293357074304307"
    assert result.reason_code == "cookies_required"


def test_video_downloader_probe_returns_unsupported_platform():
    result = VideoDownloader().probe_video_url("https://example.com/video/123")

    assert result.platform == "unknown"
    assert result.downloadable is False
    assert result.reason_code == "unsupported_platform"


def test_video_downloader_includes_cookie_file_option():
    settings = Settings(
        DOUYIN_COOKIE_FILE="/tmp/douyin-cookies.txt",
        DOUYIN_COOKIES_FROM_BROWSER="chrome",
    )

    options = VideoDownloader(settings)._build_options(download=False)

    assert options["cookiefile"] == "/tmp/douyin-cookies.txt"
    assert "cookiesfrombrowser" not in options


def test_video_downloader_includes_retry_timeout_and_ipv4_options():
    settings = Settings(
        VIDEO_DOWNLOAD_SOCKET_TIMEOUT_SEC=35,
        VIDEO_DOWNLOAD_RETRIES=4,
        VIDEO_DOWNLOAD_FORCE_IPV4=True,
    )

    options = VideoDownloader(settings)._build_options(download=False)

    assert options["socket_timeout"] == 35
    assert options["retries"] == 4
    assert options["fragment_retries"] == 4
    assert options["source_address"] == "0.0.0.0"


def test_video_downloader_uses_merged_audio_video_format_for_download(tmp_path):
    options = VideoDownloader()._build_options(download=True, output_dir=tmp_path)

    assert options["format"] == "bv*+ba/b"
    assert options["merge_output_format"] == "mp4"
    assert options["outtmpl"] == str(tmp_path / "%(id)s.%(ext)s")


def test_video_downloader_includes_browser_cookie_option():
    settings = Settings(DOUYIN_COOKIES_FROM_BROWSER="chrome")

    options = VideoDownloader(settings)._build_options(download=False)

    assert options["cookiesfrombrowser"] == ("chrome",)
    assert "cookiefile" not in options


def test_video_downloader_classifies_ssl_and_timeout_failures_as_network_errors():
    assert VideoDownloader._classify_probe_error("Read timed out while downloading media") == "network_error"
    assert VideoDownloader._classify_probe_error("SSL: UNEXPECTED_EOF_WHILE_READING") == "network_error"


def test_download_douyin_video_uses_normalized_video_url(monkeypatch, tmp_path):
    captured_options: dict = {}

    class FakeYoutubeDL:
        def __init__(self, options):
            captured_options.update(options)
            self.seen_url: str | None = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, url: str, download: bool):
            self.seen_url = url
            assert download is True
            return {"id": "7602192686975601972", "ext": "mp4"}

        def prepare_filename(self, _info):
            return str(tmp_path / "7602192686975601972.mp4")

    fake_ydl: FakeYoutubeDL | None = None

    def fake_factory(options):
        nonlocal fake_ydl
        fake_ydl = FakeYoutubeDL(options)
        return fake_ydl

    monkeypatch.setattr("app.services.video_downloader.yt_dlp.YoutubeDL", fake_factory)

    downloaded = VideoDownloader().download_douyin_video(
        "https://www.douyin.com/jingxuan?modal_id=7602192686975601972",
        tmp_path,
    )

    assert captured_options["format"] == "bv*+ba/b"
    assert captured_options["merge_output_format"] == "mp4"
    assert fake_ydl is not None
    assert fake_ydl.seen_url == "https://www.douyin.com/video/7602192686975601972"
    assert downloaded.name == "7602192686975601972.mp4"
