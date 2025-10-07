"""Match setup screen."""

from __future__ import annotations

from kivy.core.window import Window
from kivy.properties import BooleanProperty, StringProperty
from kivymd.toast import toast
from kivymd.uix.menu import MDDropdownMenu

from function.cmn_app_state import get_app_state
from function.cmn_resources import get_text

from .base import BaseManagedScreen


class MatchSetupScreen(BaseManagedScreen):
    screen_mode = "normal"

    deck_button_label = StringProperty("")
    active_mode = StringProperty("normal")
    is_broadcast = BooleanProperty(False)
    selected_deck = StringProperty("")

    def __init__(self, **kwargs):
        # `screen_mode` は通常画面か配信向け画面かを表す。継承クラスで上書きされる。
        self.screen_mode = getattr(self.__class__, "screen_mode", "normal")
        super().__init__(**kwargs)
        self.deck_menu: MDDropdownMenu | None = None

    def on_kv_post(self, base_widget):
        super().on_kv_post(base_widget)
        self.deck_button_label = self.t("match_setup.deck_button_default")

    def on_pre_enter(self):
        # 画面再表示時は選択状態をリセットし、表示モードに応じてレイアウトを切替。
        self.selected_deck = ""
        self.deck_button_label = self.t("match_setup.deck_button_default")
        field = self._get_match_count_field()
        if field is not None:
            field.text = "0"

        app = get_app_state()
        mode = self.screen_mode or getattr(app, "ui_mode", "normal")
        self.active_mode = mode
        self.is_broadcast = mode == "broadcast"
        self._sync_window_size(mode)

    def open_deck_menu(self):
        """登録済みデッキをプルダウンとして表示する。"""

        app = get_app_state()
        db = getattr(app, "db", None)
        if db is not None:
            app.decks = db.fetch_decks()
        if not app.decks:
            toast(get_text("match_setup.toast_no_decks"))
            return

        menu_items = [
            {
                "viewclass": "OneLineListItem",
                "text": deck["name"],
                "on_release": lambda name=deck["name"]: self.set_selected_deck(name),
            }
            for deck in app.decks
        ]

        if self.deck_menu:
            self.deck_menu.dismiss()

        caller = self._get_deck_button()
        self.deck_menu = MDDropdownMenu(caller=caller, items=menu_items, width_mult=4)
        self.deck_menu.open()

    def set_selected_deck(self, name: str):
        """ユーザーが選択したデッキ名を反映し、次の対戦番号を取得。"""

        self.selected_deck = name
        self.deck_button_label = self.t("match_setup.selected_deck_label").format(
            deck_name=name
        )
        app = get_app_state()
        db = getattr(app, "db", None)
        if db is not None:
            next_no = db.get_next_match_number(name)
            field = self._get_match_count_field()
            if field is not None:
                field.text = str(next_no)
        if self.deck_menu:
            self.deck_menu.dismiss()

    def start_entry(self):
        """選択したデッキ情報で対戦入力画面へ遷移する。"""

        if not self.selected_deck:
            toast(get_text("match_setup.toast_select_deck"))
            return

        try:
            field = self._get_match_count_field()
            text = field.text if field is not None else "0"
            initial_count = int(text or 0)
        except ValueError:
            toast(get_text("match_setup.toast_invalid_count"))
            return

        app = get_app_state()
        app.current_match_settings = {
            "count": initial_count,
            "deck_name": self.selected_deck,
        }
        app.current_match_count = initial_count

        toast(get_text("match_setup.toast_start"))
        self.change_screen("match_entry")

    def _get_match_count_field(self):
        return self.ids.get("match_count_field_normal") or self.ids.get(
            "match_count_field_broadcast"
        )

    def _get_deck_button(self):
        return self.ids.get("deck_button_normal") or self.ids.get(
            "deck_button_broadcast"
        )

    def on_leave(self):
        app = get_app_state()
        if self.screen_mode != "broadcast":
            default_size = getattr(app, "default_window_size", None)
            if default_size:
                Window.size = default_size


class MatchSetupBroadcastScreen(MatchSetupScreen):
    screen_mode = "broadcast"


__all__ = ["MatchSetupScreen", "MatchSetupBroadcastScreen"]
