"""``app.function`` パッケージで共通利用されるヘルパー群。

このモジュールは、アプリ全体で頻繁に利用するクラスや関数を再エクスポートします。
画面ロジックなどから ``from app.function import DatabaseManager`` のように簡潔に
インポートできるようにすることが目的です。

戻り値
    モジュール読み込み時に副作用として ``__all__`` が設定され、公開 API が
    整理されます。
"""

from .cmn_app_state import (
    AppState,
    build_state,
    get_app_state,
    reset_app_state,
    set_app_state,
)
from .cmn_database import DatabaseManager, DatabaseError, DuplicateEntryError

__all__ = [
    "AppState",
    "DatabaseManager",
    "DatabaseError",
    "DuplicateEntryError",
    "build_state",
    "get_app_state",
    "reset_app_state",
    "set_app_state",
]
