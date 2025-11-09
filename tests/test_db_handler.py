from __future__ import annotations

import logging
from pathlib import Path

import pytest

from app.function.cmn_database import DatabaseManager
from app.function.core import db_handler, versioning


@pytest.fixture()
def db_manager(tmp_path: Path) -> DatabaseManager:
    manager = DatabaseManager(tmp_path / "meta.sqlite3")
    manager.ensure_database()
    return manager


def test_get_set_app_meta(db_manager: DatabaseManager) -> None:
    expected_version = str(versioning.get_target_version())
    assert db_handler.get_app_meta("app_version", manager=db_manager) == expected_version

    db_handler.set_app_meta("app_version", "0.4.3", manager=db_manager)
    assert db_handler.get_app_meta("app_version", manager=db_manager) == "0.4.3"


def test_resolve_app_version_warns_on_missing(
    db_manager: DatabaseManager,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    caplog.set_level(logging.WARNING)
    # Reset module-level guard so the warning is emitted for this test
    monkeypatch.setattr(db_handler, "_VERSION_WARNING_EMITTED", False, raising=False)
    monkeypatch.setattr(
        db_manager, "get_app_meta", lambda key, default=None: None, raising=False
    )

    resolved = db_handler.resolve_app_version(
        "fallback", manager=db_manager, warn_on_missing=True
    )
    assert resolved == "fallback"
    assert any(
        "app_meta.app_version" in record.message for record in caplog.records
    )

    # Subsequent calls should not emit additional warnings
    caplog.clear()
    resolved_again = db_handler.resolve_app_version(
        "fallback", manager=db_manager, warn_on_missing=True
    )
    assert resolved_again == "fallback"
    assert not caplog.records
