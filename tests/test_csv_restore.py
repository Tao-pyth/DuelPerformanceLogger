from __future__ import annotations

import io
import json
import sqlite3
import zipfile
from pathlib import Path

from app.function import DatabaseManager
from app.function.core import backup_restore


def _write_csv(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    path.write_text(
        ",".join(headers) + "\n" + "\n".join(",".join(map(str, row)) for row in rows) + "\n",
        encoding="utf-8",
    )


def _prepare_csv_backup(base: Path) -> None:
    _write_csv(
        base / "decks.csv",
        ["id", "name", "description", "usage_count"],
        [["1", "Test Deck", "Notes", "0"]],
    )
    _write_csv(
        base / "opponent_decks.csv",
        ["id", "name", "usage_count"],
        [["1", "Opponent", "0"]],
    )
    _write_csv(
        base / "seasons.csv",
        [
            "id",
            "name",
            "description",
            "start_date",
            "start_time",
            "end_date",
            "end_time",
            "rank_statistics_target",
        ],
        [["1", "Spring", "Season notes", "2024-01-01", "09:00", "2024-02-01", "21:00", "1"]],
    )
    _write_csv(
        base / "matches.csv",
        [
            "id",
            "match_no",
            "deck_id",
            "season_id",
            "turn",
            "opponent_deck",
            "keywords",
            "memo",
            "result",
            "youtube_url",
            "favorite",
            "created_at",
        ],
        [
            [
                "1",
                "1",
                "1",
                "1",
                "first",
                "Rival",
                json.dumps(["tag"]),
                "memo",
                "win",
                "",
                "1",
                "1700000000",
            ]
        ],
    )


def test_restore_from_directory_inserts_records(tmp_path: Path) -> None:
    db_path = tmp_path / "db.sqlite3"
    manager = DatabaseManager(db_path)
    manager.ensure_database()

    csv_dir = tmp_path / "csv"
    csv_dir.mkdir()
    _prepare_csv_backup(csv_dir)

    report = backup_restore.restore_from_directory(db_path, csv_dir)
    assert report.ok
    assert report.restored["decks"] == 1
    assert report.log_path and report.log_path.exists()

    with sqlite3.connect(db_path) as connection:
        deck_names = [row[0] for row in connection.execute("SELECT name FROM decks").fetchall()]
        result = connection.execute("SELECT turn, result, favorite FROM matches").fetchone()
    assert deck_names == ["Test Deck"]
    assert result == (1, 1, 1)


def test_restore_from_directory_dry_run_does_not_commit(tmp_path: Path) -> None:
    db_path = tmp_path / "db.sqlite3"
    manager = DatabaseManager(db_path)
    manager.ensure_database()

    csv_dir = tmp_path / "csv"
    csv_dir.mkdir()
    _prepare_csv_backup(csv_dir)

    report = backup_restore.restore_from_directory(db_path, csv_dir, dry_run=True)
    assert report.ok
    with sqlite3.connect(db_path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM decks").fetchone()[0]
    assert count == 0


def test_restore_from_directory_reports_missing_column(tmp_path: Path) -> None:
    db_path = tmp_path / "db.sqlite3"
    manager = DatabaseManager(db_path)
    manager.ensure_database()

    csv_dir = tmp_path / "csv"
    csv_dir.mkdir()
    _prepare_csv_backup(csv_dir)

    # Remove a required column from matches
    (csv_dir / "matches.csv").write_text(
        "id,deck_id\n1,1\n",
        encoding="utf-8",
    )

    report = backup_restore.restore_from_directory(db_path, csv_dir)
    assert not report.ok
    assert report.error
    assert report.failures
    assert report.log_path and report.log_path.exists()


def test_restore_from_zip_bytes(tmp_path: Path) -> None:
    db_path = tmp_path / "db.sqlite3"
    manager = DatabaseManager(db_path)
    manager.ensure_database()

    csv_dir = tmp_path / "csv"
    csv_dir.mkdir()
    _prepare_csv_backup(csv_dir)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for csv_file in csv_dir.iterdir():
            archive.write(csv_file, arcname=csv_file.name)
    payload = buffer.getvalue()

    report = backup_restore.restore_from_zip_bytes(db_path, payload)
    assert report.ok
    assert report.restored["matches"] == 1
