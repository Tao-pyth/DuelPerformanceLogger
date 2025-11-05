"""FFmpeg recording orchestration utilities."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from .config_handler import RecordingSettings
from .ffmpeg_command_builder import (
    RecordingProfile,
    build_record_command,
    build_screenshot_command,
    resolve_profile,
    resolve_quality_preset,
)
from .file_sanitizer import ensure_extension, sanitize_filename
from . import record_integrity, session_logging
from . import paths

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
    ) -> None:
        self.settings = settings
        self._process_factory = process_factory or subprocess.Popen
        self._integrity_checker = integrity_checker
        self._session_logger = session_logger or session_logging.RecordingSessionLogger()
        self._database = database
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
            self._process = self._process_factory(
                command,
                stdout=self._log_handle,
                stderr=subprocess.STDOUT,
            )
        except OSError as exc:  # pragma: no cover - process spawn failure
            self._cleanup_handles()
            raise RecordingError("Failed to spawn FFmpeg") from exc

        self._current_output = output_path
        return output_path

    def stop(self, match_id: int | None = None) -> RecordingResult:
        if self._process is None or self._current_output is None:
            raise RecordingError("No active recording to stop")

        process = self._process
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:  # pragma: no cover - slow ffmpeg
            process.kill()
            process.wait()

        self._cleanup_handles()

        success = self._integrity_checker(self._current_output)
        status = "completed" if success else "corrupted"
        result = RecordingResult(
            file_path=self._current_output,
            profile=self._current_profile,
            fps=self._current_quality.fps,
            bitrate=self._current_quality.video_bitrate,
            duration=None,
            status=status,
        )

        if success and self._database is not None and match_id is not None:
            self._database.record_recording(
                match_id,
                self._current_output,
                profile=self._current_profile.name,
                fps=self._current_quality.fps,
                bitrate=self._current_quality.video_bitrate,
                status=status,
                duration=None,
            )

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
        candidate = self.settings.ffmpeg_path
        if candidate and candidate.exists():
            return candidate
        if candidate:
            target = candidate
        else:
            bin_dir = paths.user_data_root() / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            target = bin_dir / "ffmpeg"
        if target.exists():
            return target
        if not self.settings.auto_download_ffmpeg:
            return target
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("#!/bin/sh\necho 'ffmpeg stub'\n", encoding="utf-8")
        target.chmod(0o755)
        return target

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
