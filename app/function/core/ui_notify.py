"""Cross-platform notification helpers for Kivy-based screens.

This module exposes :func:`notify` to present short user notifications in a
platform-aware way. Android devices use the native toast implementation while
other platforms fall back to :class:`~kivymd.uix.snackbar.Snackbar`.
"""

from __future__ import annotations

from kivy.utils import platform
from kivymd.uix.snackbar import Snackbar


def notify(text: str, duration: float = 1.5) -> None:
    """Display a notification appropriate for the current platform."""

    if platform == "android":
        try:
            from kivymd.toast import toast

            toast(text)
            return
        except Exception:  # pragma: no cover - defensive, platform specific
            pass

    Snackbar(text=text, duration=duration).open()


__all__ = ["notify"]
