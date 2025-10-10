"""Application settings screen."""

from __future__ import annotations

from kivy.core.window import Window
from kivy.properties import StringProperty
from kivymd.app import MDApp

from app.function.cmn_app_state import get_app_state, get_fallback_state
from app.function.cmn_resources import get_text
# 共通通知ヘルパーで通知手段を統合。
from app.function.core.ui_notify import notify

from .base import BaseManagedScreen


class SettingsScreen(BaseManagedScreen):
    """アプリ全体の設定（UI モード、バックアップ等）を扱う画面。"""

    selected_mode = StringProperty("normal")
    backup_info = StringProperty("")

    def on_pre_enter(self):
        # 現在の UI モードとバックアップ日時を画面表示に反映。
        app = get_app_state()
        self.selected_mode = getattr(app, "ui_mode", "normal")
        self._update_backup_label()

    def _set_ui_mode(self, mode: str) -> None:
        """UI モードを更新し、アプリ状態および DB へ反映する。"""

        app = get_app_state()
        app.ui_mode = mode
        db = getattr(app, "db", None)
        if db is not None:
            db.set_ui_mode(mode)
        fallback = get_fallback_state()
        fallback.ui_mode = mode
        self.selected_mode = mode
        notify(get_text("settings.mode_updated"))

    def _update_backup_label(self) -> None:
        """最新のバックアップパスを表示用ラベルへ反映。"""

        app = get_app_state()
        db = getattr(app, "db", None)
        last_backup = None
        if db is not None:
            last_backup = db.get_metadata("last_backup")
        if last_backup:
            self.backup_info = get_text("settings.last_backup").format(path=last_backup)
        else:
            self.backup_info = get_text("settings.no_backup")

    def create_backup(self) -> None:
        """CSV バックアップを作成し、保存場所をユーザーへ知らせる。"""

        app = get_app_state()
        db = getattr(app, "db", None)
        if db is None:
            notify(get_text("common.db_error"))
            return

        try:
            backup_path = db.export_backup()
        except Exception:  # pragma: no cover - defensive
            notify(get_text("settings.backup_failure"))
            return

        db.record_backup_path(backup_path)
        self._update_backup_label()
        notify(get_text("settings.backup_success"))

    def open_db_init_dialog(self):
        """DB 初期化を実行するか確認するダイアログを表示。"""

        dialog = self.ids.get("db_init_dialog")
        if dialog:
            dialog.open()

    def _dismiss_dialog(self, *_):
        dialog = self.ids.get("db_init_dialog")
        if dialog:
            dialog.dismiss()

    def _perform_db_initialization(self, *_):
        """ユーザーの確認後にデータベース初期化を実行。"""

        self._dismiss_dialog()

        app = get_app_state()
        db = getattr(app, "db", None)
        if db is None:
            notify(get_text("common.db_error"))
            return

        try:
            db.initialize_database()
            app.decks = db.fetch_decks()
            app.seasons = db.fetch_seasons()
            app.match_records = []
            app.current_match_settings = None
            app.current_match_count = 0
            app.opponent_decks = []
            fallback = get_fallback_state()
            fallback.db = db
            fallback.decks = []
            fallback.seasons = []
            fallback.match_records = []
            fallback.current_match_settings = None
            fallback.current_match_count = 0
            fallback.opponent_decks = []
        except Exception:  # pragma: no cover - defensive
            notify(get_text("settings.db_init_failure"))
            return

        notify(get_text("settings.db_init_success"))

    def exit_app(self):
        """アプリケーションを安全に終了させる。"""

        self._dismiss_dialog()
        app = MDApp.get_running_app()
        if app:
            app.stop()
        Window.close()


__all__ = ["SettingsScreen"]
