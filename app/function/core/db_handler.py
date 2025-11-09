"""High-level helpers for interacting with application metadata stored in SQLite."""

from __future__ import annotations

import logging
from typing import Tuple

from app.function import DatabaseManager, DatabaseError

__all__ = [
    "get_app_meta",
    "set_app_meta",
    "resolve_app_version",
]

_LOGGER = logging.getLogger(__name__)
_VERSION_WARNING_EMITTED = False


def _coerce_manager(manager: DatabaseManager | None) -> Tuple[DatabaseManager, bool]:
    """Return a database manager and whether it requires initialization."""

    if manager is not None:
        return manager, False
    return DatabaseManager(), True


def get_app_meta(key: str, *, manager: DatabaseManager | None = None) -> str | None:
    """Fetch a metadata value stored under *key* from the ``app_meta`` table."""

    db, should_initialize = _coerce_manager(manager)
    if should_initialize:
        db.ensure_database()
    else:
        db.ensure_app_meta_defaults()

    try:
        return db.get_app_meta(key)
    except DatabaseError:
        raise
    except Exception as exc:  # pragma: no cover - defensive guard
        _LOGGER.error("Failed to read app_meta[%s]", key, exc_info=exc)
        raise DatabaseError(f"Failed to read app meta '{key}'") from exc


def set_app_meta(
    key: str, value: str, *, manager: DatabaseManager | None = None
) -> None:
    """Persist *value* under *key* within the ``app_meta`` table."""

    db, should_initialize = _coerce_manager(manager)
    if should_initialize:
        db.ensure_database()
    else:
        db.ensure_app_meta_defaults()

    try:
        db.set_app_meta(key, str(value))
    except DatabaseError:
        raise
    except Exception as exc:  # pragma: no cover - defensive guard
        _LOGGER.error("Failed to write app_meta[%s]", key, exc_info=exc)
        raise DatabaseError(f"Failed to write app meta '{key}'") from exc


def resolve_app_version(
    fallback: str,
    *,
    manager: DatabaseManager | None = None,
    warn_on_missing: bool = True,
) -> str:
    """Return the canonical application version stored in ``app_meta``.

    When the value is missing or cannot be retrieved, *fallback* is returned.
    The first such fallback emits a warning log so that release procedures can
    detect configuration drift.
    """

    global _VERSION_WARNING_EMITTED

    try:
        value = get_app_meta("app_version", manager=manager)
    except DatabaseError as exc:
        _LOGGER.warning(
            "Failed to fetch app_version from database; using fallback", exc_info=exc
        )
        value = None

    if value:
        return value

    if warn_on_missing and not _VERSION_WARNING_EMITTED:
        _LOGGER.warning(
            "app_meta.app_version is missing; falling back to %s", fallback
        )
        _VERSION_WARNING_EMITTED = True

    return str(fallback)
