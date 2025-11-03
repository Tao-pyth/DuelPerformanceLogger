"""v0.3.3 への移行で整合性チェックのみを実行するマイグレーション。"""

from __future__ import annotations

from typing import Iterable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - 型チェック専用
    from app.function.cmn_database import DatabaseManager


REQUIRED_TABLES: dict[str, Iterable[str]] = {
    "decks": ("name", "usage_count"),
    "seasons": ("name", "rank_statistics_target"),
    "matches": ("deck_id", "memo", "youtube_url"),
    "keywords": ("identifier", "is_protected", "is_hidden"),
    "recordings": ("match_id", "file_path", "status"),
}


def _has_column(connection, table: str, column: str) -> bool:
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)


def run(db: "DatabaseManager") -> None:
    """SQLite の整合性と必須スキーマの存在を検証し、スキーマ版数を 0.3.3 へ更新します。"""

    with db.transaction() as connection:
        result = connection.execute("PRAGMA integrity_check").fetchone()
        if not result or result[0] != "ok":
            raise RuntimeError("PRAGMA integrity_check が失敗しました")

        existing_tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        missing_tables = [name for name in REQUIRED_TABLES if name not in existing_tables]
        if missing_tables:
            raise RuntimeError(
                "必須テーブルが不足しています: " + ", ".join(sorted(missing_tables))
            )

        for table, columns in REQUIRED_TABLES.items():
            for column in columns:
                if not _has_column(connection, table, column):
                    raise RuntimeError(f"{table}.{column} カラムが存在しません")

        connection.execute(
            "INSERT OR REPLACE INTO db_metadata (key, value) VALUES (?, ?)",
            ("schema_version", "0.3.3"),
        )
