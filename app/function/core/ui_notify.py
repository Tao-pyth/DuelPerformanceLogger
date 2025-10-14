"""Notification helpers for the Eel-powered interface."""

from __future__ import annotations

import logging

try:  # pragma: no cover - import guard for optional dependency
    import eel  # type: ignore
except Exception:  # pragma: no cover - defensive fallback if Eel is unavailable
    eel = None  # type: ignore

logger = logging.getLogger(__name__)


def notify(text: str, duration: float = 1.5) -> None:
    """Display a non-blocking toast message in the web frontend."""

    duration_ms = max(int(duration * 1000), 0)

    if eel is not None:
        try:
            eel.show_notification(text, duration_ms)
            return
        except AttributeError:
            logger.debug("Eel has no 'show_notification'; text=%r", text)
        except (RuntimeError, ConnectionError) as exc:  # pragma: no cover - runtime specific
            logger.warning(
                "Eel notify failed: %s; text=%r",
                type(exc).__name__,
                text,
                exc_info=True,
            )

    logger.info("UI notification: %s", text)


__all__ = ["notify"]
