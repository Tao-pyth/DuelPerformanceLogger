"""Season list screen."""

from __future__ import annotations

from datetime import datetime

from functools import partial

from kivy.properties import BooleanProperty, ListProperty

from function import DatabaseError
from function.cmn_app_state import get_app_state
from function.cmn_logger import log_db_error
from function.cmn_resources import get_text
# 共通通知ヘルパーでトースト呼び出しを集約。
from function.core.ui_notify import notify

from .base import BaseManagedScreen
from .season_registration_screen import parse_schedule_datetime, days_until


class SeasonListScreen(BaseManagedScreen):
    """登録済みシーズンを一覧表示し、削除を行う画面。"""

    season_items = ListProperty([])
    has_seasons = BooleanProperty(False)

    def on_pre_enter(self):
        # 画面に入るたびに最新データへ更新。
        self.update_season_list()

    def update_season_list(self):
        """データベースから最新のシーズン一覧を取得し UI へ反映。"""

        app = get_app_state()
        db = getattr(app, "db", None)
        if db is not None:
            app.seasons = db.fetch_seasons()
        items = []
        for season in app.seasons:
            items.append(
                {
                    "season_name": season["name"],
                    "remaining_text": self._get_remaining_text(season),
                    "on_delete": partial(self.delete_season, season["name"]),
                }
            )

        self.season_items = items
        self.has_seasons = bool(items)

    def _get_remaining_text(self, season: dict[str, object]) -> str:
        """シーズン終了までの日数に応じたメッセージを返す。"""

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
        """指定シーズンを削除し、一覧を更新する。"""

        app = get_app_state()
        db = getattr(app, "db", None)
        if db is None:
            notify(get_text("common.db_error"))
            return

        try:
            db.delete_season(name)
        except DatabaseError as exc:
            log_db_error("Failed to delete season", exc, name=name)
            notify(get_text("common.db_error"))
            return

        app.seasons = db.fetch_seasons()
        notify(get_text("season_registration.toast_deleted"))
        self.update_season_list()


__all__ = ["SeasonListScreen"]
