"""Season list screen."""

from __future__ import annotations

from datetime import datetime

from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivymd.toast import toast
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.iconbutton import MDIconButton
from kivymd.uix.label import MDLabel

from function import DatabaseError
from function.cmn_app_state import get_app_state
from function.cmn_logger import log_db_error
from function.cmn_resources import get_text

from .base import BaseManagedScreen
from .season_registration_screen import parse_schedule_datetime, days_until


class SeasonListScreen(BaseManagedScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.season_empty_label = MDLabel(
            text=get_text("season_registration.empty_message"),
            theme_text_color="Hint",
            size_hint_y=None,
            height=dp(24),
        )
        self.season_list_container = MDBoxLayout(
            orientation="vertical",
            spacing=dp(8),
            padding=(0, 0, 0, dp(8)),
            size_hint_y=None,
        )
        self.season_list_container.bind(
            minimum_height=self.season_list_container.setter("height")
        )
        self.season_scroll = ScrollView(size_hint=(0.95, 0.95))
        self.season_scroll.add_widget(self.season_list_container)

        (
            self.root_layout,
            content_anchor,
            action_anchor,
        ) = self._create_scaffold(
            get_text("season_registration.list_header_title"),
            lambda: self.change_screen("menu"),
            lambda: self.change_screen("menu"),
            action_anchor_x="right",
        )

        content_box = MDBoxLayout(
            orientation="vertical",
            spacing=dp(16),
            padding=(dp(24), dp(24), dp(24), dp(24)),
            size_hint=(0.95, 0.95),
        )
        content_box.add_widget(self.season_empty_label)
        content_box.add_widget(self.season_scroll)
        content_anchor.add_widget(content_box)

        add_button = MDRaisedButton(
            text=get_text("season_registration.add_button"),
            on_press=lambda *_: self.change_screen("season_register"),
        )
        add_button.size_hint = (None, None)
        add_button.height = dp(48)
        add_button.width = dp(260)
        action_anchor.add_widget(add_button)

    def on_pre_enter(self):
        self.update_season_list()

    def update_season_list(self):
        app = get_app_state()
        db = getattr(app, "db", None)
        if db is not None:
            app.seasons = db.fetch_seasons()
        self.season_list_container.clear_widgets()

        if not app.seasons:
            self.season_empty_label.height = dp(24)
            self.season_empty_label.opacity = 1
            self.season_scroll.opacity = 0
            self.season_scroll.size_hint_y = None
            self.season_scroll.height = dp(0)
        else:
            self.season_empty_label.height = dp(0)
            self.season_empty_label.opacity = 0
            self.season_scroll.opacity = 1
            self.season_scroll.size_hint_y = 1
            self.season_scroll.height = 0
            for season in app.seasons:
                self.season_list_container.add_widget(
                    self._create_season_card(season)
                )

    def _create_season_card(self, season: dict[str, object]):
        card = MDCard(
            orientation="horizontal",
            padding=(dp(16), dp(12), dp(12), dp(12)),
            size_hint=(1, None),
            height=dp(72),
            radius=[16, 16, 16, 16],
        )
        card.spacing = dp(12)

        name_label = MDLabel(
            text=season["name"],
            font_style="Subtitle1",
            shorten=True,
        )
        name_label.size_hint_x = 0.55
        card.add_widget(name_label)

        remaining_label = MDLabel(
            text=self._get_remaining_text(season),
            theme_text_color="Secondary",
            halign="center",
            shorten=True,
        )
        remaining_label.size_hint_x = 0.35
        card.add_widget(remaining_label)

        delete_button = MDIconButton(
            icon="delete", on_release=lambda *_: self.delete_season(season["name"])
        )
        delete_button.theme_text_color = "Custom"
        delete_button.text_color = (0.86, 0.16, 0.16, 1)
        delete_button.size_hint = (None, None)
        delete_button.height = dp(48)
        card.add_widget(delete_button)

        return card

    def _get_remaining_text(self, season: dict[str, object]) -> str:
        end_date = season.get("end_date") or ""
        end_time = season.get("end_time") or ""
        end_dt = parse_schedule_datetime(end_date, end_time)

        if not end_dt:
            return get_text("season_registration.schedule_no_end")

        if end_dt <= datetime.now():
            return get_text("season_registration.schedule_finished")

        days = days_until(end_dt)
        return get_text("season_registration.schedule_ends_in").format(days=days)

    def delete_season(self, name: str):
        app = get_app_state()
        db = getattr(app, "db", None)
        if db is None:
            toast(get_text("common.db_error"))
            return

        try:
            db.delete_season(name)
        except DatabaseError as exc:
            log_db_error("Failed to delete season", exc, name=name)
            toast(get_text("common.db_error"))
            return

        app.seasons = db.fetch_seasons()
        toast(get_text("season_registration.toast_deleted"))
        self.update_season_list()


__all__ = ["SeasonListScreen"]
