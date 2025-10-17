import json
import sqlite3
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.function.cmn_database import DatabaseManager


@pytest.fixture()
def temp_db(tmp_path: Path) -> Path:
    return tmp_path / "duel_performance.sqlite3"


def test_initialize_database_preserves_existing_data(temp_db: Path) -> None:
    manager = DatabaseManager(temp_db)
    manager.ensure_database()

    with manager.transaction() as connection:
        deck_id = connection.execute(
            "INSERT INTO decks (name, description) VALUES (?, ?)",
            ("Test Deck", "Sample"),
        ).lastrowid
        connection.execute(
            """
            INSERT INTO matches (match_no, deck_id, season_id, turn, opponent_deck, keywords, memo, result)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (1, deck_id, None, 0, "Legacy", json.dumps(["tag"]), "note", 1),
        )

    manager.ensure_database()

    with manager._connect() as connection:
        decks = connection.execute("SELECT name FROM decks").fetchall()
        matches = connection.execute("SELECT memo FROM matches").fetchall()

    assert [row["name"] for row in decks] == ["Test Deck"]
    assert [row["memo"] for row in matches] == ["note"]


def test_migration_updates_user_version_and_preserves_data(temp_db: Path) -> None:
    with sqlite3.connect(temp_db) as connection:
        connection.execute(
            """
            CREATE TABLE decks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT DEFAULT ''
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE seasons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
            """
        )
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
        connection.execute(
            """
            CREATE TABLE matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_no INTEGER NOT NULL,
                deck_id INTEGER NOT NULL,
                turn INTEGER NOT NULL,
                opponent_deck TEXT,
                keywords TEXT,
                result INTEGER NOT NULL,
                created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
            )
            """
        )
        connection.execute(
            "INSERT INTO decks (name) VALUES (?)",
            ("Legacy Deck",),
        )
        connection.execute(
            "INSERT INTO matches (match_no, deck_id, turn, opponent_deck, keywords, result)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (1, 1, 0, "Old", json.dumps(["legacy"]), 1),
        )
        connection.execute("PRAGMA user_version = 1")

    manager = DatabaseManager(temp_db)
    manager.ensure_database()

    with manager._connect() as connection:
        schema_info = {
            "columns": [row[1] for row in connection.execute("PRAGMA table_info(matches)")],
            "user_version": connection.execute("PRAGMA user_version").fetchone()[0],
        }
        rows = connection.execute("SELECT memo, favorite, youtube_url FROM matches").fetchone()

    backup_files = list(temp_db.parent.glob("duel_performance_backup_*.sqlite3"))

    assert schema_info["user_version"] == DatabaseManager.SCHEMA_VERSION
    assert "memo" in schema_info["columns"]
    assert tuple(rows) == ("", 0, "")
    assert backup_files, "Expected migration backup file to be created"
    assert manager.get_schema_version() == DatabaseManager.CURRENT_SCHEMA_VERSION


def test_e2e_restart_keeps_data(temp_db: Path) -> None:
    first = DatabaseManager(temp_db)
    first.ensure_database()

    with first.transaction() as connection:
        deck_id = connection.execute(
            "INSERT INTO decks (name) VALUES (?)",
            ("Restart Deck",),
        ).lastrowid
        connection.execute(
            """
            INSERT INTO matches (match_no, deck_id, season_id, turn, opponent_deck, keywords, memo, result)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (1, deck_id, None, 1, "Opponent", json.dumps([]), "memo", -1),
        )

    second = DatabaseManager(temp_db)
    second.ensure_database()

    with second._connect() as connection:
        deck_names = [row["name"] for row in connection.execute("SELECT name FROM decks").fetchall()]
        match_results = [row["result"] for row in connection.execute("SELECT result FROM matches").fetchall()]
        user_version = connection.execute("PRAGMA user_version").fetchone()[0]

    assert deck_names == ["Restart Deck"]
    assert match_results == [-1]
    assert user_version == DatabaseManager.SCHEMA_VERSION
