from __future__ import annotations

from functools import partial

from kivy.properties import BooleanProperty, ListProperty, StringProperty
from kivymd.uix.screen import MDScreen

from app.function.cmn_app_state import get_app_state
from .base import resolve_screen_name


class MenuScreen(MDScreen):
    """アプリケーションの初期画面."""

    menu_data = ListProperty([])
    migration_message = StringProperty("")
    show_migration_banner = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.menu_data = [
            {
                "icon": "cards",
                "title_key": "menu.options.deck_register.title",
                "description_key": "menu.options.deck_register.description",
                "on_navigate": partial(self.change_screen, "deck_register"),
                "parent_screen": self,
            },
            {
                "icon": "calendar",
                "title_key": "menu.options.season_register.title",
                "description_key": "menu.options.season_register.description",
                "on_navigate": partial(self.change_screen, "season_list"),
                "parent_screen": self,
            },
            {
                "icon": "clipboard-text",
                "title_key": "menu.options.match_setup.title",
                "description_key": "menu.options.match_setup.description",
                "on_navigate": partial(self.change_screen, "match_setup"),
                "parent_screen": self,
            },
            {
                "icon": "chart-areaspline",
                "title_key": "menu.options.stats.title",
                "description_key": "menu.options.stats.description",
                "on_navigate": partial(self.change_screen, "stats"),
                "parent_screen": self,
            },
            {
                "icon": "cog",
                "title_key": "menu.options.settings.title",
                "description_key": "menu.options.settings.description",
                "on_navigate": partial(self.change_screen, "settings"),
                "parent_screen": self,
            },
        ]

    def on_pre_enter(self):
        app = get_app_state()
        message = getattr(app, "migration_result", "")
        if message:
            self.migration_message = message
            self.show_migration_banner = True
            app.migration_result = ""
        else:
            self.show_migration_banner = False

    def change_screen(self, screen_name):
        # ScreenManager が設定されていれば指定画面へ遷移させる。
        if self.manager:
            resolved = resolve_screen_name(screen_name)
            self.manager.current = resolved

    def dismiss_migration_message(self):
        """Dismiss the migration banner shown at the top of the menu."""

        self.show_migration_banner = False


__all__ = ["MenuScreen"]
