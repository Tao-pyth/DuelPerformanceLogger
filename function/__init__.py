"""function パッケージで共通利用されるヘルパー群。

このモジュールは、アプリ全体で頻繁に利用するクラスや関数を再エクスポートします。
画面ロジックなどから ``from function import DatabaseManager`` のように簡潔に
インポートできるようにすることが目的です。

戻り値
    モジュール読み込み時に副作用として ``__all__`` が設定され、公開 API が
    整理されます。
"""

from .cmn_database import DatabaseManager, DatabaseError, DuplicateEntryError
from .cmn_app_state import get_app_state

__all__ = [
    "DatabaseManager",
    "DatabaseError",
    "DuplicateEntryError",
    "get_app_state",
]
