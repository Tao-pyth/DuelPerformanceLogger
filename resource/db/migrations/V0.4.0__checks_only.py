"""v0.4.0 への移行で整合性チェックのみを実行するマイグレーション。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - 型チェック専用
    from app.function.cmn_database import DatabaseManager


def run(db: "DatabaseManager") -> None:
    """SQLite の健全性を確認し、スキーマ版数を 0.4.0 に更新します。"""

    with db.transaction() as connection:
        result = connection.execute("PRAGMA integrity_check").fetchone()
        if not result or result[0] != "ok":
            raise RuntimeError("PRAGMA integrity_check が失敗しました")

        connection.execute("SELECT 1")
        connection.execute(
            "INSERT OR REPLACE INTO db_metadata (key, value) VALUES (?, ?)",
            ("schema_version", "0.4.0"),
        )
