"""SQLite データベース管理モジュール（DuelPerformanceLogger 用）

このモジュールは、アプリで利用する SQLite データベースへのアクセスを一元化します。
UI 層では辞書（dict）ベースのデータ構造だけを扱えるよう抽象化し、
永続化の詳細（SQL・Row など）を極力意識せずに使える設計としています。

主な保管対象:
- デッキ情報（`decks`）
- シーズン情報（`seasons`）
- 対戦ログ（`matches`）

設計のポイント:
- 外部キー制約を常時有効化（`PRAGMA foreign_keys = ON`）。
- 取得結果は `sqlite3.Row` → dict 化して返却。
- キーワードは JSON 文字列で保存し、取得時に Python のリストへ復元。
- タイムスタンプは **UNIX エポック秒（INTEGER）** を保存し、表示時に ISO 文字列へ変換。
- 最低限の **CHECK 制約**（`turn`, `result`）と **INDEX**（検索高速化）を付与。
- トランザクション・コンテキストマネージャを提供。
"""

from __future__ import annotations

import csv
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Optional


class DatabaseError(RuntimeError):
    """DB 操作時の想定外エラーを表す基底例外。"""


class DuplicateEntryError(DatabaseError):
    """一意制約違反（同名レコードの重複登録など）を表す例外。"""


class DatabaseManager:
    """アプリ用 SQLite データベースのユーティリティラッパー。

    Parameters
    ----------
    db_path: Optional[Path | str]
        データベースファイルのパス。未指定時は ``resource/db/duel_performance.sqlite3`` を使用。
        ディレクトリを渡した場合は、その直下に既定名で作成します。
    """

    CURRENT_SCHEMA_VERSION = 2

    def __init__(self, db_path: Optional[Path | str] = None) -> None:
        # プロジェクトルートからの相対で DB 既定置き場を解決
        base_dir = Path(__file__).resolve().parent.parent / "resource" / "db"
        if db_path is None:
            db_path = base_dir / "duel_performance.sqlite3"
        else:
            db_path = Path(db_path)
            if db_path.is_dir():
                # ディレクトリだけ渡された時は既定ファイル名を付与
                db_path = db_path / "duel_performance.sqlite3"

        self._db_path = db_path
        # 保存先ディレクトリを事前に作成（既にあれば何もしない）
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 低レベルヘルパー（接続生成）
    # ------------------------------------------------------------------
    def _connect(self) -> sqlite3.Connection:
        """SQLite コネクションを生成して返します。

        - 行ファクトリを `sqlite3.Row` に設定（列名アクセスを可能に）
        - 外部キー制約を ON
        - 呼び出し側は基本的に `with` 文で使用してください
        """
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON;")
        return connection

    # ------------------------------------------------------------------
    # DB ライフサイクル管理
    # ------------------------------------------------------------------
    @property
    def db_path(self) -> Path:
        """現在使用している DB ファイルのパス（情報表示用）。"""
        return self._db_path

    def ensure_database(self) -> None:
        """DB ファイルが存在しない、またはメタデータが欠損している場合にスキーマを作成します。"""

        needs_initialization = False

        if not self._db_path.exists():
            needs_initialization = True
        else:
            try:
                with self._connect() as connection:
                    cursor = connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='db_metadata'"
                    )
                    if cursor.fetchone() is None:
                        needs_initialization = True
            except sqlite3.DatabaseError:
                # 何らかの理由で接続やメタデータ取得に失敗した場合も初期化する
                needs_initialization = True

        if needs_initialization:
            self.initialize_database()

    # ------------------------------------------------------------------
    # バージョン管理
    # ------------------------------------------------------------------
    def get_schema_version(self) -> int:
        """保存されているスキーマバージョンを取得する。"""

        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    "SELECT value FROM db_metadata WHERE key = 'schema_version'"
                )
                row = cursor.fetchone()
                if row is None:
                    return 0
                return int(row["value"])
        except (ValueError, sqlite3.DatabaseError):  # pragma: no cover - defensive
            return 0

    def set_schema_version(self, version: int) -> None:
        """スキーマバージョンを更新する。"""

        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO db_metadata (key, value) VALUES (?, ?)",
                ("schema_version", str(int(version))),
            )

    def initialize_database(self) -> None:
        """DB を初期化（既存ファイルを残したままスキーマを再構築）。

        - 何度呼んでも安全（冪等）な設計です。
        - 既存ファイルは削除せず、同一コネクション上で `DROP` → `CREATE` を実行します。
        """

        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self._db_path) as connection:
            cursor = connection.cursor()

            # 既存スキーマを安全に破棄（外部キー制約は一時的に OFF）
            cursor.execute("PRAGMA foreign_keys = OFF;")
            cursor.executescript(
                """
                DROP TABLE IF EXISTS matches;
                DROP TABLE IF EXISTS seasons;
                DROP TABLE IF EXISTS decks;
                DROP TABLE IF EXISTS db_metadata;
                """
            )

            cursor.execute("PRAGMA foreign_keys = ON;")
            cursor.executescript(
                """
                CREATE TABLE db_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE decks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT DEFAULT ''
                );

                CREATE TABLE seasons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT DEFAULT '',
                    start_date TEXT,
                    start_time TEXT,
                    end_date TEXT,
                    end_time TEXT
                );

                CREATE TABLE matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_no INTEGER NOT NULL,
                    deck_name TEXT NOT NULL,
                    turn TEXT NOT NULL CHECK (turn IN ('first', 'second')),
                    opponent_deck TEXT,
                    keywords TEXT,
                    result TEXT NOT NULL CHECK (result IN ('win', 'lose', 'draw')),
                    -- 生成時刻は UTC のエポック秒
                    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
                );

                -- 検索高速化：デッキ×作成時刻の複合インデックス
                CREATE INDEX idx_matches_deck_created_at
                    ON matches(deck_name, created_at DESC);

                -- 対戦番号へのインデックス
                CREATE INDEX idx_matches_match_no
                    ON matches(match_no);
                """
            )

            cursor.execute(
                "INSERT OR REPLACE INTO db_metadata (key, value) VALUES (?, ?)",
                ("schema_version", str(self.CURRENT_SCHEMA_VERSION)),
            )

    # ------------------------------------------------------------------
    # バックアップユーティリティ
    # ------------------------------------------------------------------
    def export_backup(self, destination: Optional[Path | str] = None) -> Path:
        """現在の DB 内容を CSV として保存し、作成先パスを返す。"""

        if destination is None:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            destination = (
                Path(__file__).resolve().parent.parent
                / "resource"
                / "theme"
                / "backups"
                / timestamp
            )
        else:
            destination = Path(destination)

        destination.mkdir(parents=True, exist_ok=True)

        with self._connect() as connection:
            tables = ("decks", "seasons", "matches")
            for table in tables:
                cursor = connection.execute(f"SELECT * FROM {table}")
                columns = [col[0] for col in cursor.description]
                file_path = destination / f"{table}.csv"
                with file_path.open("w", encoding="utf-8", newline="") as stream:
                    writer = csv.writer(stream)
                    writer.writerow(columns)
                    for row in cursor.fetchall():
                        writer.writerow([row[col] for col in columns])

        return destination

    def import_backup(self, source: Path | str) -> dict[str, int]:
        """CSV バックアップからデータを読み込み復元する。"""

        source_path = Path(source)
        if not source_path.exists():
            raise DatabaseError(f"Backup source '{source}' not found")

        restored: dict[str, int] = {}

        with self.transaction() as connection:
            for table in ("decks", "seasons", "matches"):
                file_path = source_path / f"{table}.csv"
                if not file_path.exists():
                    continue

                with file_path.open("r", encoding="utf-8", newline="") as stream:
                    reader = csv.reader(stream)
                    header = next(reader, None)
                    if not header:
                        continue

                    column_info = connection.execute(
                        f"PRAGMA table_info({table})"
                    ).fetchall()
                    valid_columns = [row[1] for row in column_info]
                    insert_columns = [col for col in header if col in valid_columns]
                    if not insert_columns:
                        continue

                    placeholders = ", ".join(["?"] * len(insert_columns))
                    column_list = ", ".join(insert_columns)
                    query = f"INSERT INTO {table} ({column_list}) VALUES ({placeholders})"

                    count = 0
                    for values in reader:
                        row_map = {
                            header[i]: values[i]
                            for i in range(min(len(values), len(header)))
                        }
                        params = [row_map.get(col) for col in insert_columns]
                        connection.execute(query, params)
                        count += 1
                    restored[table] = count

        return restored

    # ------------------------------------------------------------------
    # 取得系ヘルパー
    # ------------------------------------------------------------------
    def fetch_decks(self) -> list[dict[str, str]]:
        """登録済みデッキを名称順（大文字小文字無視）で返却。"""
        with self._connect() as connection:
            cursor = connection.execute(
                "SELECT name, description FROM decks ORDER BY name COLLATE NOCASE"
            )
            return [dict(row) for row in cursor.fetchall()]

    def fetch_seasons(self) -> list[dict[str, object]]:
        """登録済みシーズンを名称順で返却。"""
        with self._connect() as connection:
            cursor = connection.execute(
                """
                SELECT
                    name,
                    description,
                    start_date,
                    start_time,
                    end_date,
                    end_time
                FROM seasons
                ORDER BY name COLLATE NOCASE
                """
            )
            return [dict(row) for row in cursor.fetchall()]

    def fetch_matches(self, deck_name: Optional[str] = None) -> list[dict[str, object]]:
        """対戦ログを返却（デッキ名で絞り込み可能）。

        Parameters
        ----------
        deck_name: Optional[str]
            指定された場合、そのデッキの対戦のみを返します。
        """
        query = (
            "SELECT match_no, deck_name, turn, opponent_deck, keywords, result, created_at"
            " FROM matches"
        )
        params: Iterable[object] = ()
        if deck_name:
            query += " WHERE deck_name = ?"
            params = (deck_name,)

        # 生成時刻の昇順 → 同時刻の場合は id 昇順
        query += " ORDER BY created_at ASC, id ASC"

        with self._connect() as connection:
            cursor = connection.execute(query, tuple(params))
            records: list[dict[str, object]] = []
            for row in cursor.fetchall():
                keywords_raw = row["keywords"]
                keywords = json.loads(keywords_raw) if keywords_raw else []
                created_at = self._format_timestamp(row["created_at"])  # ISO 8601
                records.append(
                    {
                        "match_no": row["match_no"],
                        "deck_name": row["deck_name"],
                        "turn": row["turn"],
                        "opponent_deck": row["opponent_deck"] or "",
                        "keywords": keywords,
                        "result": row["result"],
                        "created_at": created_at,
                    }
                )
            return records

    def fetch_last_match(self, deck_name: Optional[str] = None) -> Optional[dict[str, object]]:
        """最新の対戦ログを 1 件返却（デッキ名で絞り込み可能）。"""
        query = (
            "SELECT match_no, deck_name, turn, opponent_deck, keywords, result, created_at"
            " FROM matches"
        )
        params: Iterable[object] = ()
        if deck_name:
            query += " WHERE deck_name = ?"
            params = (deck_name,)

        # 新しい順に 1 件
        query += " ORDER BY created_at DESC, id DESC LIMIT 1"

        with self._connect() as connection:
            cursor = connection.execute(query, tuple(params))
            row = cursor.fetchone()
            if row is None:
                return None

            keywords_raw = row["keywords"]
            keywords = json.loads(keywords_raw) if keywords_raw else []
            created_at = self._format_timestamp(row["created_at"])  # ISO 8601
            return {
                "match_no": row["match_no"],
                "deck_name": row["deck_name"],
                "turn": row["turn"],
                "opponent_deck": row["opponent_deck"] or "",
                "keywords": keywords,
                "result": row["result"],
                "created_at": created_at,
            }

    def get_next_match_number(self, deck_name: Optional[str] = None) -> int:
        """指定デッキの次の対戦番号を返却。

        直近の `match_no` を見て +1 した値を返します。DB が空の場合は 1。
        数値化に失敗した場合も安全側で 1 を返すフォールバックを実装しています。
        """
        last_match = self.fetch_last_match(deck_name)
        if last_match is None:
            return 1
        last_no = last_match.get("match_no")
        try:
            return int(last_no) + 1
        except (TypeError, ValueError):
            return 1

    # ------------------------------------------------------------------
    # 追加・更新系ヘルパー
    # ------------------------------------------------------------------
    def add_deck(self, name: str, description: str = "") -> None:
        """デッキ定義を追加。重複時は `DuplicateEntryError`。"""
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO decks (name, description) VALUES (?, ?)",
                    (name, description),
                )
        except sqlite3.IntegrityError as exc:  # pragma: no cover - defensive
            raise DuplicateEntryError(f"Deck '{name}' already exists") from exc
        except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive
            raise DatabaseError("Failed to insert deck") from exc

    def add_season(
        self,
        name: str,
        description: str = "",
        *,
        start_date: str | None = None,
        start_time: str | None = None,
        end_date: str | None = None,
        end_time: str | None = None,
    ) -> None:
        """シーズン定義を追加。重複時は `DuplicateEntryError`。"""
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO seasons (
                        name, description, start_date, start_time, end_date, end_time
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (name, description, start_date, start_time, end_date, end_time),
                )
        except sqlite3.IntegrityError as exc:  # pragma: no cover - defensive
            raise DuplicateEntryError(f"Season '{name}' already exists") from exc
        except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive
            raise DatabaseError("Failed to insert season") from exc

    def delete_deck(self, name: str) -> None:
        """デッキ定義を削除。存在しない場合は `DatabaseError` を送出。"""

        try:
            with self._connect() as connection:
                cursor = connection.execute("DELETE FROM decks WHERE name = ?", (name,))
                if cursor.rowcount == 0:
                    raise DatabaseError(f"Deck '{name}' not found")
        except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive
            raise DatabaseError("Failed to delete deck") from exc

    def delete_season(self, name: str) -> None:
        """シーズン定義を削除。存在しない場合は `DatabaseError` を送出。"""

        try:
            with self._connect() as connection:
                cursor = connection.execute("DELETE FROM seasons WHERE name = ?", (name,))
                if cursor.rowcount == 0:
                    raise DatabaseError(f"Season '{name}' not found")
        except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive
            raise DatabaseError("Failed to delete season") from exc

    def record_match(self, record: dict[str, object]) -> None:
        """対戦ログを 1 件保存します。

        必須キー: ``match_no``, ``deck_name``, ``turn``, ``result``
        任意キー: ``opponent_deck``, ``keywords``（イテラブル可）
        ``keywords`` は JSON 文字列へシリアライズして保存します。
        """
        keywords = record.get("keywords") or []
        keywords_json = json.dumps(list(keywords), ensure_ascii=False)
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO matches (
                        match_no, deck_name, turn, opponent_deck, keywords, result
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.get("match_no", 0),
                        record["deck_name"],
                        record["turn"],
                        record.get("opponent_deck", ""),
                        keywords_json,
                        record["result"],
                    ),
                )
        except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive
            raise DatabaseError("Failed to record match") from exc

    def fetch_opponent_decks(self) -> list[str]:
        """対戦相手デッキ名を重複排除して取得（プルダウン候補用）。"""

        with self._connect() as connection:
            cursor = connection.execute(
                """
                SELECT DISTINCT TRIM(opponent_deck) AS deck
                FROM matches
                WHERE opponent_deck IS NOT NULL
                  AND TRIM(opponent_deck) <> ''
                ORDER BY deck COLLATE NOCASE
                """
            )
            return [row["deck"] for row in cursor.fetchall() if row["deck"]]

    # ------------------------------------------------------------------
    # 高度なヘルパー
    # ------------------------------------------------------------------
    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """トランザクションを伴う安全な実行ブロックを提供します。

        利用例:
        >>> with db.transaction() as con:
        ...     con.execute(...)
        ...     con.execute(...)

        例外発生時は自動でロールバック、正常終了時はコミットします。
        """
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive
            connection.rollback()
            raise DatabaseError("Database transaction failed") from exc
        finally:
            connection.close()

    # ------------------------------------------------------------------
    # 内部ユーティリティ
    # ------------------------------------------------------------------
    @staticmethod
    def _format_timestamp(value: object) -> str:
        """SQLite に保存されたエポック秒（INTEGER）を ISO 8601 文字列へ変換。"""
        try:
            ts = int(value)
        except (TypeError, ValueError):
            return ""
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


# 将来の拡張メモ
# - FK 強化: matches.deck_name → decks.id（数値 FK）へ移行し、ON UPDATE/DELETE CASCADE を検討
# - PRAGMA 設定: WAL モード（journal_mode=WAL）や synchronous=NORMAL を運用に応じて設定
# - user_version: スキーマバージョン管理で移行を明確化
# - 型安全: record 引数の TypedDict/Dataclass 化、Enum 的表現（turn/result）など
# - エクスポート: CSV/JSON ダンプ & インポートユーティリティ
# - 統計情報: 勝率計算やターン別集計などの集計クエリヘルパー