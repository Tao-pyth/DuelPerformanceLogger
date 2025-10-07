"""Statistics screen."""

from __future__ import annotations

from kivy.properties import StringProperty
from kivymd.toast import toast
from kivymd.uix.menu import MDDropdownMenu

from function.cmn_app_state import get_app_state
from function.cmn_resources import get_text

from .base import BaseManagedScreen


class StatsScreen(BaseManagedScreen):
    """対戦結果の簡易統計を表示する画面。"""

    filter_button_label = StringProperty("")
    stats_text = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_deck: str | None = None
        self.deck_menu: MDDropdownMenu | None = None

    def on_kv_post(self, base_widget):
        super().on_kv_post(base_widget)
        self.filter_button_label = self.t("stats.filter_button")
        self.stats_text = self.t("stats.no_data")

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

        caller = self.ids.get("filter_button")
        self.deck_menu = MDDropdownMenu(caller=caller, items=menu_items, width_mult=4)
        self.deck_menu.open()

    def set_deck_filter(self, name: str):
        """選択されたデッキ名でフィルターを更新し、統計を再計算。"""

        self.selected_deck = name
        if self.deck_menu:
            self.deck_menu.dismiss()
        self.filter_button_label = self.t("stats.filter_label").format(deck_name=name)
        self.update_stats()

    def clear_filter(self):
        """フィルターを解除して全デッキの統計を表示。"""

        self.selected_deck = None
        self.filter_button_label = self.t("stats.filter_button")
        self.update_stats()

    def update_stats(self):
        """現在のフィルター設定に応じた勝敗集計を行う。"""

        app = get_app_state()
        db = getattr(app, "db", None)
        if db is None:
            self.stats_text = get_text("common.db_error")
            return

        records = db.fetch_matches(self.selected_deck)

        if not records:
            if self.selected_deck:
                self.stats_text = get_text("stats.no_data_for_deck").format(
                    deck_name=self.selected_deck
                )
            else:
                self.stats_text = get_text("stats.no_data")
            return

        total = len(records)
        wins = sum(1 for r in records if int(r["result"]) > 0)
        draws = sum(1 for r in records if int(r["result"]) == 0)
        losses = total - wins - draws
        win_rate = (wins / total) * 100

        header = get_text("stats.filter_label").format(
            deck_name=self.selected_deck or get_text("stats.filter_all")
        )
        self.stats_text = get_text("stats.summary_template").format(
            header=header,
            total=total,
            wins=wins,
            draws=draws,
            losses=losses,
            win_rate=win_rate,
        )


__all__ = ["StatsScreen"]
