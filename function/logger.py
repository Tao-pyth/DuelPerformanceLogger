"""Application-level logging helpers for persisting error details."""

from __future__ import annotations

import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

_LOG_DIR = Path(__file__).resolve().parent.parent / "resource" / "log"
_LOG_DIR.mkdir(parents=True, exist_ok=True)


def log_error(message: str, exc: BaseException | None = None, **context: Any) -> Path:
    """Write a detailed error log entry and return the written file path."""

    timestamp = datetime.now()
    log_path = _LOG_DIR / f"{timestamp:%Y%m%d}.log"
    lines = [f"[{timestamp:%Y-%m-%d %H:%M:%S}] {message}"]

    if context:
        context_repr = ", ".join(f"{key}={value!r}" for key, value in context.items())
        lines.append(f"Context: {context_repr}")

    if exc is not None:
        lines.append("Traceback:")
        lines.extend(traceback.format_exception(type(exc), exc, exc.__traceback__))
    else:
        lines.append("No exception information available.")

    with log_path.open("a", encoding="utf-8") as stream:
        stream.write("\n".join(lines))
        stream.write("\n")

    return log_path
