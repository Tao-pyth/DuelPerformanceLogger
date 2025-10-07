"""Application entry point wiring together the KivyMD screens."""

from __future__ import annotations

import os
from pathlib import Path
from platform import system

from kivy.core.text import LabelBase, DEFAULT_FONT
from kivy.core.window import Window
from kivymd.app import MDApp
from kivymd.uix.screenmanager import MDScreenManager

from function import DatabaseManager, DatabaseError
from function.cmn_app_state import get_fallback_state
from function.cmn_config import load_config
from function.cmn_logger import log_db_error
from function.cmn_resources import get_text
from function.screen.deck_registration_screen import DeckRegistrationScreen
from function.screen.match_entry_screen import MatchEntryScreen
from function.screen.match_setup_screen import MatchSetupScreen
from function.screen.menu_screen import MenuScreen
from function.screen.season_list_screen import SeasonListScreen
from function.screen.season_registration_screen import SeasonRegistrationScreen
from function.screen.settings_screen import SettingsScreen
from function.screen.stats_screen import StatsScreen

if system() == "Windows":
    _system_root = Path(os.environ.get("SystemRoot", "C:/Windows"))
    font_candidates = [
        _system_root / "Fonts" / "YuGothicUIRegular.ttf",
        _system_root / "Fonts" / "msgothic.ttc",
        _system_root / "Fonts" / "meiryo.ttc",
    ]
    for font_path in font_candidates:
        if font_path.exists():
            LabelBase.register(DEFAULT_FONT, str(font_path))
            break


class DeckAnalyzerApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "BlueGray"
        self.config = load_config()
        self.default_window_size = Window.size

        self.db = DatabaseManager()
        self.db.ensure_database()
        self.ui_mode = self.db.get_ui_mode()

        expected_version_raw = self.config.get("database", {}).get(
            "expected_version", DatabaseManager.CURRENT_SCHEMA_VERSION
        )
        try:
            expected_version = int(expected_version_raw)
        except (TypeError, ValueError):
            expected_version = DatabaseManager.CURRENT_SCHEMA_VERSION
        current_version = self.db.get_schema_version()
        if current_version != expected_version:
            self.migration_result = self._handle_version_mismatch(
                current_version, expected_version
            )
        else:
            self.migration_result = ""

        self.db.set_schema_version(expected_version)

        self.decks = self.db.fetch_decks()
        self.seasons = self.db.fetch_seasons()
        self.match_records = self.db.fetch_matches()
        self.opponent_decks = self.db.fetch_opponent_decks()
        self.current_match_settings = None
        self.current_match_count = 0

        fallback = get_fallback_state()
        fallback.reset()
        fallback.theme_cls.primary_color = self.theme_cls.primary_color
        fallback.db = self.db
        fallback.decks = list(self.decks)
        fallback.seasons = list(self.seasons)
        fallback.match_records = list(self.match_records)
        fallback.opponent_decks = list(self.opponent_decks)
        fallback.config = dict(self.config)
        fallback.ui_mode = self.ui_mode
        fallback.default_window_size = self.default_window_size
        fallback.migration_result = self.migration_result

        screen_manager = MDScreenManager()
        screen_manager.add_widget(MenuScreen(name="menu"))
        screen_manager.add_widget(DeckRegistrationScreen(name="deck_register"))
        screen_manager.add_widget(SeasonListScreen(name="season_list"))
        screen_manager.add_widget(SeasonRegistrationScreen(name="season_register"))
        screen_manager.add_widget(MatchSetupScreen(name="match_setup"))
        screen_manager.add_widget(MatchEntryScreen(name="match_entry"))
        screen_manager.add_widget(StatsScreen(name="stats"))
        screen_manager.add_widget(SettingsScreen(name="settings"))
        return screen_manager

    def _handle_version_mismatch(self, current_version: int, expected_version: int) -> str:
        lines = [
            get_text("settings.db_migration_detected").format(
                current=current_version, expected=expected_version
            )
        ]

        try:
            backup_path = self.db.export_backup()
            lines.append(
                get_text("settings.db_migration_backup").format(path=str(backup_path))
            )
            self.db.record_backup_path(backup_path)

            self.db.initialize_database()
            self.db.set_schema_version(expected_version)

            try:
                restored = self.db.import_backup(backup_path)
            except DatabaseError as exc:
                log_db_error(
                    "Failed to restore database during migration", exc, backup=str(backup_path)
                )
                lines.append(
                    get_text("settings.db_migration_restore_failed").format(error=str(exc))
                )
                return "\n".join(
                    [get_text("settings.db_migration_failure").format(error=str(exc))]
                    + lines
                )
            else:
                lines.append(
                    get_text("settings.db_migration_restore_success").format(
                        decks=restored.get("decks", 0),
                        seasons=restored.get("seasons", 0),
                        matches=restored.get("matches", 0),
                    )
                )

            return "\n".join([get_text("settings.db_migration_success")] + lines)
        except Exception as exc:  # pragma: no cover - defensive
            return "\n".join(
                [
                    get_text("settings.db_migration_failure").format(error=str(exc)),
                    *lines,
                ]
            )


if __name__ == "__main__":
    DeckAnalyzerApp().run()
