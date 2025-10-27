"""Utility helpers for creating filesystem-safe filenames."""

from __future__ import annotations

import re
from pathlib import Path

__all__ = ["sanitize_filename", "ensure_extension"]

_INVALID_PATTERN = re.compile(r"[^0-9A-Za-z._-]+")
_DEFAULT_NAME = "recording"


def sanitize_filename(name: str | None, *, default: str = _DEFAULT_NAME, max_length: int = 128) -> str:
    """Return a safe filename that excludes unsupported characters."""

    candidate = (name or "").strip()
    if not candidate:
        candidate = default
    sanitized = _INVALID_PATTERN.sub("_", candidate)
    sanitized = sanitized.strip("._") or default
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    return sanitized


def ensure_extension(path: Path, extension: str) -> Path:
    """Ensure *path* has the provided *extension* (without a leading dot)."""

    suffix = f".{extension.lstrip('.')}"
    if path.suffix.lower() != suffix.lower():
        return path.with_suffix(suffix)
    return path
