from __future__ import annotations

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.screen import MDScreen

from function.cmn_app_state import get_app_state
from function.cmn_resources import get_text

from .base import build_header, resolve_screen_name


class MenuScreen(MDScreen):
    """アプリケーションの初期画面."""

    # NOTE: ユーザーが最初に目にするトップメニュー。その他の画面への導線を
    # タイル状にまとめ、DB 移行メッセージなどのアラート表示も担当します。

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.migration_dialog: MDDialog | None = None

        # 画面全体は縦にスクロールできるレイアウトで構成。
        root_layout = MDBoxLayout(orientation="vertical", spacing=0)
        root_layout.add_widget(build_header(get_text("menu.title")))

        scroll_view = ScrollView()
        content = MDBoxLayout(
            orientation="vertical",
            padding=(dp(24), dp(24), dp(24), dp(32)),
            spacing=dp(24),
            size_hint_y=None,
        )
        content.bind(minimum_height=content.setter("height"))

        content.add_widget(self._build_hero_card())
        content.add_widget(self._build_navigation_grid())
        content.add_widget(
            MDLabel(
                text=get_text("common.version"),
                halign="center",
                theme_text_color="Hint",
                size_hint_y=None,
                height=dp(24),
            )
        )

        scroll_view.add_widget(content)
        root_layout.add_widget(scroll_view)
        self.add_widget(root_layout)

    def on_pre_enter(self):
        # DB マイグレーションの結果があればダイアログで案内する。
        app = get_app_state()
        message = getattr(app, "migration_result", "")
        if message:
            Clock.schedule_once(lambda *_: self._show_migration_message(message), 0)
            app.migration_result = ""

    def _show_migration_message(self, message: str):
        # 既にダイアログが表示されている場合は一旦閉じてから新しいものを開く。
        if self.migration_dialog:
            self.migration_dialog.dismiss()
        self.migration_dialog = MDDialog(
            title=get_text("settings.db_migration_title"),
            text=message,
            buttons=[
                MDFlatButton(
                    text=get_text("common.close"),
                    on_release=lambda *_: self._dismiss_dialog(),
                )
            ],
        )
        self.migration_dialog.open()

    def _dismiss_dialog(self):
        if self.migration_dialog:
            self.migration_dialog.dismiss()
            self.migration_dialog = None

    def _build_hero_card(self):
        """メニュー上部の紹介カードを構築する。"""

        card = MDCard(
            orientation="vertical",
            padding=(dp(24), dp(24), dp(24), dp(24)),
            size_hint=(1, None),
            height=dp(220),
            md_bg_color=self.theme_cls.primary_color,
            radius=[24, 24, 24, 24],
        )

        card.add_widget(
            MDLabel(
                text=get_text("menu.hero_title"),
                font_style="H4",
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1),
            )
        )
        card.add_widget(
            MDLabel(
                text=get_text("menu.hero_body"),
                theme_text_color="Custom",
                text_color=(1, 1, 1, 0.85),
            )
        )

        actions = MDBoxLayout(spacing=dp(12), size_hint_y=None, height=dp(48))
        actions.add_widget(
            MDRaisedButton(
                text=get_text("menu.primary_action"),
                on_press=lambda *_: self.change_screen("match_setup"),
            )
        )
        actions.add_widget(
            MDFlatButton(
                text=get_text("menu.secondary_action"),
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1),
                on_press=lambda *_: self.change_screen("stats"),
            )
        )
        card.add_widget(actions)

        return card

    def _build_navigation_grid(self):
        """各機能への遷移カードをまとめたグリッドを生成する。"""

        grid = MDGridLayout(
            cols=1,
            spacing=dp(16),
            size_hint_y=None,
            adaptive_height=True,
        )

        grid.add_widget(
            self._create_menu_option(
                icon="cards",
                title=get_text("menu.options.deck_register.title"),
                description=get_text("menu.options.deck_register.description"),
                screen_name="deck_register",
            )
        )
        grid.add_widget(
            self._create_menu_option(
                icon="calendar",
                title=get_text("menu.options.season_register.title"),
                description=get_text("menu.options.season_register.description"),
                screen_name="season_list",
            )
        )
        grid.add_widget(
            self._create_menu_option(
                icon="clipboard-text",
                title=get_text("menu.options.match_setup.title"),
                description=get_text("menu.options.match_setup.description"),
                screen_name="match_setup",
            )
        )
        grid.add_widget(
            self._create_menu_option(
                icon="chart-areaspline",
                title=get_text("menu.options.stats.title"),
                description=get_text("menu.options.stats.description"),
                screen_name="stats",
            )
        )
        grid.add_widget(
            self._create_menu_option(
                icon="cog",
                title=get_text("menu.options.settings.title"),
                description=get_text("menu.options.settings.description"),
                screen_name="settings",
            )
        )

        return grid

    def _create_menu_option(self, icon, title, description, screen_name):
        """単一のメニューカードを構築する。"""

        card = MDCard(
            orientation="vertical",
            padding=(dp(20), dp(20), dp(20), dp(20)),
            size_hint=(1, None),
            height=dp(180),
            radius=[18, 18, 18, 18],
            elevation=2,
        )

        header = MDBoxLayout(spacing=dp(12), size_hint_y=None, height=dp(36))
        header.add_widget(
            MDIcon(icon=icon, size_hint=(None, None), size=(dp(36), dp(36)))
        )
        header.add_widget(
            MDLabel(
                text=title,
                font_style="H5",
                theme_text_color="Primary",
            )
        )
        card.add_widget(header)

        card.add_widget(
            MDLabel(
                text=description,
                theme_text_color="Secondary",
            )
        )

        button_row = MDBoxLayout(size_hint_y=None, height=dp(48), padding=(0, dp(12), 0, 0))
        button_row.add_widget(Widget())
        button_row.add_widget(
            MDRaisedButton(
                text=get_text("common.open"),
                on_press=lambda *_: self.change_screen(screen_name),
            )
        )
        card.add_widget(button_row)

        return card

    def change_screen(self, screen_name):
        # ScreenManager が設定されていれば指定画面へ遷移させる。
        if self.manager:
            resolved = resolve_screen_name(screen_name)
            self.manager.current = resolved


__all__ = ["MenuScreen"]
