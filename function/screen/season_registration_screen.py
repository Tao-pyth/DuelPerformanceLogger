"""Season registration screen and related utilities."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Optional

from kivy.metrics import dp
from kivymd.toast import toast
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField

from function import DatabaseError, DuplicateEntryError
from function.cmn_app_state import get_app_state
from function.cmn_logger import log_db_error
from function.cmn_resources import get_text

from .base import BaseManagedScreen


def parse_schedule_datetime(date_text: str | None, time_text: str | None) -> Optional[datetime]:
    if not date_text:
        return None
    try:
        if time_text:
            return datetime.strptime(f"{date_text} {time_text}", "%Y-%m-%d %H:%M")
        return datetime.strptime(date_text, "%Y-%m-%d")
    except ValueError:
        return None


def days_until(target: datetime) -> int:
    delta = target - datetime.now()
    if delta.total_seconds() <= 0:
        return 0
    return math.ceil(delta.total_seconds() / 86400)


class SeasonRegistrationScreen(BaseManagedScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.name_field = MDTextField(
            hint_text=get_text("season_registration.name_hint"),
            helper_text=get_text("common.required_helper"),
            helper_text_mode="on_focus",
        )
        self.description_field = MDTextField(
            hint_text=get_text("season_registration.description_hint"),
            multiline=True,
            max_text_length=200,
        )
        self.start_date_field = MDTextField(
            hint_text=get_text("season_registration.start_date_hint"),
        )
        self.start_time_field = MDTextField(
            hint_text=get_text("season_registration.start_time_hint"),
        )
        self.end_date_field = MDTextField(
            hint_text=get_text("season_registration.end_date_hint"),
        )
        self.end_time_field = MDTextField(
            hint_text=get_text("season_registration.end_time_hint"),
        )
        (
            self.root_layout,
            content_anchor,
            action_anchor,
        ) = self._create_scaffold(
            get_text("season_registration.header_title"),
            lambda: self.change_screen("season_list"),
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
        content_box.add_widget(
            MDLabel(
                text=get_text("season_registration.schedule_section_title"),
                theme_text_color="Secondary",
            )
        )

        schedule_box = MDBoxLayout(orientation="vertical", spacing=dp(12))

        start_row = MDBoxLayout(spacing=dp(12), size_hint_y=None, height=dp(72))
        for field in (self.start_date_field, self.start_time_field):
            field.size_hint = (1, None)
            field.height = dp(72)
            start_row.add_widget(field)
        schedule_box.add_widget(start_row)

        end_row = MDBoxLayout(spacing=dp(12), size_hint_y=None, height=dp(72))
        for field in (self.end_date_field, self.end_time_field):
            field.size_hint = (1, None)
            field.height = dp(72)
            end_row.add_widget(field)
        schedule_box.add_widget(end_row)

        content_box.add_widget(schedule_box)
        content_anchor.add_widget(content_box)

        actions = MDBoxLayout(
            orientation="horizontal",
            spacing=dp(16),
            size_hint=(0.6, None),
            height=dp(48),
        )
        register_button = MDRaisedButton(
            text=get_text("common.register"),
            on_press=lambda *_: self.register_season(),
        )
        register_button.size_hint = (1, None)
        register_button.height = dp(48)
        back_button = MDFlatButton(
            text=get_text("season_registration.back_to_list"),
            on_press=lambda *_: self.change_screen("season_list"),
        )
        back_button.size_hint = (1, None)
        back_button.height = dp(48)
        actions.add_widget(back_button)
        actions.add_widget(register_button)
        action_anchor.add_widget(actions)
        self.reset_form()

    def register_season(self):
        name = self.name_field.text.strip()
        description = self.description_field.text.strip()

        if not name:
            toast(get_text("season_registration.toast_missing_name"))
            return

        app = get_app_state()
        db = getattr(app, "db", None)
        if db is None:
            toast(get_text("common.db_error"))
            return

        start_date = self.start_date_field.text.strip() or None
        start_time = self.start_time_field.text.strip() or None
        end_date = self.end_date_field.text.strip() or None
        end_time = self.end_time_field.text.strip() or None

        try:
            db.add_season(
                name,
                description,
                start_date=start_date,
                start_time=start_time,
                end_date=end_date,
                end_time=end_time,
            )
        except DuplicateEntryError:
            toast(get_text("season_registration.toast_duplicate"))
            return
        except DatabaseError as exc:
            log_db_error("Failed to add season", exc, name=name)
            toast(get_text("common.db_error"))
            return

        app.seasons = db.fetch_seasons()
        toast(get_text("season_registration.toast_registered"))
        self.reset_form()
        self.change_screen("season_list")

    def reset_form(self):
        self.name_field.text = ""
        self.description_field.text = ""
        self.start_date_field.text = ""
        self.start_time_field.text = ""
        self.end_date_field.text = ""
        self.end_time_field.text = ""


__all__ = [
    "SeasonRegistrationScreen",
    "parse_schedule_datetime",
    "days_until",
]
