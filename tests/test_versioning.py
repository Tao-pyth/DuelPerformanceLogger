from __future__ import annotations

import sqlite3
from pathlib import Path

from packaging.version import Version

from app.function.core import versioning


def test_coerce_version_parses_various_inputs() -> None:
    assert versioning.coerce_version("v0.3.2") == Version("0.3.2")
    assert versioning.coerce_version(2) == Version("0.3.1")
    assert versioning.coerce_version((0, 3, 0)) == Version("0.3.0")


def test_normalize_version_string_trims_and_formats() -> None:
    normalized = versioning.normalize_version_string(" 0.3.1 ")
    assert normalized == "0.3.1"


def test_get_db_version_prefers_user_version(tmp_path: Path) -> None:
    db_path = tmp_path / "db.sqlite3"
    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA user_version = 2")
    with sqlite3.connect(db_path) as connection:
        assert versioning.get_db_version(connection) == Version("0.3.1")


def test_get_db_version_falls_back_to_metadata(tmp_path: Path) -> None:
    db_path = tmp_path / "db.sqlite3"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE db_metadata (key TEXT PRIMARY KEY, value TEXT)")
        connection.execute(
            "INSERT INTO db_metadata (key, value) VALUES (?, ?)",
            ("schema_version", "0.2.1"),
        )
    with sqlite3.connect(db_path) as connection:
        assert versioning.get_db_version(connection) == Version("0.2.1")


def test_to_user_version_maps_known_values() -> None:
    assert versioning.to_user_version("0.3.2") == 3
    assert versioning.to_user_version(Version("0.3.1")) == 2
