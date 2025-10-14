"""Application entry point wiring together the Eel web interface."""

from __future__ import annotations

import logging
import os
import base64
from datetime import datetime
from typing import Any, Optional

import eel

from app.function import (
    AppState,
    DatabaseError,
    DatabaseManager,
    DuplicateEntryError,
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
        self.migration_timestamp = (
            self.db.get_metadata("last_migration_message_at", "") or ""
        )

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
        self.migration_timestamp = (
            self.db.get_metadata("last_migration_message_at", "") or ""
        )
        return self.refresh_state()

    def refresh_state(self) -> AppState:
        """Fetch the latest data from the database and update the state."""

        state = build_state(
            self.db,
            self.config,
            migration_result=self.migration_result,
            migration_timestamp=self.migration_timestamp,
        )
        return set_app_state(state)

    # ------------------------------------------------------------------
    # Application operations
    # ------------------------------------------------------------------
    def register_deck(self, name: str, description: str) -> AppState:
        cleaned_name = (name or "").strip()
        if not cleaned_name:
            raise ValueError("デッキ名を入力してください")
        cleaned_description = (description or "").strip()
        self.db.add_deck(cleaned_name, cleaned_description)
        return self.refresh_state()

    def register_opponent_deck(self, name: str) -> AppState:
        cleaned_name = (name or "").strip()
        if not cleaned_name:
            raise ValueError("対戦相手デッキ名を入力してください")
        self.db.add_opponent_deck(cleaned_name)
        return self.refresh_state()

    def prepare_match(
        self, deck_name: str, season_id: Optional[int] = None
    ) -> dict[str, object]:
        deck = (deck_name or "").strip()
        if not deck:
            raise ValueError("デッキを選択してください")
        next_match = self.db.get_next_match_number(deck)
        timestamp = _format_timestamp()
        normalized_season_id: Optional[int] = None
        if season_id not in (None, "", 0, "0"):
            try:
                normalized_season_id = int(season_id)  # type: ignore[arg-type]
            except (TypeError, ValueError) as exc:
                raise ValueError("シーズンの指定が不正です") from exc
            if normalized_season_id <= 0:
                raise ValueError("シーズンの指定が不正です")
        return {
            "deck_name": deck,
            "next_match_no": next_match,
            "timestamp": timestamp,
            "season_id": normalized_season_id,
        }

    def register_match(self, payload: dict[str, object]) -> AppState:
        deck_name = str(payload.get("deck_name", "")).strip()
        if not deck_name:
            raise ValueError("デッキを選択してください")

        turn = payload.get("turn")
        if turn not in (True, False):
            raise ValueError("先攻/後攻を選択してください")

        result = payload.get("result")
        if result not in (-1, 0, 1):
            raise ValueError("対戦結果を選択してください")

        opponent = str(payload.get("opponent_deck", "")).strip()
        raw_keywords = payload.get("keywords", [])
        keywords: list[str] = []
        if isinstance(raw_keywords, (list, tuple)):
            for value in raw_keywords:
                candidate = str(value or "").strip()
                if candidate:
                    keywords.append(candidate)
        season_id_value = payload.get("season_id")
        season_name = str(payload.get("season_name", "") or "").strip()
        normalized_season_id: Optional[int] = None
        if season_id_value not in (None, "", 0, "0"):
            try:
                normalized_season_id = int(season_id_value)
            except (TypeError, ValueError) as exc:
                raise ValueError("シーズンの指定が不正です") from exc
            if normalized_season_id <= 0:
                raise ValueError("シーズンの指定が不正です")
        match_record = {
            "match_no": self.db.get_next_match_number(deck_name),
            "deck_name": deck_name,
            "turn": bool(turn),
            "opponent_deck": opponent,
            "keywords": keywords,
            "result": int(result),
            "season_id": normalized_season_id,
        }
        if normalized_season_id is None and season_name:
            match_record["season_name"] = season_name

        self.db.record_match(match_record)
        return self.refresh_state()

    def delete_deck(self, name: str) -> AppState:
        cleaned = (name or "").strip()
        if not cleaned:
            raise ValueError("削除するデッキを選択してください")
        self.db.delete_deck(cleaned)
        return self.refresh_state()

    def delete_opponent_deck(self, name: str) -> AppState:
        cleaned = (name or "").strip()
        if not cleaned:
            raise ValueError("削除する対戦相手デッキを選択してください")
        self.db.delete_opponent_deck(cleaned)
        return self.refresh_state()

    def register_keyword(self, name: str, description: str) -> AppState:
        cleaned_name = (name or "").strip()
        if not cleaned_name:
            raise ValueError("キーワード名を入力してください")
        cleaned_description = (description or "").strip()
        self.db.add_keyword(cleaned_name, cleaned_description)
        return self.refresh_state()

    def delete_keyword(self, identifier: str) -> AppState:
        cleaned = (identifier or "").strip()
        if not cleaned:
            raise ValueError("削除するキーワードを選択してください")
        self.db.delete_keyword(cleaned)
        return self.refresh_state()

    def register_season(
        self,
        name: str,
        notes: str = "",
        *,
        start_date: Optional[str] = None,
        start_time: Optional[str] = None,
        end_date: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> AppState:
        cleaned_name = (name or "").strip()
        if not cleaned_name:
            raise ValueError("シーズン名を入力してください")

        def _normalize(value: Optional[str]) -> Optional[str]:
            text = (value or "").strip()
            return text or None

        self.db.add_season(
            cleaned_name,
            (notes or "").strip(),
            start_date=_normalize(start_date),
            start_time=_normalize(start_time),
            end_date=_normalize(end_date),
            end_time=_normalize(end_time),
        )
        return self.refresh_state()

    def delete_season(self, name: str) -> AppState:
        cleaned = (name or "").strip()
        if not cleaned:
            raise ValueError("削除するシーズンを選択してください")
        self.db.delete_season(cleaned)
        return self.refresh_state()

    def get_match_detail(self, match_id: int) -> dict[str, object]:
        if match_id <= 0:
            raise ValueError("対戦情報 ID が不正です")
        return self.db.fetch_match(match_id)

    def update_match(self, match_id: int, payload: dict[str, object]) -> AppState:
        if match_id <= 0:
            raise ValueError("対戦情報 ID が不正です")
        updates = dict(payload or {})
        updates.pop("id", None)
        self.db.update_match(match_id, updates)
        return self.refresh_state()

    def delete_match(self, match_id: int) -> AppState:
        if match_id <= 0:
            raise ValueError("対戦情報 ID が不正です")
        self.db.delete_match(match_id)
        return self.refresh_state()

    def generate_backup_archive(self) -> tuple[str, str, str, AppState]:
        backup_dir, archive_name, archive_bytes = self.db.export_backup_zip()
        timestamp_iso = datetime.now().astimezone().isoformat()
        self.db.record_backup_path(backup_dir)
        self.db.set_metadata("last_backup_at", timestamp_iso)
        encoded = base64.b64encode(archive_bytes).decode("ascii")
        state = self.refresh_state()
        return archive_name, encoded, timestamp_iso, state

    def import_backup_archive(self, archive_bytes: bytes) -> tuple[dict[str, int], AppState]:
        restored = self.db.import_backup_archive(archive_bytes)
        state = self.refresh_state()
        return restored, state

    def reset_database(self) -> AppState:
        self.db.reset_database()
        self.db.set_schema_version(self._expected_schema_version())
        self.migration_result = ""
        self.migration_timestamp = ""
        return self.refresh_state()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _expected_schema_version(self) -> str:
        expected_version_raw = self.config.get("database", {}).get(
            "expected_version", DatabaseManager.CURRENT_SCHEMA_VERSION
        )
        return DatabaseManager.normalize_schema_version(
            expected_version_raw, fallback=DatabaseManager.CURRENT_SCHEMA_VERSION
        )

    def _handle_version_mismatch(self, current_version: str, expected_version: str) -> str:
        """Run backup and restore flow when the schema version differs."""

        lines = [
            get_text("settings.db_migration_detected").format(
                current=current_version, expected=expected_version
            )
        ]
        timestamp_iso = datetime.now().astimezone().isoformat()
        message: str

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
                message = "\n".join(
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
                message = "\n".join([get_text("settings.db_migration_success")] + lines)
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.exception("Unexpected error during schema migration")
            message = "\n".join(
                [
                    get_text("settings.db_migration_failure").format(error=str(exc)),
                    *lines,
                ]
            )

        self.db.set_metadata("last_migration_message_at", timestamp_iso)
        self.migration_timestamp = timestamp_iso
        return message


def _ensure_service() -> DuelPerformanceService:
    global _SERVICE
    if _SERVICE is None:
        service = DuelPerformanceService()
        service.bootstrap()
        _SERVICE = service
    return _SERVICE


def _format_timestamp() -> str:
    """Return the current timestamp formatted for the UI using local time."""

    return datetime.now().strftime("%H:%M:%S（%Y/%m/%d）")


def _build_snapshot(state: Optional[AppState] = None) -> dict[str, Any]:
    snapshot_source = state or get_app_state()
    data = snapshot_source.snapshot()
    data["version"] = __version__
    return data


def _operation_response(service: DuelPerformanceService, func) -> dict[str, Any]:
    try:
        state = func()
    except DuplicateEntryError as exc:
        return {"ok": False, "error": str(exc)}
    except DatabaseError as exc:
        log_db_error("Database operation failed", exc)
        return {"ok": False, "error": str(exc)}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    else:
        if isinstance(state, AppState):
            snapshot = _build_snapshot(state)
        else:
            snapshot = _build_snapshot()
        return {"ok": True, "snapshot": snapshot}


@eel.expose
def fetch_snapshot() -> dict[str, Any]:
    """Return the latest state snapshot for the front-end."""

    service = _ensure_service()
    state = service.refresh_state()
    return _build_snapshot(state)


@eel.expose
def register_deck(payload: dict[str, Any]) -> dict[str, Any]:
    service = _ensure_service()
    name = str(payload.get("name", "")) if payload else ""
    description = str(payload.get("description", "")) if payload else ""
    return _operation_response(
        service, lambda: service.register_deck(name, description)
    )


@eel.expose
def register_opponent_deck(payload: dict[str, Any]) -> dict[str, Any]:
    service = _ensure_service()
    name = str(payload.get("name", "")) if payload else ""
    return _operation_response(service, lambda: service.register_opponent_deck(name))


@eel.expose
def prepare_match(payload: dict[str, Any]) -> dict[str, Any]:
    service = _ensure_service()
    deck_name = str(payload.get("deck_name", "")) if payload else ""
    season_id = payload.get("season_id") if payload else None
    try:
        info = service.prepare_match(deck_name, season_id=season_id)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "data": info}


@eel.expose
def register_match(payload: dict[str, Any]) -> dict[str, Any]:
    service = _ensure_service()
    return _operation_response(service, lambda: service.register_match(payload or {}))


@eel.expose
def delete_deck(payload: dict[str, Any]) -> dict[str, Any]:
    service = _ensure_service()
    name = str(payload.get("name", "")) if payload else ""
    return _operation_response(service, lambda: service.delete_deck(name))


@eel.expose
def delete_opponent_deck(payload: dict[str, Any]) -> dict[str, Any]:
    service = _ensure_service()
    name = str(payload.get("name", "")) if payload else ""
    return _operation_response(service, lambda: service.delete_opponent_deck(name))


@eel.expose
def register_keyword(payload: dict[str, Any]) -> dict[str, Any]:
    service = _ensure_service()
    name = str(payload.get("name", "")) if payload else ""
    description = str(payload.get("description", "")) if payload else ""
    return _operation_response(
        service, lambda: service.register_keyword(name, description)
    )


@eel.expose
def delete_keyword(payload: dict[str, Any]) -> dict[str, Any]:
    service = _ensure_service()
    identifier = str(payload.get("identifier", "")) if payload else ""
    return _operation_response(service, lambda: service.delete_keyword(identifier))


@eel.expose
def register_season(payload: dict[str, Any]) -> dict[str, Any]:
    service = _ensure_service()
    payload = payload or {}
    name = str(payload.get("name", ""))
    notes = str(payload.get("notes", ""))
    start_date = payload.get("start_date")
    start_time = payload.get("start_time")
    end_date = payload.get("end_date")
    end_time = payload.get("end_time")
    return _operation_response(
        service,
        lambda: service.register_season(
            name,
            notes,
            start_date=start_date,
            start_time=start_time,
            end_date=end_date,
            end_time=end_time,
        ),
    )


@eel.expose
def delete_season(payload: dict[str, Any]) -> dict[str, Any]:
    service = _ensure_service()
    name = str(payload.get("name", "")) if payload else ""
    return _operation_response(service, lambda: service.delete_season(name))


@eel.expose
def get_match_detail(payload: dict[str, Any]) -> dict[str, Any]:
    service = _ensure_service()
    match_id_raw = payload.get("id") if payload else None
    try:
        match_id = int(match_id_raw)
    except (TypeError, ValueError):
        return {"ok": False, "error": "対戦情報 ID が不正です"}

    try:
        detail = service.get_match_detail(match_id)
    except (DatabaseError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}
    else:
        return {"ok": True, "data": detail}


@eel.expose
def update_match(payload: dict[str, Any]) -> dict[str, Any]:
    service = _ensure_service()
    if not payload:
        return {"ok": False, "error": "更新内容が指定されていません"}

    match_id_raw = payload.get("id")
    try:
        match_id = int(match_id_raw)
    except (TypeError, ValueError):
        return {"ok": False, "error": "対戦情報 ID が不正です"}

    updates = dict(payload)
    updates.pop("id", None)
    return _operation_response(service, lambda: service.update_match(match_id, updates))


@eel.expose
def delete_match(payload: dict[str, Any]) -> dict[str, Any]:
    service = _ensure_service()
    payload = payload or {}
    match_id_raw = payload.get("id")
    try:
        match_id = int(match_id_raw)
    except (TypeError, ValueError):
        return {"ok": False, "error": "対戦情報 ID が不正です"}
    return _operation_response(service, lambda: service.delete_match(match_id))


@eel.expose
def export_backup_archive(_: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    service = _ensure_service()
    try:
        filename, encoded, timestamp_iso, state = service.generate_backup_archive()
    except (DatabaseError, ValueError) as exc:
        log_db_error("Failed to export backup archive", exc)
        return {"ok": False, "error": str(exc)}
    snapshot = _build_snapshot(state)
    return {
        "ok": True,
        "data": {
            "filename": filename,
            "content": encoded,
            "generated_at": timestamp_iso,
        },
        "snapshot": snapshot,
    }


@eel.expose
def import_backup_archive(payload: dict[str, Any]) -> dict[str, Any]:
    service = _ensure_service()
    payload = payload or {}
    content = payload.get("content")
    if not content:
        return {"ok": False, "error": "バックアップデータが指定されていません"}
    try:
        archive_bytes = base64.b64decode(content)
    except (TypeError, ValueError) as exc:
        return {"ok": False, "error": f"バックアップデータの形式が不正です: {exc}"}
    try:
        restored, state = service.import_backup_archive(archive_bytes)
    except DatabaseError as exc:
        log_db_error("Failed to import backup archive", exc)
        return {"ok": False, "error": str(exc)}
    snapshot = _build_snapshot(state)
    return {"ok": True, "restored": restored, "snapshot": snapshot}


@eel.expose
def reset_database(_: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    service = _ensure_service()
    return _operation_response(service, service.reset_database)


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
