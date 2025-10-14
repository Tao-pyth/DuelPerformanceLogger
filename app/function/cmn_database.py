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
import io
import json
import sqlite3
import uuid
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Optional
import tempfile
import zipfile

from app.function.core import paths

from .cmn_logger import log_error


class DatabaseError(RuntimeError):
    """DB 操作時の想定外エラーを表す基底例外。"""


class DuplicateEntryError(DatabaseError):
    """一意制約違反（同名レコードの重複登録など）を表す例外。"""


class DatabaseManager:
    """アプリ用 SQLite データベースのユーティリティラッパー。

    Parameters
    ----------
    db_path: Optional[Path | str]
        データベースファイルのパス。未指定時は ``%APPDATA%/DuelPerformanceLogger/db/``
        配下にある ``duel_performance.sqlite3`` を使用。
        ディレクトリを渡した場合は、その直下に既定名で作成します。
    """

    CURRENT_SCHEMA_VERSION = "0.2.1"
    METADATA_DEFAULTS = {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "ui_mode": "normal",
        "last_backup": "",
        "last_backup_at": "",
        "last_migration_message": "",
        "last_migration_message_at": "",
    }

    def __init__(self, db_path: Optional[Path | str] = None) -> None:
        # プロジェクト標準のユーザーデータディレクトリ配下へ DB を配置する。
        base_dir = paths.database_dir()
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

        self.ensure_metadata_defaults()
        self._migrate_schema()

    # ------------------------------------------------------------------
    # バージョン管理
    # ------------------------------------------------------------------
    @staticmethod
    def _int_to_semver(value: int) -> str:
        safe_value = max(int(value), 0)
        major = safe_value // 10000
        minor = (safe_value // 100) % 100
        patch = safe_value % 100
        return f"{major}.{minor}.{patch}"

    @staticmethod
    def _is_semver(candidate: str) -> bool:
        parts = candidate.split(".")
        if len(parts) != 3:
            return False
        for part in parts:
            if not part.isdigit():
                return False
            if not (0 <= int(part) <= 99):
                return False
        return True

    @classmethod
    def normalize_schema_version(cls, value: str | int | None, fallback: str | None = None) -> str:
        if fallback is None:
            fallback = "0.0.0"

        if isinstance(value, int):
            return cls._int_to_semver(value)

        if isinstance(value, str):
            candidate = value.strip()
        elif value is None:
            candidate = ""
        else:
            candidate = str(value).strip()

        if candidate:
            if cls._is_semver(candidate):
                return candidate
            if candidate.isdigit():
                try:
                    return cls._int_to_semver(int(candidate))
                except ValueError:  # pragma: no cover - defensive
                    pass

        return fallback

    def get_schema_version(self) -> str:
        """保存されているスキーマバージョンを取得する。"""

        value = self.get_metadata("schema_version")
        return self.normalize_schema_version(value)

    def set_schema_version(self, version: str | int) -> None:
        """スキーマバージョンを更新する。"""

        normalized = self.normalize_schema_version(
            version, fallback=self.CURRENT_SCHEMA_VERSION
        )
        self.set_metadata("schema_version", normalized)

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
                    description TEXT DEFAULT '',
                    usage_count INTEGER NOT NULL DEFAULT 0
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

                CREATE TABLE opponent_decks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    usage_count INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    identifier TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT DEFAULT '',
                    usage_count INTEGER NOT NULL DEFAULT 0,
                    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
                );

                CREATE TABLE matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_no INTEGER NOT NULL,
                    deck_id INTEGER NOT NULL,
                    season_id INTEGER,
                    turn INTEGER NOT NULL CHECK (turn IN (0, 1)),
                    opponent_deck TEXT,
                    keywords TEXT,
                    result INTEGER NOT NULL CHECK (result IN (-1, 0, 1)),
                    youtube_url TEXT DEFAULT '',
                    favorite INTEGER NOT NULL DEFAULT 0,
                    -- 生成時刻は UTC のエポック秒
                    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
                    FOREIGN KEY(deck_id)
                        REFERENCES decks(id)
                        ON DELETE RESTRICT
                        ON UPDATE CASCADE,
                    FOREIGN KEY(season_id)
                        REFERENCES seasons(id)
                        ON DELETE SET NULL
                        ON UPDATE CASCADE
                );

                CREATE INDEX idx_matches_deck_id ON matches(deck_id);
                CREATE INDEX idx_matches_season_id ON matches(season_id);
                CREATE INDEX idx_matches_created_at ON matches(created_at);
                CREATE INDEX idx_matches_result ON matches(result);
                """
            )

            cursor.execute(
                "INSERT OR REPLACE INTO db_metadata (key, value) VALUES (?, ?)",
                ("schema_version", self.CURRENT_SCHEMA_VERSION),
            )
            cursor.execute(
                "INSERT OR REPLACE INTO db_metadata (key, value) VALUES (?, ?)",
                ("ui_mode", "normal"),
            )
            cursor.execute(
                "INSERT OR REPLACE INTO db_metadata (key, value) VALUES (?, ?)",
                ("last_backup", ""),
            )
            cursor.execute(
                "INSERT OR REPLACE INTO db_metadata (key, value) VALUES (?, ?)",
                ("last_backup_at", ""),
            )
            cursor.execute(
                "INSERT OR REPLACE INTO db_metadata (key, value) VALUES (?, ?)",
                ("last_migration_message", ""),
            )
            cursor.execute(
                "INSERT OR REPLACE INTO db_metadata (key, value) VALUES (?, ?)",
                ("last_migration_message_at", ""),
            )

    # ------------------------------------------------------------------
    # メタデータ操作
    # ------------------------------------------------------------------
    def ensure_metadata_defaults(self) -> None:
        """メタデータに必須の既定値が存在することを保証する。"""

        with self._connect() as connection:
            for key, value in self.METADATA_DEFAULTS.items():
                cursor = connection.execute(
                    "SELECT 1 FROM db_metadata WHERE key = ?", (key,)
                )
                if cursor.fetchone() is None:
                    connection.execute(
                        "INSERT INTO db_metadata (key, value) VALUES (?, ?)",
                        (key, value),
                    )

    def _migrate_schema(self) -> None:
        """スキーマの不足分を補完し、バージョン番号の整合性を保つ。"""

        target_version = self.CURRENT_SCHEMA_VERSION
        current_version = self.get_schema_version()
        schema_changed = False

        keyword_changed = False
        with self._connect() as connection:
            if self._table_exists(connection, "decks") and not self._column_exists(
                connection, "decks", "usage_count"
            ):
                connection.execute(
                    "ALTER TABLE decks ADD COLUMN usage_count INTEGER NOT NULL DEFAULT 0"
                )
                schema_changed = True

            if not self._table_exists(connection, "matches"):
                connection.execute(
                    """
                    CREATE TABLE matches (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        match_no INTEGER NOT NULL,
                        deck_id INTEGER NOT NULL,
                        season_id INTEGER,
                        turn INTEGER NOT NULL CHECK (turn IN (0, 1)),
                        opponent_deck TEXT,
                        keywords TEXT,
                        result INTEGER NOT NULL CHECK (result IN (-1, 0, 1)),
                        youtube_url TEXT DEFAULT '',
                        favorite INTEGER NOT NULL DEFAULT 0,
                        created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
                        FOREIGN KEY(deck_id) REFERENCES decks(id)
                            ON DELETE RESTRICT
                            ON UPDATE CASCADE,
                        FOREIGN KEY(season_id) REFERENCES seasons(id)
                            ON DELETE SET NULL
                            ON UPDATE CASCADE
                    )
                    """
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_matches_deck_id ON matches(deck_id)"
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_matches_season_id ON matches(season_id)"
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_matches_created_at ON matches(created_at)"
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_matches_result ON matches(result)"
                )
                schema_changed = True

            if not self._table_exists(connection, "opponent_decks"):
                connection.execute(
                    """
                    CREATE TABLE opponent_decks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE,
                        usage_count INTEGER NOT NULL DEFAULT 0
                    )
                    """
                )
                schema_changed = True
            elif not self._column_exists(connection, "opponent_decks", "usage_count"):
                connection.execute(
                    "ALTER TABLE opponent_decks ADD COLUMN usage_count INTEGER NOT NULL DEFAULT 0"
                )
                schema_changed = True

            if not self._table_exists(connection, "keywords"):
                connection.execute(
                    """
                    CREATE TABLE keywords (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        identifier TEXT NOT NULL UNIQUE,
                        name TEXT NOT NULL UNIQUE,
                        description TEXT DEFAULT '',
                        usage_count INTEGER NOT NULL DEFAULT 0,
                        created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
                    )
                    """
                )
                keyword_changed = True

            if self._table_exists(connection, "matches"):
                if not self._column_exists(connection, "matches", "season_id"):
                    connection.execute(
                        "ALTER TABLE matches ADD COLUMN season_id INTEGER"
                    )
                    connection.execute(
                        "CREATE INDEX IF NOT EXISTS idx_matches_season_id ON matches(season_id)"
                    )
                    schema_changed = True
                if not self._column_exists(connection, "matches", "youtube_url"):
                    connection.execute(
                        "ALTER TABLE matches ADD COLUMN youtube_url TEXT DEFAULT ''"
                    )
                    schema_changed = True
                if not self._column_exists(connection, "matches", "favorite"):
                    connection.execute(
                        "ALTER TABLE matches ADD COLUMN favorite INTEGER NOT NULL DEFAULT 0"
                    )
                    schema_changed = True

        if schema_changed:
            self.recalculate_usage_counts()
        if keyword_changed:
            self.recalculate_keyword_usage()

        if current_version != target_version:
            self.set_schema_version(target_version)

    def get_metadata(self, key: str, default: str | None = None) -> str | None:
        """Retrieve a metadata value or return *default* when absent."""

        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    "SELECT value FROM db_metadata WHERE key = ?", (key,)
                )
                row = cursor.fetchone()
                if row is None:
                    return default
                return row["value"]
        except sqlite3.DatabaseError:  # pragma: no cover - defensive
            return default

    def set_metadata(self, key: str, value: str) -> None:
        """Persist a metadata value as text."""

        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO db_metadata (key, value) VALUES (?, ?)",
                (key, value),
            )

    def get_ui_mode(self, default: str = "normal") -> str:
        value = self.get_metadata("ui_mode", default) or default
        return value

    def set_ui_mode(self, mode: str) -> None:
        self.set_metadata("ui_mode", mode)

    def record_backup_path(self, path: Path | str) -> None:
        self.set_metadata("last_backup", str(path))

    # ------------------------------------------------------------------
    # バックアップユーティリティ
    # ------------------------------------------------------------------
    def export_backup(self, destination: Optional[Path | str] = None) -> Path:
        """現在の DB 内容を CSV として保存し、作成先パスを返す。"""

        if destination is None:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            destination = paths.backup_dir() / timestamp
        else:
            destination = Path(destination)

        destination.mkdir(parents=True, exist_ok=True)

        with self._connect() as connection:
            tables = ("decks", "opponent_decks", "seasons", "matches")
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
            for table in ("decks", "opponent_decks", "seasons", "matches"):
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
                    if table == "matches" and "deck_id" not in insert_columns:
                        insert_columns.append("deck_id")
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

                        if table == "matches":
                            try:
                                if "turn" in row_map:
                                    row_map["turn"] = self._encode_turn(row_map["turn"])
                                if "result" in row_map:
                                    row_map["result"] = self._encode_result(row_map["result"])
                                if "season_id" in insert_columns:
                                    season_value = row_map.get("season_id")
                                    if season_value in (None, "", "null", "NULL"):
                                        row_map["season_id"] = None
                                    else:
                                        try:
                                            row_map["season_id"] = int(season_value)
                                        except (TypeError, ValueError):
                                            row_map["season_id"] = None
                                deck_identifier = row_map.get("deck_id")
                                if deck_identifier in (None, "", 0):
                                    deck_name_value = str(row_map.get("deck_name", "") or "").strip()
                                    deck_id = self._find_deck_id(connection, deck_name_value)
                                    if deck_id is None:
                                        log_error(
                                            "Failed to resolve deck_id during import",
                                            DatabaseError("Unknown deck name"),
                                            deck_name=deck_name_value,
                                        )
                                        continue
                                    row_map["deck_id"] = deck_id
                                else:
                                    row_map["deck_id"] = int(deck_identifier)
                            except ValueError as exc:
                                log_error(
                                    "Failed to convert legacy match data during import",
                                    exc,
                                    row=row_map,
                                )
                                continue

                        params = [row_map.get(col) for col in insert_columns]
                        connection.execute(query, params)
                        count += 1
                    restored[table] = count

        self.recalculate_usage_counts()
        return restored

    def export_backup_zip(
        self, destination: Optional[Path | str] = None
    ) -> tuple[Path, str, bytes]:
        """バックアップ CSV を生成し ZIP 圧縮したバイト列を返す。"""

        backup_dir = self.export_backup(destination)
        archive_name = f"dpl-backup-{backup_dir.name}.zip"

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for csv_file in sorted(backup_dir.glob("*.csv")):
                archive.write(csv_file, arcname=csv_file.name)

        buffer.seek(0)
        return backup_dir, archive_name, buffer.read()

    def import_backup_archive(self, payload: bytes) -> dict[str, int]:
        """ZIP 化されたバックアップからデータを復元する。"""

        if not payload:
            raise DatabaseError("バックアップデータが空です")

        expected_files = {
            "decks.csv",
            "opponent_decks.csv",
            "seasons.csv",
            "matches.csv",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                members = [info for info in archive.infolist() if not info.is_dir()]
                found_files = {Path(info.filename).name for info in members}
                missing = expected_files - found_files
                if missing:
                    raise DatabaseError(
                        "バックアップに必要なファイルが不足しています: "
                        + ", ".join(sorted(missing))
                    )

                for info in members:
                    name = Path(info.filename).name
                    if name not in expected_files:
                        continue
                    target_path = temp_path / name
                    with archive.open(info) as source, target_path.open("wb") as dest:
                        dest.write(source.read())

            return self.import_backup(temp_path)

    def reset_database(self) -> None:
        """テーブルを再構築して空の状態へ初期化する。"""

        self.initialize_database()
        self.ensure_metadata_defaults()

    # ------------------------------------------------------------------
    # 取得系ヘルパー
    # ------------------------------------------------------------------
    def fetch_decks(self) -> list[dict[str, object]]:
        """登録済みデッキを名称順（大文字小文字無視）で返却。"""
        with self._connect() as connection:
            cursor = connection.execute(
                """
                SELECT name, description, usage_count
                FROM decks
                ORDER BY name COLLATE NOCASE
                """
            )
            return [dict(row) for row in cursor.fetchall()]

    def fetch_seasons(self) -> list[dict[str, object]]:
        """登録済みシーズンを名称順で返却。"""
        with self._connect() as connection:
            cursor = connection.execute(
                """
                SELECT
                    id,
                    name,
                    description AS notes,
                    start_date,
                    start_time,
                    end_date,
                    end_time
                FROM seasons
                ORDER BY name COLLATE NOCASE
                """
            )
            results: list[dict[str, object]] = []
            for row in cursor.fetchall():
                payload = dict(row)
                payload.setdefault("notes", payload.get("description", ""))
                payload.pop("description", None)
                results.append(payload)
            return results

    def fetch_matches(self, deck_name: Optional[str] = None) -> list[dict[str, object]]:
        """
        matches テーブル参照。
        起動順序/既存DB差異により matches が未作成だった場合、
        1) マイグレーションで自己修復し、2) 同クエリを 1 回のみ再試行する。
        """

        def _run_query() -> list[dict[str, object]]:
            with self._connect() as connection:
                keyword_lookup, name_lookup = self._build_keyword_lookups(connection)

                params: tuple[object, ...] = ()
                query = (
                    "SELECT "
                    "m.id, m.match_no, m.deck_id, d.name AS deck_name, "
                    "m.season_id, s.name AS season_name, m.turn, "
                    "m.opponent_deck, m.keywords, m.result, m.created_at, "
                    "m.youtube_url, m.favorite "
                    "FROM matches AS m "
                    "JOIN decks AS d ON d.id = m.deck_id "
                    "LEFT JOIN seasons AS s ON s.id = m.season_id"
                )

                if deck_name:
                    deck_id = self._find_deck_id(connection, deck_name)
                    if deck_id is None:
                        return []
                    query += " WHERE m.deck_id = ?"
                    params = (deck_id,)

                query += " ORDER BY m.created_at ASC, m.id ASC"

                cursor = connection.execute(query, params)
                rows = cursor.fetchall()
                return [
                    self._hydrate_match_row(row, keyword_lookup, name_lookup)
                    for row in rows
                ]

        try:
            return _run_query()
        except sqlite3.OperationalError as exc:
            # "no such table: matches" が原因のときだけ、自己修復して 1 回再試行
            msg = str(exc).lower()
            if "no such table" in msg and "matches" in msg:
                # 不足スキーマ補完（冪等）
                self._migrate_schema()
                # 再試行（1回だけ）
                return _run_query()
            # 別要因は投げ直し
            raise

    def fetch_last_match(self, deck_name: Optional[str] = None) -> Optional[dict[str, object]]:
        """最新の対戦ログを 1 件返却（デッキ名で絞り込み可能）。"""
        query = (
            "SELECT "
            "m.id, m.match_no, m.deck_id, d.name AS deck_name, "
            "m.season_id, s.name AS season_name, m.turn, "
            "m.opponent_deck, m.keywords, m.result, m.created_at, "
            "m.youtube_url, m.favorite "
            "FROM matches AS m "
            "JOIN decks AS d ON d.id = m.deck_id "
            "LEFT JOIN seasons AS s ON s.id = m.season_id"
        )

        with self._connect() as connection:
            keyword_lookup, name_lookup = self._build_keyword_lookups(connection)
            params: tuple[object, ...] = ()
            if deck_name:
                deck_id = self._find_deck_id(connection, deck_name)
                if deck_id is None:
                    return None
                query += " WHERE m.deck_id = ?"
                params = (deck_id,)

            query += " ORDER BY m.created_at DESC, m.id DESC LIMIT 1"
            cursor = connection.execute(query, params)
            row = cursor.fetchone()
            if row is None:
                return None
            return self._hydrate_match_row(row, keyword_lookup, name_lookup)

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
        cleaned = name.strip()
        if not cleaned:
            raise DatabaseError("デッキ名を入力してください")
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO decks (name, description) VALUES (?, ?)",
                    (cleaned, description),
                )
        except sqlite3.IntegrityError as exc:  # pragma: no cover - defensive
            log_error("Duplicate deck insertion attempted", exc, name=cleaned)
            raise DuplicateEntryError(
                f"デッキ「{cleaned}」は既に登録されています"
            ) from exc
        except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive
            log_error("Failed to insert deck", exc, name=cleaned)
            raise DatabaseError("Failed to insert deck") from exc

    def add_season(
        self,
        name: str,
        notes: str = "",
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
                    (name, notes, start_date, start_time, end_date, end_time),
                )
        except sqlite3.IntegrityError as exc:  # pragma: no cover - defensive
            log_error("Duplicate season insertion attempted", exc, name=name)
            raise DuplicateEntryError(f"Season '{name}' already exists") from exc
        except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive
            log_error("Failed to insert season", exc, name=name)
            raise DatabaseError("Failed to insert season") from exc

    def delete_deck(self, name: str) -> None:
        """デッキ定義を削除。存在しない場合は `DatabaseError` を送出。"""

        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    "SELECT usage_count FROM decks WHERE name = ?",
                    (name,),
                )
                row = cursor.fetchone()
                if row is None:
                    raise DatabaseError(f"デッキ「{name}」が見つかりません")
                if int(row["usage_count"] or 0) > 0:
                    raise DatabaseError("使用中のデッキは削除できません")
                connection.execute("DELETE FROM decks WHERE name = ?", (name,))
        except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive
            log_error("Failed to delete deck", exc, name=name)
            raise DatabaseError("Failed to delete deck") from exc

    def delete_season(self, name: str) -> None:
        """シーズン定義を削除。存在しない場合は `DatabaseError` を送出。"""

        try:
            with self._connect() as connection:
                cursor = connection.execute("DELETE FROM seasons WHERE name = ?", (name,))
                if cursor.rowcount == 0:
                    raise DatabaseError(f"Season '{name}' not found")
        except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive
            log_error("Failed to delete season", exc, name=name)
            raise DatabaseError("Failed to delete season") from exc

    def record_match(self, record: dict[str, object]) -> None:
        """対戦ログを 1 件保存します。

        必須キー: ``match_no``, ``deck_name``, ``turn``, ``result``
        任意キー: ``opponent_deck``, ``keywords``（イテラブル可）
        ``keywords`` は JSON 文字列へシリアライズして保存します。
        """
        try:
            turn_value = self._encode_turn(record["turn"])
            result_value = self._encode_result(record["result"])
        except (KeyError, ValueError) as exc:
            log_error("Invalid match record supplied", exc, record=record)
            raise DatabaseError("Invalid match record") from exc
        deck_name = str(record.get("deck_name", "")).strip()
        if not deck_name:
            raise DatabaseError("デッキ名を指定してください")
        opponent_name = str(record.get("opponent_deck", "")).strip()
        raw_keywords = record.get("keywords") or []
        youtube_url = str(record.get("youtube_url", "") or "").strip()
        favorite_flag = 1 if bool(record.get("favorite")) else 0
        season_id: Optional[int] = None
        season_input = record.get("season_id")
        season_name_input = record.get("season_name")

        try:
            with self._connect() as connection:
                deck_id = self._get_deck_id(connection, deck_name)
                if season_input not in (None, ""):
                    try:
                        candidate = int(season_input)
                    except (TypeError, ValueError) as exc:
                        raise DatabaseError("シーズン ID が不正です") from exc
                    if candidate <= 0:
                        raise DatabaseError("シーズン ID が不正です")
                    season_id = candidate
                elif season_name_input:
                    season_id = self._find_season_id(
                        connection, str(season_name_input or "")
                    )
                    if season_name_input and season_id is None:
                        raise DatabaseError("指定したシーズンが見つかりません")
                keyword_lookup, name_lookup = self._build_keyword_lookups(connection)
                filtered_keywords = [
                    str(value or "").strip()
                    for value in raw_keywords
                    if str(value or "").strip()
                ]
                keyword_ids = self._sanitize_keyword_ids_from_lookup(
                    keyword_lookup, name_lookup, raw_keywords
                )
                if filtered_keywords and not keyword_ids:
                    raise DatabaseError("存在しないキーワードが含まれています")
                keywords_json = json.dumps(keyword_ids, ensure_ascii=False)
                connection.execute(
                    """
                    INSERT INTO matches (
                        match_no,
                        deck_id,
                        season_id,
                        turn,
                        opponent_deck,
                        keywords,
                        result,
                        youtube_url,
                        favorite
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.get("match_no", 0),
                        deck_id,
                        season_id,
                        turn_value,
                        opponent_name if opponent_name else None,
                        keywords_json,
                        result_value,
                        youtube_url,
                        favorite_flag,
                    ),
                )

                connection.execute(
                    "UPDATE decks SET usage_count = usage_count + 1 WHERE id = ?",
                    (deck_id,),
                )

                if opponent_name:
                    connection.execute(
                        """
                        INSERT INTO opponent_decks (name, usage_count)
                        VALUES (?, 1)
                        ON CONFLICT(name)
                        DO UPDATE SET usage_count = usage_count + 1
                        """,
                        (opponent_name,),
                    )

                for identifier in keyword_ids:
                    connection.execute(
                        """
                        UPDATE keywords
                        SET usage_count = usage_count + 1
                        WHERE identifier = ?
                        """,
                        (identifier,),
                    )
        except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive
            log_error("Failed to record match", exc, record=record)
            raise DatabaseError("Failed to record match") from exc

    def fetch_opponent_decks(self) -> list[dict[str, object]]:
        """登録済みの対戦相手デッキ一覧を名称順で返却。"""

        with self._connect() as connection:
            cursor = connection.execute(
                """
                SELECT name, usage_count
                FROM opponent_decks
                ORDER BY name COLLATE NOCASE
                """
            )
            return [dict(row) for row in cursor.fetchall()]

    def fetch_keywords(self) -> list[dict[str, object]]:
        """登録済みキーワード一覧を名称順で返却。"""

        with self._connect() as connection:
            cursor = connection.execute(
                """
                SELECT identifier, name, description, usage_count, created_at
                FROM keywords
                ORDER BY name COLLATE NOCASE
                """
            )
            results: list[dict[str, object]] = []
            for row in cursor.fetchall():
                results.append(
                    {
                        "identifier": row["identifier"],
                        "name": row["name"],
                        "description": row["description"] or "",
                        "usage_count": row["usage_count"],
                        "created_at": self._format_timestamp(row["created_at"]),
                    }
                )
            return results

    def add_opponent_deck(self, name: str) -> None:
        """対戦相手デッキ定義を追加。重複時は ``DuplicateEntryError``。"""

        cleaned = name.strip()
        if not cleaned:
            raise DatabaseError("対戦相手デッキ名を入力してください")

        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO opponent_decks (name, usage_count) VALUES (?, 0)",
                    (cleaned,),
                )
        except sqlite3.IntegrityError as exc:  # pragma: no cover - defensive
            log_error(
                "Duplicate opponent deck insertion attempted",
                exc,
                name=cleaned,
            )
            raise DuplicateEntryError(
                f"対戦相手デッキ「{cleaned}」は既に登録されています"
            ) from exc
        except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive
            log_error("Failed to insert opponent deck", exc, name=cleaned)
            raise DatabaseError("Failed to insert opponent deck") from exc

    def delete_opponent_deck(self, name: str) -> None:
        """対戦相手デッキ定義を削除。使用中は削除できない。"""

        cleaned = name.strip()
        if not cleaned:
            raise DatabaseError("対戦相手デッキを指定してください")

        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    "SELECT usage_count FROM opponent_decks WHERE name = ?",
                    (cleaned,),
                )
                row = cursor.fetchone()
                if row is None:
                    raise DatabaseError(f"対戦相手デッキ「{cleaned}」が見つかりません")
                if int(row["usage_count"] or 0) > 0:
                    raise DatabaseError("使用中の対戦相手デッキは削除できません")
                connection.execute(
                    "DELETE FROM opponent_decks WHERE name = ?",
                    (cleaned,),
                )
        except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive
            log_error("Failed to delete opponent deck", exc, name=cleaned)
            raise DatabaseError("Failed to delete opponent deck") from exc

    def add_keyword(self, name: str, description: str = "") -> str:
        """キーワードを追加し、生成された識別子を返却。"""

        cleaned_name = name.strip()
        if not cleaned_name:
            raise DatabaseError("キーワード名を入力してください")
        cleaned_description = (description or "").strip()

        try:
            with self._connect() as connection:
                identifier = self._generate_keyword_identifier(connection)
                connection.execute(
                    """
                    INSERT INTO keywords (identifier, name, description, usage_count)
                    VALUES (?, ?, ?, 0)
                    """,
                    (identifier, cleaned_name, cleaned_description),
                )
                return identifier
        except sqlite3.IntegrityError as exc:  # pragma: no cover - defensive
            log_error("Duplicate keyword insertion attempted", exc, name=cleaned_name)
            raise DuplicateEntryError(
                f"キーワード「{cleaned_name}」は既に登録されています"
            ) from exc
        except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive
            log_error("Failed to insert keyword", exc, name=cleaned_name)
            raise DatabaseError("Failed to insert keyword") from exc

    def delete_keyword(self, identifier: str) -> None:
        """キーワードを削除。使用中は削除できない。"""

        cleaned = (identifier or "").strip()
        if not cleaned:
            raise DatabaseError("削除するキーワードを指定してください")

        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    "SELECT usage_count FROM keywords WHERE identifier = ?",
                    (cleaned,),
                )
                row = cursor.fetchone()
                if row is None:
                    raise DatabaseError("指定したキーワードが見つかりません")
                if int(row["usage_count"] or 0) > 0:
                    raise DatabaseError("使用中のキーワードは削除できません")
                connection.execute(
                    "DELETE FROM keywords WHERE identifier = ?",
                    (cleaned,),
                )
        except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive
            log_error("Failed to delete keyword", exc, identifier=cleaned)
            raise DatabaseError("Failed to delete keyword") from exc

    def fetch_match(self, match_id: int) -> dict[str, object]:
        """対戦ログ 1 件の詳細を取得する。"""

        with self._connect() as connection:
            keyword_lookup, name_lookup = self._build_keyword_lookups(connection)
            cursor = connection.execute(
                """
                SELECT
                    m.id,
                    m.match_no,
                    m.deck_id,
                    d.name AS deck_name,
                    m.season_id,
                    s.name AS season_name,
                    m.turn,
                    m.opponent_deck,
                    m.keywords,
                    m.result,
                    m.created_at,
                    m.youtube_url,
                    m.favorite
                FROM matches AS m
                JOIN decks AS d ON d.id = m.deck_id
                LEFT JOIN seasons AS s ON s.id = m.season_id
                WHERE m.id = ?
                """,
                (match_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise DatabaseError("指定した対戦情報が見つかりません")

            return self._hydrate_match_row(row, keyword_lookup, name_lookup)

    def update_match(self, match_id: int, updates: dict[str, object]) -> dict[str, object]:
        """既存の対戦ログを更新し、更新後の詳細を返却する。"""

        with self.transaction() as connection:
            keyword_lookup, name_lookup = self._build_keyword_lookups(connection)
            cursor = connection.execute(
                """
                SELECT m.*, d.name AS deck_name
                FROM matches AS m
                JOIN decks AS d ON d.id = m.deck_id
                WHERE m.id = ?
                """,
                (match_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise DatabaseError("指定した対戦情報が見つかりません")

            old_deck_id = int(row["deck_id"])
            old_deck_name = row["deck_name"]
            old_season_id = row["season_id"] if "season_id" in row.keys() else None
            new_deck_name = str(updates.get("deck_name", old_deck_name) or "").strip()
            if not new_deck_name:
                raise DatabaseError("デッキ名を指定してください")

            new_deck_id = self._get_deck_id(connection, new_deck_name)

            season_id_value = old_season_id
            if "season_id" in updates or "season_name" in updates:
                season_input = updates.get("season_id")
                season_name_input = updates.get("season_name")
                if season_input not in (None, ""):
                    try:
                        candidate = int(season_input)
                    except (TypeError, ValueError) as exc:
                        raise DatabaseError("シーズン ID が不正です") from exc
                    if candidate <= 0:
                        raise DatabaseError("シーズン ID が不正です")
                    season_id_value = candidate
                elif season_name_input:
                    season_id_value = self._find_season_id(
                        connection, str(season_name_input or "")
                    )
                    if season_name_input and season_id_value is None:
                        raise DatabaseError("指定したシーズンが見つかりません")
                else:
                    season_id_value = None

            match_no_value = updates.get("match_no", row["match_no"])
            try:
                match_no = int(match_no_value)
            except (TypeError, ValueError) as exc:
                raise DatabaseError("対戦番号には数値を入力してください") from exc
            if match_no <= 0:
                raise DatabaseError("対戦番号には 1 以上の値を指定してください")

            turn_input = updates.get("turn", self._decode_turn(row["turn"]))
            turn_value = self._encode_turn(turn_input)

            result_input = updates.get("result", self._decode_result(row["result"]))
            result_value = self._encode_result(result_input)

            opponent_input = updates.get("opponent_deck", row["opponent_deck"] or "")
            opponent_name = str(opponent_input or "").strip()

            youtube_url = str(updates.get("youtube_url", row["youtube_url"] or "") or "").strip()
            if len(youtube_url) > 2048:
                raise DatabaseError("YouTube URL は 2048 文字以内で入力してください")

            favorite_input = updates.get("favorite", bool(row["favorite"]))
            if isinstance(favorite_input, str):
                normalized_favorite = favorite_input.strip().lower()
                favorite_flag = (
                    1
                    if normalized_favorite
                    in {"1", "true", "yes", "on", "お気に入り", "favorite"}
                    else 0
                )
            elif isinstance(favorite_input, (int, float)):
                favorite_flag = 1 if int(favorite_input) != 0 else 0
            else:
                favorite_flag = 1 if bool(favorite_input) else 0

            current_keywords_raw: list[object] = []
            if row["keywords"]:
                try:
                    current_keywords_raw = json.loads(row["keywords"])
                except json.JSONDecodeError:
                    current_keywords_raw = []
            old_keyword_ids = self._sanitize_keyword_ids_from_lookup(
                keyword_lookup, name_lookup, current_keywords_raw
            )

            if "keywords" in updates:
                new_keywords_input = updates.get("keywords") or []
                filtered_new_keywords = [
                    str(value or "").strip()
                    for value in new_keywords_input
                    if str(value or "").strip()
                ]
                new_keyword_ids = self._sanitize_keyword_ids_from_lookup(
                    keyword_lookup, name_lookup, new_keywords_input
                )
                if filtered_new_keywords and not new_keyword_ids:
                    raise DatabaseError("選択したキーワードが存在しません")
            else:
                new_keyword_ids = list(old_keyword_ids)

            keywords_json = json.dumps(new_keyword_ids, ensure_ascii=False)

            old_opponent = row["opponent_deck"] or ""

            if opponent_name:
                connection.execute(
                    """
                    INSERT INTO opponent_decks (name, usage_count)
                    VALUES (?, 0)
                    ON CONFLICT(name) DO NOTHING
                    """,
                    (opponent_name,),
                )

            connection.execute(
                """
                UPDATE matches
                SET match_no = ?,
                    deck_id = ?,
                    season_id = ?,
                    turn = ?,
                    opponent_deck = ?,
                    keywords = ?,
                    result = ?,
                    youtube_url = ?,
                    favorite = ?
                WHERE id = ?
                """,
                (
                    match_no,
                    new_deck_id,
                    season_id_value,
                    turn_value,
                    opponent_name if opponent_name else None,
                    keywords_json,
                    result_value,
                    youtube_url,
                    favorite_flag,
                    match_id,
                ),
            )

            if old_deck_id != new_deck_id:
                connection.execute(
                    """
                    UPDATE decks
                    SET usage_count = CASE
                        WHEN usage_count > 0 THEN usage_count - 1
                        ELSE 0
                    END
                    WHERE id = ?
                    """,
                    (old_deck_id,),
                )
                connection.execute(
                    "UPDATE decks SET usage_count = usage_count + 1 WHERE id = ?",
                    (new_deck_id,),
                )

            if old_opponent != opponent_name:
                if old_opponent:
                    connection.execute(
                        """
                        UPDATE opponent_decks
                        SET usage_count = CASE
                            WHEN usage_count > 0 THEN usage_count - 1
                            ELSE 0
                        END
                        WHERE name = ?
                        """,
                        (old_opponent,),
                    )
                if opponent_name:
                    connection.execute(
                        "UPDATE opponent_decks SET usage_count = usage_count + 1 WHERE name = ?",
                        (opponent_name,),
                    )

            old_keyword_set = set(old_keyword_ids)
            new_keyword_set = set(new_keyword_ids)
            removed_keywords = old_keyword_set - new_keyword_set
            added_keywords = new_keyword_set - old_keyword_set

            for identifier in removed_keywords:
                connection.execute(
                    """
                    UPDATE keywords
                    SET usage_count = CASE
                        WHEN usage_count > 0 THEN usage_count - 1
                        ELSE 0
                    END
                    WHERE identifier = ?
                    """,
                    (identifier,),
                )

            for identifier in added_keywords:
                connection.execute(
                    "UPDATE keywords SET usage_count = usage_count + 1 WHERE identifier = ?",
                    (identifier,),
                )

        return self.fetch_match(match_id)

    def delete_match(self, match_id: int) -> None:
        """対戦ログを削除し、関連する使用回数を更新する。"""

        with self.transaction() as connection:
            keyword_lookup, name_lookup = self._build_keyword_lookups(connection)
            cursor = connection.execute(
                "SELECT deck_id, opponent_deck, keywords FROM matches WHERE id = ?",
                (match_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise DatabaseError("指定した対戦情報が見つかりません")

            deck_id = row["deck_id"]
            opponent_name = (row["opponent_deck"] or "").strip()
            keyword_ids: list[str] = []
            if row["keywords"]:
                try:
                    keyword_ids = self._sanitize_keyword_ids_from_lookup(
                        keyword_lookup, name_lookup, json.loads(row["keywords"])
                    )
                except json.JSONDecodeError:
                    keyword_ids = []

            connection.execute("DELETE FROM matches WHERE id = ?", (match_id,))

            if deck_id is not None:
                connection.execute(
                    """
                    UPDATE decks
                    SET usage_count = CASE
                        WHEN usage_count > 0 THEN usage_count - 1
                        ELSE 0
                    END
                    WHERE id = ?
                    """,
                    (deck_id,),
                )

            if opponent_name:
                connection.execute(
                    """
                    UPDATE opponent_decks
                    SET usage_count = CASE
                        WHEN usage_count > 0 THEN usage_count - 1
                        ELSE 0
                    END
                    WHERE name = ?
                    """,
                    (opponent_name,),
                )

            for identifier in keyword_ids:
                connection.execute(
                    """
                    UPDATE keywords
                    SET usage_count = CASE
                        WHEN usage_count > 0 THEN usage_count - 1
                        ELSE 0
                    END
                    WHERE identifier = ?
                    """,
                    (identifier,),
                )

    def recalculate_usage_counts(self) -> None:
        """デッキと対戦相手デッキの使用回数を対戦ログから再計算する。"""

        with self._connect() as connection:
            connection.execute("UPDATE decks SET usage_count = 0")

            if self._column_exists(connection, "matches", "deck_id"):
                cursor = connection.execute(
                    "SELECT deck_id, COUNT(*) AS match_count FROM matches GROUP BY deck_id"
                )
                for row in cursor.fetchall():
                    deck_id = row["deck_id"]
                    if deck_id is None:
                        continue
                    connection.execute(
                        "UPDATE decks SET usage_count = ? WHERE id = ?",
                        (int(row["match_count"]), deck_id),
                    )

            cursor = connection.execute("SELECT name FROM opponent_decks")
            for row in cursor.fetchall():
                name = row["name"]
                if not name:
                    continue
                count_row = connection.execute(
                    "SELECT COUNT(*) FROM matches WHERE TRIM(opponent_deck) = TRIM(?)",
                    (name,),
                ).fetchone()
                usage = int(count_row[0]) if count_row else 0
                connection.execute(
                    "UPDATE opponent_decks SET usage_count = ? WHERE name = ?",
                    (usage, name),
                )

    def recalculate_keyword_usage(self) -> None:
        """キーワードの使用回数を対戦ログから再計算する。"""

        with self._connect() as connection:
            keyword_lookup, name_lookup = self._build_keyword_lookups(connection)
            if not keyword_lookup:
                return

            usage_counter: Counter[str] = Counter()
            cursor = connection.execute("SELECT keywords FROM matches")
            for row in cursor.fetchall():
                if not row["keywords"]:
                    continue
                try:
                    raw_keywords = json.loads(row["keywords"])
                except json.JSONDecodeError:
                    continue
                keyword_ids = self._sanitize_keyword_ids_from_lookup(
                    keyword_lookup, name_lookup, raw_keywords
                )
                usage_counter.update(keyword_ids)

            connection.execute("UPDATE keywords SET usage_count = 0")
            for identifier, count in usage_counter.items():
                connection.execute(
                    "UPDATE keywords SET usage_count = ? WHERE identifier = ?",
                    (int(count), identifier),
                )

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
            log_error("Database transaction failed", exc)
            raise DatabaseError("Database transaction failed") from exc
        finally:
            connection.close()

    # ------------------------------------------------------------------
    # 内部ユーティリティ
    # ------------------------------------------------------------------
    def _find_deck_id(
        self, connection: sqlite3.Connection, deck_name: str
    ) -> Optional[int]:
        cleaned = (deck_name or "").strip()
        if not cleaned:
            return None
        cursor = connection.execute(
            "SELECT id FROM decks WHERE name = ?",
            (cleaned,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return int(row["id"])

    def _get_deck_id(self, connection: sqlite3.Connection, deck_name: str) -> int:
        deck_id = self._find_deck_id(connection, deck_name)
        if deck_id is None:
            raise DatabaseError(f"デッキ「{deck_name}」が見つかりません")
        return deck_id

    def _find_season_id(
        self, connection: sqlite3.Connection, season_name: str
    ) -> Optional[int]:
        cleaned = (season_name or "").strip()
        if not cleaned:
            return None
        cursor = connection.execute(
            "SELECT id FROM seasons WHERE name = ?",
            (cleaned,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return int(row["id"])

    def _get_season_id(self, connection: sqlite3.Connection, season_name: str) -> int:
        season_id = self._find_season_id(connection, season_name)
        if season_id is None:
            raise DatabaseError(f"シーズン「{season_name}」が見つかりません")
        return season_id

    def _hydrate_match_row(
        self,
        row: sqlite3.Row,
        keyword_lookup: dict[str, dict[str, object]],
        name_lookup: dict[str, str],
    ) -> dict[str, object]:
        raw_keywords: list[object] = []
        if row["keywords"]:
            try:
                raw_keywords = json.loads(row["keywords"])
            except json.JSONDecodeError:
                raw_keywords = []

        keyword_ids = self._sanitize_keyword_ids_from_lookup(
            keyword_lookup, name_lookup, raw_keywords
        )
        keyword_details = self._keyword_details_from_lookup(
            keyword_lookup, keyword_ids
        )

        return {
            "id": row["id"],
            "match_no": row["match_no"],
            "deck_name": row["deck_name"],
            "season_id": row["season_id"],
            "season_name": row["season_name"] or "",
            "turn": self._decode_turn(row["turn"]),
            "opponent_deck": row["opponent_deck"] or "",
            "keywords": [item["name"] for item in keyword_details],
            "keyword_ids": keyword_ids,
            "keyword_details": keyword_details,
            "result": self._decode_result(row["result"]),
            "created_at": self._format_timestamp(row["created_at"]),
            "youtube_url": row["youtube_url"] or "",
            "favorite": bool(row["favorite"]),
        }

    def _build_keyword_lookups(
        self, connection: sqlite3.Connection
    ) -> tuple[dict[str, dict[str, object]], dict[str, str]]:
        cursor = connection.execute(
            "SELECT identifier, name, description, usage_count FROM keywords"
        )
        keyword_lookup: dict[str, dict[str, object]] = {}
        name_lookup: dict[str, str] = {}
        for row in cursor.fetchall():
            identifier = row["identifier"]
            name = row["name"]
            info = {
                "identifier": identifier,
                "name": name,
                "description": row["description"] or "",
                "usage_count": row["usage_count"],
            }
            keyword_lookup[identifier] = info
            name_lookup[name.strip().lower()] = identifier
        return keyword_lookup, name_lookup

    def _sanitize_keyword_ids_from_lookup(
        self,
        keyword_lookup: dict[str, dict[str, object]],
        name_lookup: dict[str, str],
        keywords: Iterable[object],
    ) -> list[str]:
        sanitized: list[str] = []
        seen: set[str] = set()
        for value in keywords or []:
            candidate = str(value or "").strip()
            if not candidate:
                continue
            identifier = None
            lower = candidate.lower()
            if candidate in keyword_lookup:
                identifier = candidate
            elif lower in name_lookup:
                identifier = name_lookup[lower]
            if identifier and identifier not in seen:
                seen.add(identifier)
                sanitized.append(identifier)
        return sanitized

    def _keyword_details_from_lookup(
        self,
        keyword_lookup: dict[str, dict[str, object]],
        keyword_ids: Iterable[str],
    ) -> list[dict[str, object]]:
        details: list[dict[str, object]] = []
        for identifier in keyword_ids:
            info = keyword_lookup.get(identifier)
            if not info:
                continue
            details.append(
                {
                    "identifier": info["identifier"],
                    "name": info["name"],
                    "description": info.get("description", ""),
                    "usage_count": info.get("usage_count", 0),
                }
            )
        return details

    def _generate_keyword_identifier(self, connection: sqlite3.Connection) -> str:
        while True:
            identifier = f"kw-{uuid.uuid4().hex[:10]}"
            cursor = connection.execute(
                "SELECT 1 FROM keywords WHERE identifier = ?",
                (identifier,),
            )
            if cursor.fetchone() is None:
                return identifier

    @staticmethod
    def _format_timestamp(value: object) -> str:
        """SQLite に保存されたエポック秒（INTEGER）を ISO 8601 文字列へ変換。"""
        try:
            ts = int(value)
        except (TypeError, ValueError):
            return ""
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()

    @staticmethod
    def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
        cursor = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        )
        return cursor.fetchone() is not None

    @staticmethod
    def _column_exists(
        connection: sqlite3.Connection, table_name: str, column_name: str
    ) -> bool:
        try:
            cursor = connection.execute(f"PRAGMA table_info({table_name})")
        except sqlite3.DatabaseError:
            return False
        for row in cursor.fetchall():
            # `PRAGMA table_info` returns tuples like (cid, name, type, notnull, dflt_value, pk)
            if len(row) > 1 and row[1] == column_name:
                return True
        return False

    @staticmethod
    def _encode_turn(value: object) -> int:
        if isinstance(value, bool):
            return 1 if value else 0
        if isinstance(value, (int, float)):
            return 1 if int(value) != 0 else 0
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "first", "先攻"}:
                return 1
            if normalized in {"0", "false", "second", "後攻"}:
                return 0
        raise ValueError(f"Unsupported turn value: {value!r}")

    @staticmethod
    def _encode_result(value: object) -> int:
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            mapping = {
                "win": 1,
                "lose": -1,
                "loss": -1,
                "draw": 0,
                "victory": 1,
                "敗北": -1,
                "勝ち": 1,
                "負け": -1,
                "引き分け": 0,
            }
            if normalized in mapping:
                return mapping[normalized]
            if normalized in {"1", "-1", "0"}:
                return int(normalized)
        raise ValueError(f"Unsupported result value: {value!r}")

    @staticmethod
    def _decode_turn(value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return int(value) != 0
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"first", "先攻", "true", "1"}:
                return True
            if normalized in {"second", "後攻", "false", "0"}:
                return False
        return False

    @staticmethod
    def _decode_result(value: object) -> int:
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            mapping = {
                "win": 1,
                "victory": 1,
                "lose": -1,
                "loss": -1,
                "draw": 0,
                "勝ち": 1,
                "負け": -1,
                "引き分け": 0,
            }
            if normalized in mapping:
                return mapping[normalized]
            if normalized in {"1", "-1", "0"}:
                return int(normalized)
        return 0


# 将来の拡張メモ
# - FK 強化: seasons / keywords など他テーブル間の参照制約追加を検討
# - PRAGMA 設定: WAL モード（journal_mode=WAL）や synchronous=NORMAL を運用に応じて設定
# - user_version: スキーマバージョン管理で移行を明確化
# - 型安全: record 引数の TypedDict/Dataclass 化、Enum 的表現（turn/result）など
# - エクスポート: CSV/JSON ダンプ & インポートユーティリティ
# - 統計情報: 勝率計算やターン別集計などの集計クエリヘルパー
