"""Season registration screen and related utilities."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Optional

from kivy.properties import StringProperty

from app.function import DatabaseError, DuplicateEntryError
from app.function.cmn_app_state import get_app_state
from app.function.cmn_logger import log_db_error
from app.function.cmn_resources import get_text
# 共通通知処理でプラットフォーム差異に対応。
from app.function.core.ui_notify import notify

from .base import BaseManagedScreen


def parse_schedule_datetime(date_text: str | None, time_text: str | None) -> Optional[datetime]:
    """日付文字列と時刻文字列から `datetime` を生成するユーティリティ。"""

    if not date_text:
        return None
    try:
        if time_text:
            return datetime.strptime(f"{date_text} {time_text}", "%Y-%m-%d %H:%M")
        return datetime.strptime(date_text, "%Y-%m-%d")
    except ValueError:
        return None


def days_until(target: datetime) -> int:
    """現在から指定日時までの残日数を整数で返す。"""

    delta = target - datetime.now()
    if delta.total_seconds() <= 0:
        return 0
    return math.ceil(delta.total_seconds() / 86400)


class SeasonRegistrationScreen(BaseManagedScreen):
    """シーズン情報を新規登録するフォーム画面。"""

    name_text = StringProperty("")
    description_text = StringProperty("")
    start_date_text = StringProperty("")
    start_time_text = StringProperty("")
    end_date_text = StringProperty("")
    end_time_text = StringProperty("")

    def on_kv_post(self, base_widget):
        super().on_kv_post(base_widget)
        self.reset_form()

    def register_season(self):
        """フォーム内容を検証し、シーズンをデータベースへ保存する。"""

        name = self.ids.name_field.text.strip()
        description = self.ids.description_field.text.strip()

        if not name:
            notify(get_text("season_registration.toast_missing_name"))
            return

        app = get_app_state()
        db = getattr(app, "db", None)
        if db is None:
            notify(get_text("common.db_error"))
            return

        start_date = self.ids.start_date_field.text.strip() or None
        start_time = self.ids.start_time_field.text.strip() or None
        end_date = self.ids.end_date_field.text.strip() or None
        end_time = self.ids.end_time_field.text.strip() or None

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
            notify(get_text("season_registration.toast_duplicate"))
            return
        except DatabaseError as exc:
            log_db_error("Failed to add season", exc, name=name)
            notify(get_text("common.db_error"))
            return

        app.seasons = db.fetch_seasons()
        notify(get_text("season_registration.toast_registered"))
        self.reset_form()
        self.change_screen("season_list")

    def reset_form(self):
        """入力内容を初期化し、次の登録に備える。"""

        self.ids.name_field.text = ""
        self.ids.description_field.text = ""
        self.ids.start_date_field.text = ""
        self.ids.start_time_field.text = ""
        self.ids.end_date_field.text = ""
        self.ids.end_time_field.text = ""

        self.name_text = ""
        self.description_text = ""
        self.start_date_text = ""
        self.start_time_text = ""
        self.end_date_text = ""
        self.end_time_text = ""


__all__ = [
    "SeasonRegistrationScreen",
    "parse_schedule_datetime",
    "days_until",
]
