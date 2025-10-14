"""Application state helpers for the Eel-based user interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, TYPE_CHECKING

from .cmn_config import load_config

if TYPE_CHECKING:  # pragma: no cover - import guard for type checking only
    from .cmn_database import DatabaseManager


@dataclass
class AppState:
    """Container object representing the current application state."""

    config: dict[str, Any] = field(default_factory=dict)
    ui_mode: str = "normal"
    decks: list[dict[str, Any]] = field(default_factory=list)
    seasons: list[dict[str, Any]] = field(default_factory=list)
    match_records: list[dict[str, Any]] = field(default_factory=list)
    opponent_decks: list[dict[str, Any]] = field(default_factory=list)
    keywords: list[dict[str, Any]] = field(default_factory=list)
    current_match_settings: Optional[dict[str, Any]] = None
    current_match_count: int = 0
    migration_result: str = ""
    migration_timestamp: str = ""
    last_backup_path: str = ""
    last_backup_at: str = ""
    database_path: str = ""
    db: Optional["DatabaseManager"] = None

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation of the current state."""

        return {
            "config": self.config,
            "ui_mode": self.ui_mode,
            "decks": self.decks,
            "seasons": self.seasons,
            "matches": self.match_records,
            "opponent_decks": self.opponent_decks,
            "keywords": self.keywords,
            "current_match_settings": self.current_match_settings,
            "current_match_count": self.current_match_count,
            "migration_result": self.migration_result,
            "migration_timestamp": self.migration_timestamp,
            "last_backup_path": self.last_backup_path,
            "last_backup_at": self.last_backup_at,
            "database_path": self.database_path,
        }

    def clone(self) -> "AppState":
        """Create a deep-ish copy of the state for safe external use."""

        return AppState(
            config=dict(self.config),
            ui_mode=self.ui_mode,
            decks=[dict(item) for item in self.decks],
            seasons=[dict(item) for item in self.seasons],
            match_records=[dict(item) for item in self.match_records],
            opponent_decks=[dict(item) for item in self.opponent_decks],
            keywords=[dict(item) for item in self.keywords],
            current_match_settings=(
                dict(self.current_match_settings) if self.current_match_settings else None
            ),
            current_match_count=self.current_match_count,
            migration_result=self.migration_result,
            migration_timestamp=self.migration_timestamp,
            last_backup_path=self.last_backup_path,
            last_backup_at=self.last_backup_at,
            database_path=self.database_path,
            db=self.db,
        )


_state = AppState(config=load_config())


def get_app_state() -> AppState:
    """Return the current global :class:`AppState` instance."""

    return _state


def set_app_state(state: AppState) -> AppState:
    """Replace the global application state with *state* and return it."""

    global _state
    _state = state
    return _state


def reset_app_state() -> AppState:
    """Reset the global state to a fresh configuration baseline."""

    global _state
    _state = AppState(config=load_config())
    return _state


def build_state(
    db: "DatabaseManager",
    config: Mapping[str, Any],
    *,
    migration_result: str = "",
    migration_timestamp: str = "",
) -> AppState:
    """Create an :class:`AppState` filled with the latest DB snapshot."""

    state = AppState(
        config=dict(config),
        ui_mode=db.get_ui_mode(),
        decks=db.fetch_decks(),
        seasons=db.fetch_seasons(),
        match_records=db.fetch_matches(),
        opponent_decks=db.fetch_opponent_decks(),
        keywords=db.fetch_keywords(),
        current_match_settings=None,
        current_match_count=0,
        migration_result=migration_result,
        migration_timestamp=migration_timestamp,
        last_backup_path=db.get_metadata("last_backup", "") or "",
        last_backup_at=db.get_metadata("last_backup_at", "") or "",
        database_path=str(db.db_path),
        db=db,
    )
    return state


__all__ = [
    "AppState",
    "build_state",
    "get_app_state",
    "reset_app_state",
    "set_app_state",
]
