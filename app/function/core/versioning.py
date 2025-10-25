"""Helpers for semantic database version management.

This module centralizes schema version metadata so that migration logic and
consumers such as the CLI or UI can reason about version numbers in a single
place.  The functions primarily wrap :class:`packaging.version.Version` to
ensure consistent comparisons.
"""

from __future__ import annotations

from typing import Any
import sqlite3

from packaging.version import InvalidVersion, Version

__all__ = [
    "SCHEMA_VERSION_MAP",
    "SCHEMA_VERSION_STR_MAP",
    "TARGET_SCHEMA_VERSION",
    "TARGET_SCHEMA_VERSION_STR",
    "TARGET_SCHEMA_USER_VERSION",
    "RestoreVersionError",
    "coerce_version",
    "format_version",
    "get_db_version",
    "get_target_version",
    "normalize_version_string",
    "to_user_version",
]


class RestoreVersionError(RuntimeError):
    """Raised when schema version information cannot be interpreted."""


SCHEMA_VERSION_MAP: dict[int, Version] = {
    0: Version("0.0.0"),
    1: Version("0.3.0"),
    2: Version("0.3.1"),
    3: Version("0.3.2"),
}
"""Mapping of ``PRAGMA user_version`` integers to semantic Versions."""

SCHEMA_VERSION_STR_MAP: dict[int, str] = {
    number: str(version) for number, version in SCHEMA_VERSION_MAP.items()
}
"""String representation of :data:`SCHEMA_VERSION_MAP`."""

TARGET_SCHEMA_USER_VERSION: int = max(SCHEMA_VERSION_MAP)
"""Latest known ``user_version`` value."""

TARGET_SCHEMA_VERSION: Version = SCHEMA_VERSION_MAP[TARGET_SCHEMA_USER_VERSION]
"""Latest schema version expressed as :class:`~packaging.version.Version`."""

TARGET_SCHEMA_VERSION_STR: str = str(TARGET_SCHEMA_VERSION)
"""Latest schema version expressed as a string."""

def _int_to_version(value: int) -> Version:
    """Convert an integer ``user_version`` to a :class:`Version` instance."""

    mapped = SCHEMA_VERSION_MAP.get(value)
    if mapped is not None:
        return mapped

    safe_value = max(int(value), 0)
    major = safe_value // 10000
    minor = (safe_value // 100) % 100
    patch = safe_value % 100
    return Version(f"{major}.{minor}.{patch}")


def coerce_version(value: Any, fallback: Version | None = None) -> Version:
    """Best-effort conversion of *value* into a :class:`Version`.

    Parameters
    ----------
    value:
        Arbitrary value representing a version number.
    fallback:
        Fallback version returned when *value* cannot be interpreted.  When
        omitted, :data:`TARGET_SCHEMA_VERSION` is used.
    """

    if fallback is None:
        fallback = TARGET_SCHEMA_VERSION

    if isinstance(value, Version):
        return value

    if isinstance(value, int):
        try:
            return _int_to_version(value)
        except Exception:  # pragma: no cover - defensive
            return fallback

    if isinstance(value, (tuple, list)) and len(value) == 3:
        try:
            major, minor, patch = (int(part) for part in value)
        except (TypeError, ValueError):  # pragma: no cover - defensive
            return fallback
        return Version(f"{major}.{minor}.{patch}")

    text = "" if value is None else str(value)
    candidate = text.strip()
    if not candidate:
        return fallback

    if candidate.lower().startswith("v"):
        candidate = candidate[1:]

    try:
        return Version(candidate)
    except InvalidVersion:
        if candidate.isdigit():
            try:
                return _int_to_version(int(candidate))
            except Exception:  # pragma: no cover - defensive
                return fallback
        return fallback


def format_version(version: Version | str | int | None) -> str:
    """Return a canonical string representation for *version*."""

    return str(coerce_version(version))


def normalize_version_string(value: Any, fallback: str | Version | None = None) -> str:
    """Return :class:`str` form of :func:`coerce_version` with *fallback*."""

    fallback_version = coerce_version(fallback) if fallback is not None else TARGET_SCHEMA_VERSION
    return str(coerce_version(value, fallback=fallback_version))


def to_user_version(version: Version | str | int | None) -> int:
    """Convert *version* into the ``PRAGMA user_version`` integer."""

    coerced = coerce_version(version)
    for number, mapped in SCHEMA_VERSION_MAP.items():
        if mapped == coerced:
            return number
    return TARGET_SCHEMA_USER_VERSION


def _read_metadata_version(connection: sqlite3.Connection) -> Version | None:
    try:
        row = connection.execute(
            "SELECT value FROM db_metadata WHERE key = 'schema_version'"
        ).fetchone()
    except sqlite3.DatabaseError:
        return None

    if row and row[0]:
        return coerce_version(row[0])
    return None


def get_db_version(connection: sqlite3.Connection) -> Version:
    """Return the schema version recorded in the SQLite database."""

    try:
        row = connection.execute("PRAGMA user_version").fetchone()
    except sqlite3.DatabaseError:
        row = None

    if row:
        try:
            user_version = int(row[0])
        except (TypeError, ValueError):  # pragma: no cover - defensive
            user_version = 0
        else:
            if user_version:
                return _int_to_version(user_version)

    metadata_version = _read_metadata_version(connection)
    if metadata_version is not None:
        return metadata_version

    return TARGET_SCHEMA_VERSION


def get_target_version() -> Version:
    """Return the schema version expected by the current application."""

    return TARGET_SCHEMA_VERSION
