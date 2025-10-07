"""Application state helpers shared across screens."""

# NOTE: Kivy では `MDApp.get_running_app()` を通してアプリ全体の状態へアクセス
# しますが、テストや一部のモジュールではアプリがまだ起動していない場合も
# あります。そのようなケースでも安全に値へアクセスできるよう、フォール
# バック用の状態オブジェクトを提供しています。

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
        # `theme_cls` など KivyMD で一般的に参照される属性を SimpleNamespace で
        # 疑似的に用意しておく。これにより、画面クラスはアプリが未起動でも
        # 例外を出さずに参照を行える。
        self.theme_cls = SimpleNamespace(primary_color=(0.2, 0.6, 0.86, 1))
        self.reset()

    def reset(self) -> None:
        # 初期状態をまとめてリセットする。辞書やリストは都度新しいインスタンスを
        # 作成し、外部からの変更が内部状態に影響しないようにしている。
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

    # MDApp が起動済みならそのインスタンスを返し、そうでなければフォールバックを返す。
    app = MDApp.get_running_app()
    if app is None:
        return _fallback_app_state
    return app


def get_fallback_state() -> _FallbackAppState:
    """Expose the fallback state for modules that need direct access."""

    # 直接フォールバック状態を扱いたい（テストなど）場面のために公開。
    return _fallback_app_state


__all__ = ["get_app_state", "get_fallback_state"]
