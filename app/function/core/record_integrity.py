"""Helpers for validating completed recording files."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Callable

__all__ = [
    "check_integrity",
    "ensure_integrity",
]


def _run_ffprobe(ffprobe: str | None, path: Path) -> bool:
    if not ffprobe:
        return True
    try:
        subprocess.run(
            [ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=duration", "-of", "csv=p=0", str(path)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):  # pragma: no cover - defensive
        return False


def check_integrity(path: Path, *, ffprobe: str | None = None, min_size_bytes: int = 1024) -> bool:
    """Return ``True`` when *path* appears to be a healthy recording."""

    if not path.exists() or not path.is_file():
        return False
    size = path.stat().st_size
    if size < max(min_size_bytes, 1):
        return False
    return _run_ffprobe(ffprobe, path)


def ensure_integrity(
    path: Path,
    *,
    ffprobe: str | None = None,
    retries: int = 1,
    wait_seconds: float = 0.5,
    retry_action: Callable[[], Path] | None = None,
) -> bool:
    """Validate *path* and optionally perform a retry when corruption is detected."""

    attempts = 0
    current_path = path
    while attempts <= retries:
        if check_integrity(current_path, ffprobe=ffprobe):
            return True
        attempts += 1
        if retry_action is None or attempts > retries:
            break
        time.sleep(max(wait_seconds, 0))
        current_path = retry_action()
    return False
