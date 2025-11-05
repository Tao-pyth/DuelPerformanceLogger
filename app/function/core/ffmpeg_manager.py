"""Helpers for managing FFmpeg binaries across supported platforms."""

from __future__ import annotations

import logging
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from platform import system
from typing import TYPE_CHECKING

from . import paths

if TYPE_CHECKING:  # pragma: no cover
    from .config_handler import RecordingSettings

__all__ = [
    "FFmpegStatus",
    "inspect",
    "ensure",
    "remove",
    "managed_executable_path",
]


_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class FFmpegStatus:
    """Represents the availability of an FFmpeg executable."""

    path: Path
    exists: bool
    managed: bool

    def to_dict(self) -> dict[str, object]:
        """Serialize the status into a JSON friendly mapping."""

        return {
            "path": str(self.path),
            "exists": self.exists,
            "managed": self.managed,
        }


def managed_executable_path() -> Path:
    """Return the default managed FFmpeg executable path for the current OS."""

    platform_name = system()
    executable = "ffmpeg.exe" if platform_name == "Windows" else "ffmpeg"
    return paths.user_data_root() / "bin" / executable


def inspect(settings: "RecordingSettings") -> FFmpegStatus:
    """Inspect FFmpeg availability based on :class:`RecordingSettings`."""

    candidate = settings.ffmpeg_path
    managed = False
    if not candidate or not str(candidate):
        candidate = managed_executable_path()
        managed = True
    return FFmpegStatus(path=candidate, exists=candidate.exists(), managed=managed)


def ensure(settings: "RecordingSettings", *, allow_download: bool = False) -> FFmpegStatus:
    """Ensure an FFmpeg executable exists, downloading a stub if permitted."""

    status = inspect(settings)
    if status.exists:
        return status
    if not status.managed:
        raise FileNotFoundError(f"FFmpeg executable not found: {status.path}")
    if not allow_download:
        raise FileNotFoundError(f"FFmpeg executable is missing: {status.path}")
    _deploy_stub(status.path)
    return FFmpegStatus(path=status.path, exists=True, managed=True)


def remove(settings: "RecordingSettings") -> FFmpegStatus:
    """Remove the managed FFmpeg binary if it exists."""

    status = inspect(settings)
    if status.managed and status.path.exists():
        try:
            status.path.unlink()
        except OSError as exc:  # pragma: no cover - filesystem guard
            _LOGGER.warning("Failed to remove managed FFmpeg binary", exc_info=exc)
    return inspect(settings)


def _deploy_stub(target: Path) -> None:
    """Create a minimal FFmpeg stub executable for offline environments."""

    target.parent.mkdir(parents=True, exist_ok=True)
    platform_name = system()
    if platform_name == "Windows":
        target.write_text("@echo off\necho FFmpeg stub\n", encoding="utf-8")
    else:
        target.write_text("#!/bin/sh\nprintf 'FFmpeg stub\\n'\n", encoding="utf-8")
        try:
            current_mode = os.stat(target).st_mode
        except FileNotFoundError:  # pragma: no cover - race condition guard
            current_mode = 0o755
        os.chmod(target, current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
