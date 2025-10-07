"""Deck registration screen."""

from __future__ import annotations

from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivymd.toast import toast
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.button import MDIconButton  
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField

from function import DatabaseError, DuplicateEntryError
from function.cmn_app_state import get_app_state
from function.cmn_logger import log_db_error
from function.cmn_resources import get_text

from .base import BaseManagedScreen


class DeckRegistrationScreen(BaseManagedScreen):
    """デッキ登録画面."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.name_field = MDTextField(
            hint_text=get_text("deck_registration.name_hint"),
            helper_text=get_text("common.required_helper"),
            helper_text_mode="on_focus",
        )
        self.description_field = MDTextField(
            hint_text=get_text("deck_registration.description_hint"),
            multiline=True,
            max_text_length=200,
        )
        self.deck_empty_label = MDLabel(
            text=get_text("deck_registration.empty_message"),
            theme_text_color="Hint",
            size_hint_y=None,
            height=dp(24),
        )
        self.deck_list_container = MDBoxLayout(
            orientation="vertical",
            spacing=dp(8),
            padding=(0, 0, 0, dp(8)),
            size_hint_y=None,
        )
        self.deck_list_container.bind(minimum_height=self.deck_list_container.setter("height"))
        self.deck_scroll = ScrollView(size_hint=(1, 1))
        self.deck_scroll.add_widget(self.deck_list_container)

        self.root_layout, content_anchor, action_anchor = self._create_scaffold(
            get_text("deck_registration.header_title"),
            lambda: self.change_screen("menu"),
            lambda: self.change_screen("menu"),
        )

        content_box = MDBoxLayout(
            orientation="vertical",
            spacing=dp(16),
            padding=(dp(24), dp(24), dp(24), dp(24)),
            size_hint=(0.95, 0.95),
        )
        content_box.add_widget(self.name_field)
        content_box.add_widget(self.description_field)
        content_box.add_widget(self.deck_empty_label)
        content_box.add_widget(self.deck_scroll)
        content_anchor.add_widget(content_box)

        register_button = MDRaisedButton(
            text=get_text("common.register"),
            on_press=lambda *_: self.register_deck(),
        )
        register_button.size_hint = (None, None)
        register_button.height = dp(48)
        register_button.width = dp(220)
        action_anchor.add_widget(register_button)

    def register_deck(self):
        name = self.name_field.text.strip()
        description = self.description_field.text.strip()

        if not name:
            toast(get_text("deck_registration.toast_missing_name"))
            return

        app = get_app_state()
        db = getattr(app, "db", None)

        if db is None:
            toast(get_text("common.db_error"))
            return

        try:
            db.add_deck(name, description)
        except DuplicateEntryError:
            toast(get_text("deck_registration.toast_duplicate"))
            return
        except DatabaseError as exc:
            log_db_error("Failed to add deck", exc, name=name)
            toast(get_text("common.db_error"))
            return

        app.decks = db.fetch_decks()
        toast(get_text("deck_registration.toast_registered"))
        self.name_field.text = ""
        self.description_field.text = ""
        self.update_deck_list()

    def on_pre_enter(self):
        self.update_deck_list()

    def update_deck_list(self):
        app = get_app_state()
        db = getattr(app, "db", None)
        if db is not None:
            app.decks = db.fetch_decks()
        self.deck_list_container.clear_widgets()

        if not app.decks:
            self.deck_empty_label.height = dp(24)
            self.deck_empty_label.opacity = 1
            self.deck_scroll.opacity = 0
            self.deck_scroll.size_hint_y = None
            self.deck_scroll.height = dp(0)
        else:
            self.deck_empty_label.height = dp(0)
            self.deck_empty_label.opacity = 0
            self.deck_scroll.opacity = 1
            self.deck_scroll.size_hint_y = 1
            for deck in app.decks:
                self.deck_list_container.add_widget(self._create_deck_card(deck))

    def _create_deck_card(self, deck: dict[str, str]):
        fallback_description = get_text("common.no_description")
        card = MDCard(
            orientation="horizontal",
            padding=(dp(16), dp(12), dp(12), dp(12)),
            size_hint=(1, None),
            height=dp(84),
            radius=[16, 16, 16, 16],
        )

        text_box = MDBoxLayout(orientation="vertical", spacing=dp(4))
        text_box.add_widget(
            MDLabel(text=deck["name"], font_style="Subtitle1", shorten=True)
        )
        text_box.add_widget(
            MDLabel(
                text=deck["description"] or fallback_description,
                theme_text_color="Secondary",
                shorten=True,
            )
        )

        card.add_widget(text_box)
        card.add_widget(Widget())

        delete_button = MDIconButton(
            icon="delete", on_release=lambda *_: self.delete_deck(deck["name"])
        )
        delete_button.theme_text_color = "Custom"
        delete_button.text_color = (0.86, 0.16, 0.16, 1)
        card.add_widget(delete_button)

        return card

    def delete_deck(self, name: str):
        app = get_app_state()
        db = getattr(app, "db", None)
        if db is None:
            toast(get_text("common.db_error"))
            return

        try:
            db.delete_deck(name)
        except DatabaseError as exc:
            log_db_error("Failed to delete deck", exc, name=name)
            toast(get_text("common.db_error"))
            return

        app.decks = db.fetch_decks()
        toast(get_text("deck_registration.toast_deleted"))
        self.update_deck_list()


__all__ = ["DeckRegistrationScreen"]
