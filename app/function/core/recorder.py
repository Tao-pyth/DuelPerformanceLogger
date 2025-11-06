"""FFmpeg recording orchestration utilities."""

from __future__ import annotations

import subprocess
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from .config_handler import RecordingSettings
from . import ffmpeg_manager
from .ffmpeg_command_builder import (
    RecordingProfile,
    build_record_command,
    build_screenshot_command,
    resolve_profile,
    resolve_quality_preset,
)
from .file_sanitizer import ensure_extension, sanitize_filename
from . import record_integrity, session_logging
from .retry_queue import RetryQueue
from . import paths

logger = logging.getLogger(__name__)

__all__ = ["RecordingError", "FFmpegRecorder", "RecordingResult"]


class RecordingError(RuntimeError):
    """Raised when recording operations fail."""


@dataclass(slots=True)
class RecordingResult:
    """Result of a completed recording session."""

    file_path: Path
    profile: RecordingProfile
    fps: int
    bitrate: str
    duration: float | None = None
    status: str = "completed"


class FFmpegRecorder:
    """Manage FFmpeg processes for recording and screenshots."""

    def __init__(
        self,
        settings: RecordingSettings,
        *,
        process_factory: Callable[..., subprocess.Popen] | None = None,
        integrity_checker: Callable[..., bool] = record_integrity.ensure_integrity,
        session_logger: session_logging.RecordingSessionLogger | None = None,
        database: Optional["DatabaseManager"] = None,
        retry_queue: RetryQueue | None = None,
        notifier: Callable[[str, float], None] | None = None,
    ) -> None:
        self.settings = settings
        self._process_factory = process_factory or subprocess.Popen
        self._integrity_checker = integrity_checker
        self._session_logger = session_logger or session_logging.RecordingSessionLogger()
        self._database = database
        self._retry_queue = retry_queue or RetryQueue()
        self._notifier = notifier
        self._process: subprocess.Popen | None = None
        self._log_handle = None
        self._current_profile = resolve_profile(settings.profile)
        self._current_quality = resolve_quality_preset(settings.quality_preset)
        self._current_output: Optional[Path] = None

    # ------------------------------------------------------------------
    # Recording lifecycle
    # ------------------------------------------------------------------
    def is_running(self) -> bool:
        """現在録画プロセスが稼働中かを返します。"""

        return self._process is not None and self._process.poll() is None

    def start(self, match_id: int | None = None) -> Path:
        job_id = f"ffmpeg:start:{match_id or 'unbound'}"
        return self._run_with_retry(
            job_id,
            lambda: self._start_once(match_id),
            "録画開始",
            backoff_seconds=min(self._retry_queue.backoff_seconds, 1.0),
        )

    def stop(self, match_id: int | None = None) -> RecordingResult:
        if self._process is None or self._current_output is None:
            raise RecordingError("No active recording to stop")

        job_id = f"ffmpeg:stop:{match_id or 'unbound'}"
        try:
            result = self._run_with_retry(
                job_id,
                lambda: self._stop_once(match_id),
                "録画停止",
                backoff_seconds=min(self._retry_queue.backoff_seconds, 1.0),
            )
        finally:
            self._process = None
            self._current_output = None
        return result

    # ------------------------------------------------------------------
    # Screenshot helpers
    # ------------------------------------------------------------------
    def capture_screenshot(self, name: str | None = None) -> Path:
        executable = self._resolve_ffmpeg()
        output_dir = self.settings.save_directory
        sanitized = sanitize_filename(name or self._default_basename(prefix="screenshot"))
        output_path = ensure_extension(output_dir / sanitized, "png")
        profile = resolve_profile(self.settings.profile)
        command = build_screenshot_command(
            executable,
            output_path,
            profile=profile,
            video_source=self.settings.video_source,
        )
        subprocess.run(command, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return output_path

    # ------------------------------------------------------------------
    # Internal utilities
    # ------------------------------------------------------------------
    def _default_basename(self, prefix: str = "match") -> str:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return f"{prefix}_{timestamp}"

    def _build_output_path(self, match_id: int | None) -> Path:
        base_name = self._default_basename()
        if match_id is not None:
            base_name = f"match_{match_id}_{datetime.now().strftime('%H%M%S')}"
        sanitized = sanitize_filename(base_name)
        return ensure_extension(self.settings.save_directory / sanitized, "mp4")

    def _resolve_ffmpeg(self) -> Path:
        status = ffmpeg_manager.inspect(self.settings)
        if status.exists:
            return status.path
        if not self.settings.auto_download_ffmpeg:
            raise RecordingError(f"FFmpeg executable not found: {status.path}")
        try:
            ensured = ffmpeg_manager.ensure(self.settings, allow_download=True)
        except FileNotFoundError as exc:  # pragma: no cover - defensive
            raise RecordingError(str(exc)) from exc
        return ensured.path

    def _start_once(self, match_id: int | None) -> Path:
        if self._process is not None:
            raise RecordingError("A recording is already running")

        executable = self._resolve_ffmpeg()
        output_path = self._build_output_path(match_id)
        log_path = self._session_logger.log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self._log_handle = open(log_path, "a", encoding="utf-8")

        self._current_profile = resolve_profile(self.settings.profile)
        self._current_quality = resolve_quality_preset(self.settings.quality_preset)
        command = build_record_command(
            executable,
            output_path,
            quality=self._current_quality,
            profile=self._current_profile,
            video_source=self.settings.video_source,
            audio_device=self.settings.audio_device,
        )
        try:
            process = self._process_factory(
                command,
                stdout=self._log_handle,
                stderr=subprocess.STDOUT,
            )
        except OSError as exc:  # pragma: no cover - process spawn failure
            self._cleanup_handles()
            raise RecordingError("Failed to spawn FFmpeg") from exc

        self._process = process
        self._current_output = output_path
        return output_path

    def _stop_once(self, match_id: int | None) -> RecordingResult:
        process = self._process
        if process is None or self._current_output is None:
            raise RecordingError("No active recording to stop")

        poll = getattr(process, "poll", None)
        is_active = True
        if callable(poll):
            try:
                is_active = poll() is None
            except Exception:  # pragma: no cover - defensive fallback
                is_active = True

        if is_active:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:  # pragma: no cover - slow ffmpeg
                process.kill()
                process.wait()

        self._cleanup_handles()

        integrity_job = f"ffmpeg:integrity:{match_id or 'unbound'}"
        try:
            self._run_with_retry(
                integrity_job,
                lambda: self._ensure_integrity(self._current_output),
                "録画ファイル整合性チェック",
                metadata={"path": str(self._current_output)},
                raise_on_failure=False,
                backoff_seconds=0.5,
            )
        except RecordingError:
            pass

        state = self._retry_queue.state(integrity_job)
        is_valid = state is None or state.status != "failed"

        status = "completed" if is_valid else "corrupted"
        result = RecordingResult(
            file_path=self._current_output,
            profile=self._current_profile,
            fps=self._current_quality.fps,
            bitrate=self._current_quality.video_bitrate,
            duration=None,
            status=status,
        )

        if status == "completed" and self._database is not None and match_id is not None:
            self._database.record_recording(
                match_id,
                self._current_output,
                profile=self._current_profile.name,
                fps=self._current_quality.fps,
                bitrate=self._current_quality.video_bitrate,
                status=status,
                duration=None,
            )

        return result

    def _ensure_integrity(self, path: Path) -> bool:
        if self._integrity_checker(path):
            return True
        raise RecordingError("Recording integrity check failed")

    def _run_with_retry(
        self,
        job_id: str,
        func: Callable[[], Any],
        description: str,
        *,
        metadata: Optional[dict[str, Any]] = None,
        raise_on_failure: bool = True,
        max_attempts: int | None = None,
        backoff_seconds: float | None = None,
    ) -> Any:
        metadata = metadata or {}

        def on_retry(exc: Exception, state) -> None:
            logger.warning(
                "%s retry scheduled (attempt %s/%s): %s",
                description,
                state.attempts,
                state.max_attempts,
                exc,
            )

        def on_failure(exc: Exception, state) -> None:
            message = f"{description}の再試行が上限に達しました"
            logger.error("%s: attempts=%s", message, state.attempts, exc_info=exc)
            self._notify(message)

        def on_success(result: Any, state) -> None:
            logger.info("%sに成功しました（試行 %s 回目）", description, state.attempts)

        return self._retry_queue.run(
            job_id,
            func,
            description=description,
            metadata=metadata,
            on_retry=on_retry,
            on_failure=on_failure,
            on_success=on_success,
            raise_on_failure=raise_on_failure,
            max_attempts=max_attempts,
            backoff_seconds=backoff_seconds,
        )

    def _notify(self, message: str, duration: float = 3.6) -> None:
        if self._notifier is None:
            return
        try:
            self._notifier(message, duration=duration)
        except TypeError:  # pragma: no cover - notifier without duration parameter
            self._notifier(message)

    def _cleanup_handles(self) -> None:
        if self._log_handle:
            try:
                self._log_handle.close()
            finally:
                self._log_handle = None


# Avoid circular import
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from app.function.cmn_database import DatabaseManager
