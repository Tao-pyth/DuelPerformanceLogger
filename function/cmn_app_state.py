"""Application state helpers shared across screens."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Optional

from kivy.core.window import Window
from kivymd.app import MDApp

from .cmn_config import load_config
from .cmn_database import DatabaseManager


class _FallbackAppState:
    """Provide default attributes when no running MDApp is available."""

    def __init__(self) -> None:
        self.theme_cls = SimpleNamespace(primary_color=(0.2, 0.6, 0.86, 1))
        self.reset()

    def reset(self) -> None:
        self.config = load_config()
        self.ui_mode = "normal"
        self.decks: list[dict[str, Any]] = []
        self.seasons: list[dict[str, Any]] = []
        self.match_records: list[dict[str, Any]] = []
        self.current_match_settings: Optional[dict[str, Any]] = None
        self.current_match_count = 0
        self.db: Optional[DatabaseManager] = None
        self.opponent_decks: list[str] = []
        self.default_window_size = Window.size
        self.migration_result: str = ""


_fallback_app_state = _FallbackAppState()


def get_app_state():
    """Return the running app instance or a fallback with default attributes."""

    app = MDApp.get_running_app()
    if app is None:
        return _fallback_app_state
    return app


def get_fallback_state() -> _FallbackAppState:
    """Expose the fallback state for modules that need direct access."""

    return _fallback_app_state


__all__ = ["get_app_state", "get_fallback_state"]
