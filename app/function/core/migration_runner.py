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
    """DB スキーマを期待バージョンへ整合させ、結果のバージョンを返します。

    入力
        manager: :class:`DatabaseManager`
            スキーマ更新対象のデータベースマネージャー。
    出力
        :class:`Version`
            マイグレーション適用後（またはスキップ後）の確定バージョン。
    処理概要
        1. 現在のスキーマバージョンとターゲットバージョンを取得・比較します。
        2. 一致した場合はログのみ記録してそのまま返します。
        3. ターゲットが上回る場合のみ逐次マイグレーションを実行します。
        4. DB 側がターゲットより新しい場合は設計上の前提としてダウングレード
           を禁止し、バックアップ等も行わずメッセージだけを残します。
    例外
        manager.migrate_semver_chain の実行中に発生した例外をそのまま送出します。
    """

    target = versioning.get_target_version()
    current = versioning.coerce_version(manager.get_schema_version(), fallback=target)

    logger.info("[DB] current=%s target=%s (current>target? %s)", current, target, current > target)

    if current == target:
        logger.info("[DB] Database is already at the expected schema version; no migration executed.")
        return current

    if current > target:
        logger.info(
            "[DB] Upper DB detected. current=%s > target=%s. Migration skipped.", current, target
        )
        return current

    # current < target の場合のみ順方向マイグレーションを実施する。
    reached = manager.migrate_semver_chain(current, target)
    manager.set_schema_version(reached)
    logger.info("[DB] Applied forward migrations from %s to %s.", current, reached)
    return reached
