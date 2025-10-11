"""Application entry point wiring together the Eel web interface."""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

import eel

from app.function import (
    AppState,
    DatabaseError,
    DatabaseManager,
    build_state,
    get_app_state,
    set_app_state,
)
from app.function.cmn_config import load_config
from app.function.cmn_logger import log_db_error
from app.function.cmn_resources import get_text
from app.function.core import paths
from app.function.core.version import __version__

logger = logging.getLogger(__name__)
_WEB_ROOT = paths.web_root()
_INDEX_FILE = "index.html"
_SERVICE: Optional["DuelPerformanceService"] = None


class DuelPerformanceService:
    """Coordinate database access and expose snapshots for the web UI."""

    def __init__(self) -> None:
        self.config = load_config()
        self.db = DatabaseManager()
        self.db.ensure_database()
        self.migration_result = ""

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------
    def bootstrap(self) -> AppState:
        """Ensure the database is ready and return the initial state."""

        expected_version = self._expected_schema_version()
        current_version = self.db.get_schema_version()
        if current_version != expected_version:
            self.migration_result = self._handle_version_mismatch(
                current_version, expected_version
            )
        else:
            self.migration_result = ""

        self.db.set_schema_version(expected_version)
        return self.refresh_state()

    def refresh_state(self) -> AppState:
        """Fetch the latest data from the database and update the state."""

        state = build_state(self.db, self.config, migration_result=self.migration_result)
        return set_app_state(state)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _expected_schema_version(self) -> int:
        expected_version_raw = self.config.get("database", {}).get(
            "expected_version", DatabaseManager.CURRENT_SCHEMA_VERSION
        )
        try:
            return int(expected_version_raw)
        except (TypeError, ValueError):
            return DatabaseManager.CURRENT_SCHEMA_VERSION

    def _handle_version_mismatch(self, current_version: int, expected_version: int) -> str:
        """Run backup and restore flow when the schema version differs."""

        lines = [
            get_text("settings.db_migration_detected").format(
                current=current_version, expected=expected_version
            )
        ]

        try:
            backup_path = self.db.export_backup()
            lines.append(
                get_text("settings.db_migration_backup").format(path=str(backup_path))
            )
            self.db.record_backup_path(backup_path)

            self.db.initialize_database()
            self.db.set_schema_version(expected_version)

            try:
                restored = self.db.import_backup(backup_path)
            except DatabaseError as exc:
                log_db_error(
                    "Failed to restore database during migration",
                    exc,
                    backup=str(backup_path),
                )
                lines.append(
                    get_text("settings.db_migration_restore_failed").format(
                        error=str(exc)
                    )
                )
                return "\n".join(
                    [get_text("settings.db_migration_failure").format(error=str(exc))]
                    + lines
                )
            else:
                lines.append(
                    get_text("settings.db_migration_restore_success").format(
                        decks=restored.get("decks", 0),
                        seasons=restored.get("seasons", 0),
                        matches=restored.get("matches", 0),
                    )
                )

            return "\n".join([get_text("settings.db_migration_success")] + lines)
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.exception("Unexpected error during schema migration")
            return "\n".join(
                [
                    get_text("settings.db_migration_failure").format(error=str(exc)),
                    *lines,
                ]
            )


def _ensure_service() -> DuelPerformanceService:
    global _SERVICE
    if _SERVICE is None:
        service = DuelPerformanceService()
        service.bootstrap()
        _SERVICE = service
    return _SERVICE


def _build_snapshot(state: Optional[AppState] = None) -> dict[str, Any]:
    snapshot_source = state or get_app_state()
    data = snapshot_source.snapshot()
    data["version"] = __version__
    return data


@eel.expose
def fetch_snapshot() -> dict[str, Any]:
    """Return the latest state snapshot for the front-end."""

    service = _ensure_service()
    state = service.refresh_state()
    return _build_snapshot(state)


def main() -> None:
    """Launch the Eel application."""

    logging.basicConfig(level=logging.INFO)
    service = _ensure_service()
    eel.init(str(_WEB_ROOT))

    # Preload data once so the first fetch does not need to hit disk.
    _build_snapshot(service.refresh_state())

    eel_mode = os.environ.get("DPL_EEL_MODE", "default")
    block = os.environ.get("DPL_NO_UI") != "1"

    eel.start(
        _INDEX_FILE,
        mode=eel_mode,
        size=(1280, 768),
        host="127.0.0.1",
        port=0,
        block=block,
    )


if __name__ == "__main__":
    main()
