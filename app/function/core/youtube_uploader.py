"""YouTube への動画アップロードを行うユーティリティ。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from app.function.core import paths

try:  # pragma: no cover - optional dependency typing guard
    from google.oauth2.credentials import Credentials
except Exception:  # pragma: no cover - import guard
    Credentials = object  # type: ignore[assignment]

LOGGER = logging.getLogger(__name__)


class YouTubeUploadError(RuntimeError):
    """アップロード処理で発生したエラーを表す例外。"""


@dataclass(slots=True)
class YouTubeUploadResult:
    """アップロード成功時の結果を格納するデータクラス。"""

    video_id: str
    url: str
    log_path: Path


class YouTubeUploader:
    """YouTube Data API v3 を用いたシンプルなアップロードラッパー。"""

    def __init__(
        self,
        credentials_provider: Callable[[], "Credentials"],
        upload_dir: str | Path,
        *,
        default_privacy: str = "unlisted",
        log_root: Path | None = None,
        service_factory: Optional[Callable[["Credentials"], object]] = None,
    ) -> None:
        self._credentials_provider = credentials_provider
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.default_privacy = default_privacy
        self.log_root = log_root or paths.youtube_log_dir()
        self.log_root.mkdir(parents=True, exist_ok=True)
        self._service_factory = service_factory

    def upload_video(
        self,
        filepath: Path | str,
        title: str,
        description: str,
        *,
        privacy_status: Optional[str] = None,
    ) -> YouTubeUploadResult:
        path = Path(filepath)
        if not path.is_absolute():
            path = self.upload_dir / path
        if not path.exists():
            raise FileNotFoundError(path)

        session_log = self._open_session_log()
        self._write_log(session_log, f"Upload start: file={path}")

        privacy = (privacy_status or self.default_privacy or "unlisted").lower()
        service = self._build_service()
        media = MediaFileUpload(str(path), mimetype="video/*", resumable=False)
        body = {
            "snippet": {"title": title, "description": description},
            "status": {"privacyStatus": privacy},
        }

        try:
            request = service.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media,
            )
            response = request.execute()
        except HttpError as exc:  # pragma: no cover - network dependent
            self._handle_error(session_log, exc)
            raise YouTubeUploadError(f"YouTube API error: {exc}") from exc

        video_id = response.get("id", "")
        url = f"https://www.youtube.com/watch?v={video_id}" if video_id else ""
        self._write_log(
            session_log,
            f"Upload completed: status=OK video_id={video_id} url={url}",
        )
        return YouTubeUploadResult(video_id=video_id, url=url, log_path=session_log)

    def _build_service(self) -> object:
        credentials = self._credentials_provider()
        if self._service_factory is not None:
            return self._service_factory(credentials)
        return build(
            "youtube",
            "v3",
            credentials=credentials,
            cache_discovery=False,
        )

    def _open_session_log(self) -> Path:
        now = datetime.now(timezone.utc)
        day_dir = self.log_root / now.strftime("%Y%m%d")
        day_dir.mkdir(parents=True, exist_ok=True)
        log_path = day_dir / f"session-{now.strftime('%H%M%S')}.log"
        log_path.touch(exist_ok=True)
        return log_path

    def _write_log(self, path: Path, message: str) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        with path.open("a", encoding="utf-8") as stream:
            stream.write(f"[{timestamp}] {message}\n")
        LOGGER.info("%s", message)

    def _handle_error(self, session_log: Path, exc: HttpError) -> None:
        status = getattr(exc, "status_code", None) or getattr(exc.resp, "status", "")
        reason = getattr(exc, "error_details", None) or getattr(exc.resp, "reason", "")
        message = f"Upload failed: status={status} reason={reason}"
        self._write_log(session_log, message)
        error_dir = session_log.parent
        error_name = f"error_{status or 'unknown'}.log"
        error_path = error_dir / error_name
        with error_path.open("a", encoding="utf-8") as stream:
            stream.write(message + "\n")
        LOGGER.error("%s", message, exc_info=exc)

__all__ = ["YouTubeUploader", "YouTubeUploadError", "YouTubeUploadResult"]

