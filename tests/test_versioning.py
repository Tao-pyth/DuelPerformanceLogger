from __future__ import annotations

import importlib
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


def test_get_target_version_prefers_semver_from_files(
    tmp_path: Path, monkeypatch
) -> None:
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "V0.3.4__upgrade.sql").write_text("", encoding="utf-8")
    (migrations / "V0.3.3__hotfix.py").write_text("", encoding="utf-8")

    monkeypatch.setenv("DPL_MIGRATIONS_ROOT", str(migrations))
    try:
        importlib.reload(versioning)
        assert versioning.get_target_version() == Version("0.3.4")
    finally:
        monkeypatch.delenv("DPL_MIGRATIONS_ROOT", raising=False)
        importlib.reload(versioning)


def test_get_target_version_falls_back_when_missing_semver(
    tmp_path: Path, monkeypatch
) -> None:
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "001_legacy.sql").write_text("", encoding="utf-8")

    monkeypatch.setenv("DPL_MIGRATIONS_ROOT", str(migrations))
    try:
        importlib.reload(versioning)
        assert versioning.get_target_version() == max(versioning.SCHEMA_VERSION_MAP.values())
    finally:
        monkeypatch.delenv("DPL_MIGRATIONS_ROOT", raising=False)
        importlib.reload(versioning)


def test_get_target_version_uses_current_fallback(
    tmp_path: Path, monkeypatch
) -> None:
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "legacy.sql").write_text("", encoding="utf-8")

    monkeypatch.setenv("DPL_MIGRATIONS_ROOT", str(migrations))
    try:
        importlib.reload(versioning)
        fallback = Version("9.9.9")
        assert versioning.get_target_version(fallback) == fallback
    finally:
        monkeypatch.delenv("DPL_MIGRATIONS_ROOT", raising=False)
        importlib.reload(versioning)
