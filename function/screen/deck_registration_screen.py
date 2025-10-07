"""Deck registration screen."""

from __future__ import annotations

from functools import partial

from kivy.properties import BooleanProperty, ListProperty
from kivymd.toast import toast

from function import DatabaseError, DuplicateEntryError
from function.cmn_app_state import get_app_state
from function.cmn_logger import log_db_error
from function.cmn_resources import get_text

from .base import BaseManagedScreen


class DeckRegistrationScreen(BaseManagedScreen):
    """デッキ登録画面."""

    deck_items = ListProperty([])
    has_decks = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def register_deck(self):
        """フォームの内容を検証し、デッキを DB へ登録する。"""

        name = self.ids.name_field.text.strip()
        description = self.ids.description_field.text.strip()

        # 必須項目チェック。空の場合はトーストでユーザーへ通知して処理終了。
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
            # 一意制約に引っかかった場合は重複メッセージを表示。
            toast(get_text("deck_registration.toast_duplicate"))
            return
        except DatabaseError as exc:
            # 予期せぬ DB エラーはログに残し、汎用エラーメッセージを表示。
            log_db_error("Failed to add deck", exc, name=name)
            toast(get_text("common.db_error"))
            return

        # DB への反映が成功したらアプリ状態を更新し、フォームをクリア。
        app.decks = db.fetch_decks()
        toast(get_text("deck_registration.toast_registered"))
        self.ids.name_field.text = ""
        self.ids.description_field.text = ""
        self.update_deck_list()

    def on_pre_enter(self):
        # 画面表示前に常に一覧を最新化する。
        self.update_deck_list()

    def update_deck_list(self):
        """登録済みデッキ一覧を UI に反映する。"""

        app = get_app_state()
        db = getattr(app, "db", None)
        if db is not None:
            app.decks = db.fetch_decks()
        fallback_description = get_text("common.no_description")
        items = []
        for deck in app.decks:
            items.append(
                {
                    "deck_name": deck["name"],
                    "description": deck["description"] or fallback_description,
                    "on_delete": partial(self.delete_deck, deck["name"]),
                }
            )

        self.deck_items = items
        self.has_decks = bool(items)

    def delete_deck(self, name: str):
        """指定されたデッキを削除し、一覧を更新する。"""

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
