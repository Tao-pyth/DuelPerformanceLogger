"""Helpers for coordinating schema migrations."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from packaging.version import Version

from . import versioning

if TYPE_CHECKING:
    from app.function.cmn_database import DatabaseManager

logger = logging.getLogger(__name__)

__all__ = ["ensure_migrated"]


def ensure_migrated(manager: "DatabaseManager") -> Version:
    """Ensure *manager*'s database schema matches the expected version."""

    target = versioning.get_target_version()
    current = versioning.coerce_version(manager.get_schema_version(), fallback=target)

    if current == target:
        return current

    if current < target:
        reached = manager.migrate_semver_chain(current, target)
        manager.set_schema_version(reached)
        return reached

    logger.info(
        "Detected newer schema version %s (expected %s); skipping migrations", current, target
    )
    return current
