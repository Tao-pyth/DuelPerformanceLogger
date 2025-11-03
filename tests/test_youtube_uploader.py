from __future__ import annotations

from pathlib import Path

import pytest

google_errors = pytest.importorskip("googleapiclient.errors")
pytest.importorskip("googleapiclient.discovery")

from app.function.core import youtube_uploader

HttpError = google_errors.HttpError


class _DummyResponse:
    status = 403
    reason = "quotaExceeded"


class _DummyRequest:
    def __init__(self, response: dict[str, object] | None, error: Exception | None) -> None:
        self._response = response
        self._error = error

    def execute(self) -> dict[str, object]:
        if self._error is not None:
            raise self._error
        return self._response or {}


class _DummyVideos:
    def __init__(
        self,
        response: dict[str, object] | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self._response = response
        self._error = error
        self.last_kwargs: dict[str, object] | None = None

    def insert(self, **kwargs: object) -> _DummyRequest:  # noqa: D401 - mock helper
        self.last_kwargs = kwargs
        return _DummyRequest(self._response, self._error)


class _DummyService:
    def __init__(self, videos: _DummyVideos) -> None:
        self._videos = videos

    def videos(self) -> _DummyVideos:  # noqa: D401 - mock helper
        return self._videos


def _patch_media_file_upload(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, object]]:
    calls: list[tuple[str, object]] = []

    def _fake_media(path: str, *, mimetype: str, resumable: bool) -> tuple[str, str, bool]:
        calls.append((path, mimetype, resumable))
        return (path, mimetype, resumable)

    monkeypatch.setattr(youtube_uploader, "MediaFileUpload", _fake_media)
    return calls


def test_upload_video_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    video_path = uploads / "match.mp4"
    video_path.write_bytes(b"video")

    calls = _patch_media_file_upload(monkeypatch)
    videos = _DummyVideos({"id": "video123"})

    def _factory(api_key: str) -> _DummyService:
        assert api_key == "API_KEY"
        return _DummyService(videos)

    uploader = youtube_uploader.YouTubeUploader(
        api_key="API_KEY",
        upload_dir=uploads,
        default_privacy="unlisted",
        log_root=tmp_path / "logs",
        service_factory=_factory,
    )

    result = uploader.upload_video(video_path, "Title", "Description")

    assert result.video_id == "video123"
    assert result.url == "https://www.youtube.com/watch?v=video123"
    assert result.log_path.exists()
    log_content = result.log_path.read_text(encoding="utf-8")
    assert "Upload start" in log_content
    assert "Upload completed" in log_content

    assert videos.last_kwargs is not None
    assert videos.last_kwargs["part"] == "snippet,status"
    body = videos.last_kwargs["body"]
    assert isinstance(body, dict)
    assert body["snippet"]["title"] == "Title"
    assert body["status"]["privacyStatus"] == "unlisted"

    assert calls == [(str(video_path), "video/*", False)]


def test_upload_video_missing_file(tmp_path: Path) -> None:
    uploads = tmp_path / "uploads"
    uploads.mkdir()

    uploader = youtube_uploader.YouTubeUploader(
        api_key="API_KEY",
        upload_dir=uploads,
        log_root=tmp_path / "logs",
        service_factory=lambda _: _DummyService(_DummyVideos({"id": "noop"})),
    )

    with pytest.raises(FileNotFoundError):
        uploader.upload_video(uploads / "missing.mp4", "Title", "Description")


def test_upload_video_http_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    video_path = uploads / "match.mp4"
    video_path.write_bytes(b"video")

    calls = _patch_media_file_upload(monkeypatch)
    error = HttpError(resp=_DummyResponse(), content=b"{}")
    videos = _DummyVideos(None, error=error)

    uploader = youtube_uploader.YouTubeUploader(
        api_key="API_KEY",
        upload_dir=uploads,
        log_root=tmp_path / "logs",
        service_factory=lambda _: _DummyService(videos),
    )

    with pytest.raises(youtube_uploader.YouTubeUploadError):
        uploader.upload_video(video_path, "Title", "Description")

    assert calls == [(str(video_path), "video/*", False)]

    session_logs = list((tmp_path / "logs").rglob("session-*.log"))
    assert session_logs, "expected session log"
    session_log = session_logs[0]
    content = session_log.read_text(encoding="utf-8")
    assert "Upload start" in content
    assert "Upload failed" in content

    error_logs = list(session_log.parent.glob("error_403.log"))
    assert error_logs, "expected error log to be created"
    assert "quotaExceeded" in error_logs[0].read_text(encoding="utf-8")
