"""Statistics screen."""

from __future__ import annotations

from kivy.metrics import dp
from kivymd.toast import toast
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.label import MDLabel
from kivymd.uix.menu import MDDropdownMenu

from function.cmn_app_state import get_app_state
from function.cmn_resources import get_text

from .base import BaseManagedScreen


class StatsScreen(BaseManagedScreen):
    """対戦結果の簡易統計を表示する画面。"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_deck: str | None = None
        self.deck_menu: MDDropdownMenu | None = None

        self.stats_label = MDLabel(
            text=get_text("stats.no_data"),
            theme_text_color="Secondary",
        )

        self.filter_button = MDRaisedButton(
            text=get_text("stats.filter_button"),
            on_press=lambda *_: self.open_deck_menu(),
        )
        self.filter_button.size_hint = (1, None)
        self.filter_button.height = dp(48)

        (
            self.root_layout,
            content_anchor,
            action_anchor,
        ) = self._create_scaffold(
            get_text("stats.header_title"),
            lambda: self.change_screen("menu"),
            lambda: self.change_screen("menu"),
        )

        content_box = MDBoxLayout(
            orientation="vertical",
            spacing=dp(16),
            padding=(dp(24), dp(24), dp(24), dp(24)),
            size_hint=(0.95, 0.95),
        )
        content_box.add_widget(self.filter_button)
        content_box.add_widget(self.stats_label)
        content_anchor.add_widget(content_box)

        clear_button = MDFlatButton(
            text=get_text("common.clear_filter"),
            on_press=lambda *_: self.clear_filter(),
        )
        clear_button.size_hint = (None, None)
        clear_button.height = dp(48)
        clear_button.width = dp(200)
        action_anchor.add_widget(clear_button)

    def on_pre_enter(self):
        # 画面表示時に統計情報を最新化。
        self.update_stats()

    def open_deck_menu(self):
        """統計対象のデッキを選ぶドロップダウンを表示。"""

        app = get_app_state()
        db = getattr(app, "db", None)
        if db is not None:
            app.decks = db.fetch_decks()
        if not app.decks:
            toast(get_text("stats.toast_no_decks"))
            return

        menu_items = [
            {
                "viewclass": "OneLineListItem",
                "text": deck["name"],
                "on_release": lambda name=deck["name"]: self.set_deck_filter(name),
            }
            for deck in app.decks
        ]

        if self.deck_menu:
            self.deck_menu.dismiss()

        self.deck_menu = MDDropdownMenu(caller=self.filter_button, items=menu_items, width_mult=4)
        self.deck_menu.open()

    def set_deck_filter(self, name: str):
        """選択されたデッキ名でフィルターを更新し、統計を再計算。"""

        self.selected_deck = name
        if self.deck_menu:
            self.deck_menu.dismiss()
        self.filter_button.text = get_text("stats.filter_label").format(deck_name=name)
        self.update_stats()

    def clear_filter(self):
        """フィルターを解除して全デッキの統計を表示。"""

        self.selected_deck = None
        self.filter_button.text = get_text("stats.filter_button")
        self.update_stats()

    def update_stats(self):
        """現在のフィルター設定に応じた勝敗集計を行う。"""

        app = get_app_state()
        db = getattr(app, "db", None)
        if db is None:
            self.stats_label.text = get_text("common.db_error")
            return

        records = db.fetch_matches(self.selected_deck)

        if not records:
            if self.selected_deck:
                self.stats_label.text = get_text("stats.no_data_for_deck").format(
                    deck_name=self.selected_deck
                )
            else:
                self.stats_label.text = get_text("stats.no_data")
            return

        total = len(records)
        wins = sum(1 for r in records if int(r["result"]) > 0)
        draws = sum(1 for r in records if int(r["result"]) == 0)
        losses = total - wins - draws
        win_rate = (wins / total) * 100

        header = get_text("stats.filter_label").format(
            deck_name=self.selected_deck or get_text("stats.filter_all")
        )
        self.stats_label.text = get_text("stats.summary_template").format(
            header=header,
            total=total,
            wins=wins,
            draws=draws,
            losses=losses,
            win_rate=win_rate,
        )


__all__ = ["StatsScreen"]
