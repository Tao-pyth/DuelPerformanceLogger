import json
import sqlite3
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.function.cmn_database import DatabaseManager
from app.function.core.youtube_types import YouTubeSyncFlag


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
        youtube_row = connection.execute(
            "SELECT youtube_flag, youtube_url, youtube_video_id, youtube_checked_at FROM matches"
        ).fetchone()

    assert [row["name"] for row in decks] == ["Test Deck"]
    assert [row["memo"] for row in matches] == ["note"]
    assert tuple(youtube_row) == (0, "", None, None)


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
        rows = connection.execute(
            """
            SELECT memo, favorite, youtube_flag, youtube_url, youtube_video_id, youtube_checked_at
            FROM matches
            """
        ).fetchone()

    backup_files = list(temp_db.parent.glob("duel_performance_backup_*.sqlite3"))

    assert schema_info["user_version"] == DatabaseManager.SCHEMA_VERSION
    assert "memo" in schema_info["columns"]
    assert rows["memo"] == ""
    assert rows["favorite"] == 0
    assert rows["youtube_flag"] == 0
    assert rows["youtube_url"] == ""
    assert rows["youtube_video_id"] in {"", None}
    if rows["youtube_checked_at"] is not None:
        assert isinstance(rows["youtube_checked_at"], int)
    assert backup_files, "Expected migration backup file to be created"
    assert manager.get_schema_version() == DatabaseManager.CURRENT_SCHEMA_VERSION


def test_record_youtube_state_transitions(temp_db: Path) -> None:
    manager = DatabaseManager(temp_db)
    manager.ensure_database()

    with manager.transaction() as connection:
        deck_id = connection.execute(
            "INSERT INTO decks (name, description) VALUES (?, ?)",
            ("Deck", ""),
        ).lastrowid
        match_id = connection.execute(
            """
            INSERT INTO matches (match_no, deck_id, season_id, turn, opponent_deck, keywords, memo, result)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (1, deck_id, None, 0, "Opponent", json.dumps([]), "", 1),
        ).lastrowid

    manager.record_youtube_in_progress(match_id)
    with manager._connect() as connection:
        row = connection.execute(
            "SELECT youtube_flag, youtube_url, youtube_video_id, youtube_checked_at FROM matches WHERE id = ?",
            (match_id,),
        ).fetchone()
    assert row["youtube_flag"] == YouTubeSyncFlag.IN_PROGRESS
    assert row["youtube_url"] == ""
    assert row["youtube_video_id"] == ""
    assert isinstance(row["youtube_checked_at"], int)

    manager.record_youtube_success(match_id, " https://youtu.be/abc123 ", "abc123")
    with manager._connect() as connection:
        row = connection.execute(
            "SELECT youtube_flag, youtube_url, youtube_video_id, youtube_checked_at FROM matches WHERE id = ?",
            (match_id,),
        ).fetchone()
    assert row["youtube_flag"] == YouTubeSyncFlag.COMPLETED
    assert row["youtube_url"] == "https://youtu.be/abc123"
    assert row["youtube_video_id"] == "abc123"
    assert isinstance(row["youtube_checked_at"], int)

    manager.record_youtube_failure(match_id)
    with manager._connect() as connection:
        row = connection.execute(
            "SELECT youtube_flag, youtube_url, youtube_video_id, youtube_checked_at FROM matches WHERE id = ?",
            (match_id,),
        ).fetchone()
    assert row["youtube_flag"] == YouTubeSyncFlag.NEEDS_RETRY
    assert row["youtube_url"] == ""
    assert row["youtube_video_id"] == ""
    assert isinstance(row["youtube_checked_at"], int)

    manager.record_youtube_manual(match_id, " https://www.youtube.com/watch?v=xyz789 ", "xyz789")
    with manager._connect() as connection:
        row = connection.execute(
            "SELECT youtube_flag, youtube_url, youtube_video_id, youtube_checked_at FROM matches WHERE id = ?",
            (match_id,),
        ).fetchone()
    assert row["youtube_flag"] == YouTubeSyncFlag.MANUAL
    assert row["youtube_url"] == "https://www.youtube.com/watch?v=xyz789"
    assert row["youtube_video_id"] == "xyz789"
    assert isinstance(row["youtube_checked_at"], int)

    manager.record_youtube_manual(match_id, "", None)
    with manager._connect() as connection:
        row = connection.execute(
            "SELECT youtube_flag, youtube_url, youtube_video_id FROM matches WHERE id = ?",
            (match_id,),
        ).fetchone()
    assert row["youtube_flag"] == YouTubeSyncFlag.NOT_REQUESTED
    assert row["youtube_url"] == ""
    assert row["youtube_video_id"] == ""


def test_record_match_accepts_minimal_payload(temp_db: Path) -> None:
    manager = DatabaseManager(temp_db)
    manager.ensure_database()

    with manager.transaction() as connection:
        connection.execute(
            "INSERT INTO decks (name, description) VALUES (?, ?)",
            ("Minimal", ""),
        )

    match_id = manager.record_match(
        {
            "match_no": 1,
            "deck_name": "Minimal",
            "turn": "first",
            "result": "win",
        }
    )

    assert match_id > 0
    with manager._connect() as connection:
        row = connection.execute(
            "SELECT match_no, deck_id, favorite FROM matches WHERE id = ?",
            (match_id,),
        ).fetchone()

    assert row["match_no"] == 1
    assert row["deck_id"] > 0
    assert row["favorite"] == 0


def test_upload_job_lifecycle(temp_db: Path, tmp_path: Path) -> None:
    manager = DatabaseManager(temp_db)
    manager.ensure_database()

    with manager.transaction() as connection:
        deck_id = connection.execute(
            "INSERT INTO decks (name, description) VALUES (?, ?)",
            ("Deck", ""),
        ).lastrowid
        match_id = connection.execute(
            """
            INSERT INTO matches (match_no, deck_id, season_id, turn, opponent_deck, keywords, memo, result)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (1, deck_id, None, 1, "Auto", json.dumps([]), "", 1),
        ).lastrowid

    recording_dir = tmp_path / "recordings"
    recording_dir.mkdir(parents=True, exist_ok=True)
    recording_path = recording_dir / "match.mp4"
    recording_path.write_bytes(b"video")

    job_id = manager.create_upload_job(match_id, recording_path)
    assert job_id > 0

    job = manager.fetch_upload_job(match_id)
    assert job is not None
    assert job["status"] == "pending"
    assert Path(job["recording_path"]).name == "match.mp4"

    manager.update_upload_job(
        job_id,
        status="uploaded",
        youtube_url="https://youtu.be/example",
        youtube_video_id="example",
    )
    updated = manager.fetch_upload_job(match_id)
    assert updated["status"] == "uploaded"
    assert updated["youtube_url"] == "https://youtu.be/example"
    assert updated["youtube_video_id"] == "example"

    replacement = manager.create_upload_job(
        match_id,
        recording_path.with_name("match_v2.mp4"),
        status="failed",
        error_message="integrity error",
    )
    assert replacement == job_id
    final = manager.fetch_upload_job(match_id)
    assert final["status"] == "failed"
    assert final["error_message"] == "integrity error"
    assert Path(final["recording_path"]).name == "match_v2.mp4"


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
