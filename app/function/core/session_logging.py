"""Organise FFmpeg session logs under ``/log/recording``."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from . import paths

__all__ = ["RecordingSessionLogger"]


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


@dataclass
class RecordingSessionLogger:
    """Create and manage per-session directories for FFmpeg logs."""

    root: Path = field(default_factory=paths.recording_log_root)
    session_dir: Optional[Path] = None

    def ensure_session(self) -> Path:
        if self.session_dir is None:
            date_root = self.root / datetime.now().strftime("%Y%m%d")
            date_root.mkdir(parents=True, exist_ok=True)
            self.session_dir = date_root / _timestamp()
            self.session_dir.mkdir(parents=True, exist_ok=True)
        return self.session_dir

    def log_path(self, name: str = "ffmpeg.log") -> Path:
        session = self.ensure_session()
        return session / name
