"""Utility helpers exposed at the package level."""

# NOTE: `function` パッケージ外から頻繁に利用されるヘルパーを再エクスポート
# しています。`from function import DatabaseManager` のように短く書けるため、
# 画面ロジックからの import をシンプルに保てます。

"""Convenience exports for commonly used helpers."""

from .cmn_database import DatabaseManager, DatabaseError, DuplicateEntryError
from .cmn_app_state import get_app_state

__all__ = [
    "DatabaseManager",
    "DatabaseError",
    "DuplicateEntryError",
    "get_app_state",
]
