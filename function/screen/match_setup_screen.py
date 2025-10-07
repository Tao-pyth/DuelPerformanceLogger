"""Match setup screen."""

from __future__ import annotations

from kivy.metrics import dp
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivymd.toast import toast
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.button import MDIconButton
from kivymd.uix.label import MDLabel
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.textfield import MDTextField

from function.cmn_app_state import get_app_state
from function.cmn_resources import get_text

from .base import BaseManagedScreen


class MatchSetupScreen(BaseManagedScreen):
    screen_mode = "normal"

    def __init__(self, **kwargs):
        self.screen_mode = getattr(self.__class__, "screen_mode", "normal")
        super().__init__(**kwargs)
        self.selected_deck: str | None = None
        self.deck_menu: MDDropdownMenu | None = None

        self.match_count_field = MDTextField(
            hint_text=get_text("match_setup.count_hint"),
            input_filter="int",
            text="0",
        )
        self.deck_button = MDRaisedButton(
            text=get_text("match_setup.deck_button_default"),
            on_press=lambda *_: self.open_deck_menu(),
        )

        (
            self.normal_root,
            content_anchor,
            self.normal_action_anchor,
        ) = self._create_scaffold(
            get_text("match_setup.header_title"),
            lambda: self.change_screen("menu"),
            lambda: self.change_screen("menu"),
        )

        self.count_label = MDLabel(
            text=get_text("match_setup.count_label"),
            font_style="Subtitle1",
        )
        self.deck_label = MDLabel(
            text=get_text("match_setup.deck_label"),
            font_style="Subtitle1",
        )

        self.match_count_field.size_hint = (1, None)
        self.match_count_field.height = dp(72)
        self.deck_button.size_hint = (1, None)
        self.deck_button.height = dp(48)

        self.normal_content_box = MDBoxLayout(
            orientation="vertical",
            spacing=dp(16),
            padding=(dp(24), dp(24), dp(24), dp(24)),
            size_hint=(0.95, 0.95),
        )
        self.normal_content_box.add_widget(self.count_label)
        self.normal_content_box.add_widget(self.match_count_field)
        self.normal_content_box.add_widget(self.deck_label)
        self.normal_content_box.add_widget(self.deck_button)
        content_anchor.add_widget(self.normal_content_box)

        self.start_button = MDRaisedButton(
            text=get_text("match_setup.start_button"),
            on_press=lambda *_: self.start_entry(),
        )
        self.start_button.size_hint = (None, None)
        self.start_button.height = dp(48)
        self.start_button.width = dp(220)
        self.normal_action_anchor.add_widget(self.start_button)

        self.broadcast_layout = self._build_broadcast_layout()

    def on_pre_enter(self):
        self.selected_deck = None
        self.deck_button.text = get_text("match_setup.deck_button_default")

        app = get_app_state()
        mode = self.screen_mode or getattr(app, "ui_mode", "normal")
        self._apply_mode_layout(mode)
        self._sync_window_size(mode)

    def open_deck_menu(self):
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

        self.deck_menu = MDDropdownMenu(caller=self.deck_button, items=menu_items, width_mult=4)
        self.deck_menu.open()

    def set_selected_deck(self, name: str):
        self.selected_deck = name
        self.deck_button.text = get_text("match_setup.selected_deck_label").format(
            deck_name=name
        )
        app = get_app_state()
        db = getattr(app, "db", None)
        if db is not None:
            next_no = db.get_next_match_number(name)
            self.match_count_field.text = str(next_no)
        if self.deck_menu:
            self.deck_menu.dismiss()

    def start_entry(self):
        if not self.selected_deck:
            toast(get_text("match_setup.toast_select_deck"))
            return

        try:
            initial_count = int(self.match_count_field.text or 0)
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

    def _build_broadcast_layout(self) -> MDBoxLayout:
        layout = MDBoxLayout(
            orientation="horizontal",
            spacing=dp(12),
            padding=(dp(12), dp(12), dp(12), dp(12)),
        )

        nav_section = MDBoxLayout(
            orientation="vertical",
            spacing=dp(12),
            size_hint_x=1,
        )
        for icon, callback in (
            ("home", lambda *_: self.change_screen("menu")),
            ("arrow-left", lambda *_: self.change_screen("menu")),
        ):
            button = MDIconButton(icon=icon, on_release=callback)
            button.theme_text_color = "Custom"
            button.text_color = (0.18, 0.36, 0.58, 1)
            button.size_hint = (None, None)
            button.height = dp(48)
            button.width = dp(48)
            nav_section.add_widget(button)
        layout.add_widget(nav_section)

        self.broadcast_form_section = MDBoxLayout(
            orientation="vertical",
            spacing=dp(12),
            size_hint_x=5,
            padding=(dp(12), dp(12), dp(12), dp(12)),
        )
        layout.add_widget(self.broadcast_form_section)

        self.broadcast_actions_section = MDBoxLayout(
            orientation="vertical",
            spacing=dp(12),
            size_hint_x=2,
        )
        layout.add_widget(self.broadcast_actions_section)

        return layout

    @staticmethod
    def _remove_from_parent(widget: Widget):
        parent = widget.parent
        if parent is not None:
            parent.remove_widget(widget)

    def _apply_mode_layout(self, mode: str) -> None:
        if mode == "broadcast":
            self._show_broadcast_layout()
        else:
            self._show_normal_layout()

    def _show_broadcast_layout(self) -> None:
        if self.normal_root.parent:
            self.remove_widget(self.normal_root)
        if not self.broadcast_layout.parent:
            self.add_widget(self.broadcast_layout)

        self.broadcast_form_section.clear_widgets()
        for widget in (
            self.count_label,
            self.match_count_field,
            self.deck_label,
            self.deck_button,
        ):
            self._remove_from_parent(widget)
            self.broadcast_form_section.add_widget(widget)

        self.broadcast_actions_section.clear_widgets()
        self._remove_from_parent(self.start_button)
        self.start_button.size_hint = (1, None)
        self.start_button.width = dp(180)
        self.broadcast_actions_section.add_widget(self.start_button)

    def _show_normal_layout(self) -> None:
        if self.broadcast_layout.parent:
            self.remove_widget(self.broadcast_layout)
        if not self.normal_root.parent:
            self.add_widget(self.normal_root)

        for widget in (
            self.count_label,
            self.match_count_field,
            self.deck_label,
            self.deck_button,
        ):
            self._remove_from_parent(widget)
            if widget not in self.normal_content_box.children:
                self.normal_content_box.add_widget(widget)

        self._remove_from_parent(self.start_button)
        self.start_button.size_hint = (None, None)
        self.start_button.width = dp(220)
        if self.start_button not in self.normal_action_anchor.children:
            self.normal_action_anchor.add_widget(self.start_button)

    def on_leave(self):
        app = get_app_state()
        if self.screen_mode != "broadcast":
            default_size = getattr(app, "default_window_size", None)
            if default_size:
                Window.size = default_size


class MatchSetupBroadcastScreen(MatchSetupScreen):
    screen_mode = "broadcast"


__all__ = ["MatchSetupScreen", "MatchSetupBroadcastScreen"]
