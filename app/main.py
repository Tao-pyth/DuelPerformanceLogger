"""Eel ベースの UI とバックエンドサービスを橋渡しするエントリーポイント。

記載内容
    - :class:`DuelPerformanceService` クラス: データベースとアプリ状態の調停役。
    - Eel へ公開される関数群: UI から呼び出される各種操作 API。
    - アプリケーション起動関数 :func:`main`。

想定参照元
    - ``resource/web`` 配下の JavaScript から ``eel.<function>`` 経由で呼び出し。
    - テストコードやスクリプトがサービス層の振る舞いを検証する際の直接利用。
"""

from __future__ import annotations

import logging
import os
import base64
import sqlite3
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
from app.function.core import paths, versioning
from app.function.core.backup_restore import RestoreReport
from app.function.core.version import __version__

logger = logging.getLogger(__name__)
_WEB_ROOT = paths.web_root()
_INDEX_FILE = "index.html"
_SERVICE: Optional["DuelPerformanceService"] = None


class DuelPerformanceService:
    """データベース操作とアプリ状態生成を一手に担うサービス層クラス。

    役割
        - DB マネージャーを初期化し、マイグレーションやバックアップ処理をラップする。
        - 画面で必要な最新の :class:`AppState` を組み立て、Eel 経由の API に提供する。

    想定利用箇所
        - 本モジュール内の ``@eel.expose`` 関数から委譲される操作。
        - CLI やテストでバックエンドの単体検証を行う際の直接呼び出し。
    """

    def __init__(self) -> None:
        """サービス起動時の構成要素を初期化します。

        入力
            引数はありません。
        出力
            ``None``
                副作用として設定情報と DB 接続が初期化されます。
        処理概要
            1. 設定ファイルを読み込み :class:`DatabaseManager` を生成。
            2. データベースの存在チェックとマイグレーション結果の取得を実施。
            3. マイグレーション状態に応じてメッセージとタイムスタンプを保持します。
        """
        self.config = load_config()
        self.db = DatabaseManager()
        try:
            self.db.ensure_database()
        except (sqlite3.DatabaseError, DatabaseError) as exc:
            self.migration_result = self._handle_startup_migration_failure(exc)
        else:
            self.migration_result = (
                self.db.get_metadata("last_migration_message", "") or ""
            )
        self.migration_timestamp = (
            self.db.get_metadata("last_migration_message_at", "") or ""
        )

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------
    def bootstrap(self) -> AppState:
        """データベースを再確認して初期状態を構築します。

        入力
            引数はありません。
        出力
            :class:`AppState`
                UI へ供給する初期スナップショット。
        処理概要
            1. :meth:`DatabaseManager.ensure_database` を冪等に再実行し、
               起動直前のマイグレーション状態を保証します。
            2. スキーマバージョンを検証し、不一致ならバックアップ→再構築フローへ委譲します。
            3. 最新のメタデータを反映した :class:`AppState` を返却します。
        """
        # --- A) 強制プリフライト（冪等） ---
        try:
            self.db.ensure_database()  # ※ __init__ 側で実行済みでも冪等
        except (sqlite3.DatabaseError, DatabaseError) as exc:
            # 既存の復旧ルートに委譲（バックアップ→再構築→復元 等）
            self.migration_result = self._handle_startup_migration_failure(exc)

        # --- バージョン整合性チェック（既存ハンドラ利用） ---
        target_version = self._expected_schema_version()
        current_version = self.db.get_schema_version()
        current_semver = versioning.coerce_version(current_version)
        target_semver = versioning.coerce_version(
            target_version, fallback=current_semver
        )

        if current_semver < target_semver:
            self.migration_result = self._handle_version_mismatch(
                current_version, target_version
            )
        elif current_semver == target_semver:
            message = get_text("settings.db_migration_up_to_date")
            self._record_migration_message(message)
            self.db.set_schema_version(target_semver)
        else:
            # DB 側がターゲットより新しい場合は明示的にスキップメッセージのみ通知する。
            message = get_text("settings.db_migration_upper_detected").format(
                current=current_version, target=target_version
            )
            self._record_migration_message(message)

        # --- 起動後の AppState 構築 ---
        return self.refresh_state()

    def refresh_state(self) -> AppState:
        """データベースから最新情報を取得しアプリ状態を更新します。

        入力
            引数はありません。
        出力
            :class:`AppState`
                取得直後の状態オブジェクト。:func:`set_app_state` の結果を返します。
        処理概要
            1. :func:`build_state` を用いて DB から各種リストを取得。
            2. マイグレーション結果やバックアップ情報を埋め込んだ状態を生成します。
            3. グローバル状態へ反映したうえで返却します。
        """

        state = build_state(
            self.db,
            self.config,
            migration_result=self.migration_result,
            migration_timestamp=self.migration_timestamp,
        )
        return set_app_state(state)

    def _record_migration_message(self, message: str) -> None:
        """マイグレーション結果メッセージをメタデータと状態へ記録します。

        入力
            message: ``str``
                ユーザーへ提示するメッセージ本文。
        出力
            ``None``
                副作用としてメタデータおよび :class:`AppState` 相当の属性を更新します。
        処理概要
            1. 現在時刻を取得し ISO 形式でタイムスタンプを作成します。
            2. ``last_migration_message``/``last_migration_message_at`` メタデータへ保存します。
            3. :attr:`migration_result` と :attr:`migration_timestamp` を更新します。
        例外
            なし。
        """

        timestamp_iso = datetime.now().astimezone().isoformat()
        self.db.set_metadata("last_migration_message", message)
        self.db.set_metadata("last_migration_message_at", timestamp_iso)
        self.migration_result = message
        self.migration_timestamp = timestamp_iso

    # ------------------------------------------------------------------
    # Application operations
    # ------------------------------------------------------------------
    def register_deck(self, name: str, description: str) -> AppState:
        """新しいデッキを登録し最新状態を返します。

        入力
            name: ``str``
                登録するデッキ名。空文字の場合は例外を送出します。
            description: ``str``
                デッキの説明。未入力時は空文字として扱います。
        出力
            :class:`AppState`
                登録後に再構築したアプリ状態。
        処理概要
            1. 文字列をトリムして必須入力を検証します。
            2. :meth:`DatabaseManager.add_deck` へ登録処理を委譲します。
            3. :meth:`refresh_state` で最新状態を返却します。
        """
        cleaned_name = (name or "").strip()
        if not cleaned_name:
            raise ValueError("デッキ名を入力してください")
        cleaned_description = (description or "").strip()
        self.db.add_deck(cleaned_name, cleaned_description)
        return self.refresh_state()

    def register_opponent_deck(self, name: str) -> AppState:
        """対戦相手デッキを登録し最新状態を返します。

        入力
            name: ``str``
                対戦相手デッキ名。空文字の場合は例外を送出します。
        出力
            :class:`AppState`
                登録後のアプリ状態。
        処理概要
            1. 入力文字列のトリムと必須チェックを実施。
            2. :meth:`DatabaseManager.add_opponent_deck` で保存。
            3. :meth:`refresh_state` を呼び最新状態を返却します。
        """
        cleaned_name = (name or "").strip()
        if not cleaned_name:
            raise ValueError("対戦相手デッキ名を入力してください")
        self.db.add_opponent_deck(cleaned_name)
        return self.refresh_state()

    def prepare_match(
        self, deck_name: str, season_id: Optional[int] = None
    ) -> dict[str, object]:
        """対戦登録前に必要な番号やタイムスタンプを提供します。

        入力
            deck_name: ``str``
                対戦を行う自分のデッキ名。必須項目です。
            season_id: ``Optional[int]``
                既存シーズンを選択した場合の ID。空値は ``None`` として扱います。
        出力
            ``dict[str, object]``
                ``deck_name``、``next_match_no``、``timestamp``、``season_id`` を含む辞書。
        処理概要
            1. デッキ名を必須チェックし、DB から次の対戦番号を取得。
            2. 現在時刻を UI 表示用の文字列に整形。
            3. シーズン ID の整合性を検証し、正規化した情報をまとめて返却します。
        """
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
        """対戦結果を保存し状態を更新します。

        入力
            payload: ``dict[str, object]``
                対戦登録画面から送信された辞書。デッキ名や結果、キーワード等を含みます。
        出力
            :class:`AppState`
                登録後に再構築した状態。
        処理概要
            1. デッキ名・先攻後攻・勝敗など必須項目の妥当性を検証します。
            2. キーワードやシーズン ID を正規化し、登録用辞書 ``match_record`` を生成します。
            3. :meth:`DatabaseManager.record_match` を呼び出し、処理後に :meth:`refresh_state` を返します。
        """
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
        memo = str(payload.get("memo", "") or "")
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
            "memo": memo,
            "result": int(result),
            "season_id": normalized_season_id,
        }
        if normalized_season_id is None and season_name:
            match_record["season_name"] = season_name

        self.db.record_match(match_record)
        return self.refresh_state()

    def delete_deck(self, name: str) -> AppState:
        """指定されたデッキを削除し状態を更新します。

        入力
            name: ``str``
                削除対象のデッキ名。空文字は許容されません。
        出力
            :class:`AppState`
                削除後に再取得した状態。
        処理概要
            1. 引数をトリムし空の場合は :class:`ValueError` を送出します。
            2. :meth:`DatabaseManager.delete_deck` で削除処理を実行。
            3. :meth:`refresh_state` の結果を返します。
        """
        cleaned = (name or "").strip()
        if not cleaned:
            raise ValueError("削除するデッキを選択してください")
        self.db.delete_deck(cleaned)
        return self.refresh_state()

    def delete_opponent_deck(self, name: str) -> AppState:
        """対戦相手デッキを削除し状態を更新します。

        入力
            name: ``str``
                削除したい相手デッキ名。空文字は無効です。
        出力
            :class:`AppState`
                削除後の状態。
        処理概要
            1. 文字列をトリムし、空の場合は :class:`ValueError` を送出。
            2. :meth:`DatabaseManager.delete_opponent_deck` で削除処理。
            3. :meth:`refresh_state` を呼び最新状態を返します。
        """
        cleaned = (name or "").strip()
        if not cleaned:
            raise ValueError("削除する対戦相手デッキを選択してください")
        self.db.delete_opponent_deck(cleaned)
        return self.refresh_state()

    def register_keyword(self, name: str, description: str) -> AppState:
        """キーワードを登録し状態を更新します。

        入力
            name: ``str``
                登録するキーワード名。必須。
            description: ``str``
                補足説明文。空文字可。
        出力
            :class:`AppState`
                登録後の状態。
        処理概要
            1. キーワード名を必須チェック。
            2. :meth:`DatabaseManager.add_keyword` で保存。
            3. :meth:`refresh_state` の結果を返します。
        """
        cleaned_name = (name or "").strip()
        if not cleaned_name:
            raise ValueError("キーワード名を入力してください")
        cleaned_description = (description or "").strip()
        self.db.add_keyword(cleaned_name, cleaned_description)
        return self.refresh_state()

    def delete_keyword(self, identifier: str) -> AppState:
        """キーワードを削除して状態を更新します。

        入力
            identifier: ``str``
                削除対象のキーワード ID または名称。
        出力
            :class:`AppState`
                削除後の状態。
        処理概要
            1. 文字列をトリムし空であれば :class:`ValueError` を送出。
            2. :meth:`DatabaseManager.delete_keyword` に削除を委譲。
            3. :meth:`refresh_state` の結果を返します。
        """
        cleaned = (identifier or "").strip()
        if not cleaned:
            raise ValueError("削除するキーワードを選択してください")
        self.db.delete_keyword(cleaned)
        return self.refresh_state()

    def set_keyword_visibility(self, identifier: str, hidden: bool) -> AppState:
        """キーワードの表示状態を切り替えて状態を更新します。"""

        cleaned = (identifier or "").strip()
        if not cleaned:
            raise ValueError("キーワードを選択してください")
        self.db.set_keyword_visibility(cleaned, hidden)
        return self.refresh_state()

    def register_season(
        self,
        name: str,
        notes: str = "",
        *,
        rank_statistics_target: bool | str | int = False,
        start_date: Optional[str] = None,
        start_time: Optional[str] = None,
        end_date: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> AppState:
        """シーズン情報を登録し最新状態を返します。

        入力
            name: ``str``
                シーズン名称。必須。
            notes: ``str``
                備考テキスト。任意。
            start_date / start_time / end_date / end_time: ``Optional[str]``
                開始・終了日時の文字列。空文字は ``None`` に正規化します。
        出力
            :class:`AppState`
                登録後の状態。
        処理概要
            1. シーズン名の必須チェックを実施。
            2. 日付・時刻を正規化する内部関数 ``_normalize`` を利用。
            3. ランク統計対象フラグを正規化し、:meth:`DatabaseManager.add_season` で保存。
            4. :meth:`refresh_state` を返します。
        """
        cleaned_name = (name or "").strip()
        if not cleaned_name:
            raise ValueError("シーズン名を入力してください")

        def _normalize(value: Optional[str]) -> Optional[str]:
            text = (value or "").strip()
            return text or None

        def _normalize_flag(value: object) -> bool:
            if isinstance(value, str):
                normalized = value.strip().lower()
                return normalized in {"1", "true", "yes", "on", "t", "y"}
            if isinstance(value, (int, float)):
                try:
                    return int(value) != 0
                except (TypeError, ValueError):
                    return False
            return bool(value)

        self.db.add_season(
            cleaned_name,
            (notes or "").strip(),
            rank_statistics_target=_normalize_flag(rank_statistics_target),
            start_date=_normalize(start_date),
            start_time=_normalize(start_time),
            end_date=_normalize(end_date),
            end_time=_normalize(end_time),
        )
        return self.refresh_state()

    def delete_season(self, name: str) -> AppState:
        """シーズン情報を削除し状態を更新します。

        入力
            name: ``str``
                削除対象のシーズン名。
        出力
            :class:`AppState`
                削除後の状態。
        処理概要
            1. 引数をトリムし空の場合は :class:`ValueError` を送出。
            2. :meth:`DatabaseManager.delete_season` を呼び出します。
            3. :meth:`refresh_state` を返します。
        """
        cleaned = (name or "").strip()
        if not cleaned:
            raise ValueError("削除するシーズンを選択してください")
        self.db.delete_season(cleaned)
        return self.refresh_state()

    def get_match_detail(self, match_id: int) -> dict[str, object]:
        """対戦記録の詳細を取得します。

        入力
            match_id: ``int``
                対戦レコードの主キー。1 以上である必要があります。
        出力
            ``dict[str, object]``
                DB から取得した対戦情報。
        処理概要
            1. ID の妥当性をチェックし、0 以下なら :class:`ValueError` を送出。
            2. :meth:`DatabaseManager.fetch_match` を呼び出し、その結果を返します。
        """
        if match_id <= 0:
            raise ValueError("対戦情報 ID が不正です")
        return self.db.fetch_match(match_id)

    def update_match(self, match_id: int, payload: dict[str, object]) -> AppState:
        """対戦記録を更新し状態を再構築します。

        入力
            match_id: ``int``
                更新対象の対戦 ID。
            payload: ``dict[str, object]``
                更新内容。``id`` キーは無視されます。
        出力
            :class:`AppState`
                更新後の状態。
        処理概要
            1. ID の妥当性を検証し 0 以下なら :class:`ValueError` を送出。
            2. 更新用辞書から ``id`` を除去し :meth:`DatabaseManager.update_match` を実行。
            3. :meth:`refresh_state` で最新状態を返します。
        """
        if match_id <= 0:
            raise ValueError("対戦情報 ID が不正です")
        updates = dict(payload or {})
        updates.pop("id", None)
        self.db.update_match(match_id, updates)
        return self.refresh_state()

    def delete_match(self, match_id: int) -> AppState:
        """対戦記録を削除し状態を更新します。

        入力
            match_id: ``int``
                削除対象の ID。1 以上が必要です。
        出力
            :class:`AppState`
                削除後の状態。
        処理概要
            1. ID の妥当性を確認し、0 以下は :class:`ValueError` を送出。
            2. :meth:`DatabaseManager.delete_match` を呼び出します。
            3. :meth:`refresh_state` で最新状態を返します。
        """
        if match_id <= 0:
            raise ValueError("対戦情報 ID が不正です")
        self.db.delete_match(match_id)
        return self.refresh_state()

    def generate_backup_archive(self) -> tuple[str, str, str, AppState]:
        """バックアップアーカイブを生成し状態を更新します。

        入力
            引数はありません。
        出力
            ``tuple[str, str, str, AppState]``
                (ファイル名, Base64 文字列, 生成時刻 ISO, 更新後状態)。
        処理概要
            1. :meth:`DatabaseManager.export_backup_zip` で ZIP を取得し Base64 化します。
            2. バックアップ保存先パスを記録し、メタデータ ``last_backup_at`` を更新します。
            3. :meth:`refresh_state` で状態を再構築し結果タプルを返却します。
        """
        backup_dir, archive_name, archive_bytes = self.db.export_backup_zip()
        timestamp_iso = datetime.now().astimezone().isoformat()
        self.db.record_backup_path(backup_dir)
        self.db.set_metadata("last_backup_at", timestamp_iso)
        encoded = base64.b64encode(archive_bytes).decode("ascii")
        state = self.refresh_state()
        return archive_name, encoded, timestamp_iso, state

    def import_backup_archive(
        self,
        archive_bytes: bytes,
        *,
        mode: str = "full",
        dry_run: bool = False,
    ) -> tuple[RestoreReport, AppState]:
        """バックアップアーカイブを取り込み状態を更新します。"""

        report = self.db.import_backup_archive(
            archive_bytes, mode=mode, dry_run=dry_run
        )
        state = self.refresh_state()
        return report, state

    def reset_database(self) -> AppState:
        """データベースを初期化し状態を再構築します。

        入力
            引数はありません。
        出力
            :class:`AppState`
                初期化後の状態。
        処理概要
            1. :meth:`DatabaseManager.reset_database` でテーブルを再生成。
            2. スキーマバージョンとマイグレーションメタデータを既定値へ更新。
            3. :meth:`refresh_state` を呼び直後の状態を返します。
        """
        self.db.reset_database()
        self.db.set_schema_version(self._expected_schema_version())
        self.db.set_metadata("last_migration_message", "")
        self.db.set_metadata("last_migration_message_at", "")
        self.migration_result = ""
        self.migration_timestamp = ""
        return self.refresh_state()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _expected_schema_version(self) -> str:
        """設定から期待するスキーマバージョンを取得します。

        入力
            引数はありません。
        出力
            ``str``
                設定ファイルに定義された期待バージョン。無効時は現在バージョン。
        処理概要
            1. コンフィグから ``database.expected_version`` を参照。
            2. :meth:`DatabaseManager.normalize_schema_version` で整形し返却します。
        """
        expected_version_raw = self.config.get("database", {}).get(
            "expected_version", DatabaseManager.CURRENT_SCHEMA_VERSION
        )
        return DatabaseManager.normalize_schema_version(
            expected_version_raw, fallback=DatabaseManager.CURRENT_SCHEMA_VERSION
        )

    def _format_restore_lines(self, report: RestoreReport) -> list[str]:
        """復元結果をユーザー通知用メッセージへ整形します。"""

        lines = [
            get_text("settings.db_migration_restore_success").format(
                decks=report.restored.get("decks", 0),
                seasons=report.restored.get("seasons", 0),
                matches=report.restored.get("matches", 0),
            ),
            get_text("settings.db_restore_failure_count").format(
                count=len(report.failures)
            ),
        ]
        if report.log_path:
            lines.append(
                get_text("settings.db_restore_log_path").format(
                    path=str(report.log_path)
                )
            )
        return lines

    def _handle_version_mismatch(self, current_version: str, target_version: str) -> str:
        """スキーマバージョン不一致時のバックアップ/復元処理を実行します。

        入力
            current_version: ``str``
                DB に記録されているスキーマバージョン。
            target_version: ``str``
                アプリが期待するスキーマバージョン。
        出力
            ``str``
                ユーザーへ表示するマイグレーション結果メッセージ。
        処理概要
            1. 事前メッセージを組み立てつつバックアップをエクスポートし、復元ログを追加。
            2. スキーマ初期化後、バックアップを再インポートして成功/失敗メッセージを構築。
            3. メタデータへ結果と実行時刻を保存し、整形済みメッセージを返します。
        """

        lines = [
            get_text("settings.db_migration_detected").format(
                current=current_version, target=target_version
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
            self.db.set_schema_version(target_version)

            try:
                report = self.db.import_backup(backup_path)
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
                last_report = self.db.last_restore_report
                if last_report:
                    lines.append(
                        get_text("settings.db_restore_failure_count").format(
                            count=len(last_report.failures)
                        )
                    )
                    if last_report.log_path:
                        lines.append(
                            get_text("settings.db_restore_log_path").format(
                                path=str(last_report.log_path)
                            )
                        )
                message = "\n".join(
                    [get_text("settings.db_migration_failure").format(error=str(exc))]
                    + lines
                )
            else:
                lines.extend(self._format_restore_lines(report))
                message = "\n".join([get_text("settings.db_migration_success")] + lines)
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.exception("Unexpected error during schema migration")
            message = "\n".join(
                [
                    get_text("settings.db_migration_failure").format(error=str(exc)),
                    *lines,
                ]
            )

        self.db.set_metadata("last_migration_message", message)
        self.db.set_metadata("last_migration_message_at", timestamp_iso)
        self.migration_timestamp = timestamp_iso
        return message

    def _handle_startup_migration_failure(self, error: Exception) -> str:
        """起動時のマイグレーション失敗から自動復旧を試みます。

        入力
            error: :class:`Exception`
                マイグレーション失敗時に捕捉した例外。
        出力
            ``str``
                復旧フローの結果メッセージ。
        処理概要
            1. 失敗内容をログに残し、バックアップのエクスポートと復旧準備を実行。
            2. データベースを初期化後、バックアップ復元を試行し結果を蓄積。
            3. メタデータへ結果とタイムスタンプを記録し、メッセージを返します。
        """

        timestamp_iso = datetime.now().astimezone().isoformat()
        lines = [
            get_text("settings.db_migration_auto_recovery").format(error=str(error))
        ]

        log_db_error("Automatic schema recovery triggered", error)

        backup_path = None
        try:
            backup_path = self.db.export_backup()
            self.db.record_backup_path(backup_path)
            self.db.set_metadata("last_backup_at", timestamp_iso)
            lines.append(
                get_text("settings.db_migration_backup").format(path=str(backup_path))
            )
        except Exception as backup_exc:  # pragma: no cover - defensive
            log_db_error("Failed to export backup during auto recovery", backup_exc)
            lines.append(
                get_text("settings.db_migration_backup_failed").format(
                    error=str(backup_exc)
                )
            )

        self.db.initialize_database()
        self.db.set_schema_version(self._expected_schema_version())
        lines.append(get_text("settings.db_migration_reset_performed"))

        if backup_path is not None:
            try:
                report = self.db.import_backup(backup_path)
            except DatabaseError as exc:
                log_db_error(
                    "Failed to restore database during auto recovery",
                    exc,
                    backup=str(backup_path),
                )
                lines.append(
                    get_text("settings.db_migration_restore_failed").format(
                        error=str(exc)
                    )
                )
                last_report = self.db.last_restore_report
                if last_report:
                    lines.append(
                        get_text("settings.db_restore_failure_count").format(
                            count=len(last_report.failures)
                        )
                    )
                    if last_report.log_path:
                        lines.append(
                            get_text("settings.db_restore_log_path").format(
                                path=str(last_report.log_path)
                            )
                        )
            else:
                lines.extend(self._format_restore_lines(report))

        message = "\n".join(lines)
        self.db.set_metadata("last_migration_message", message)
        self.db.set_metadata("last_migration_message_at", timestamp_iso)
        self.migration_timestamp = timestamp_iso
        return message


def _ensure_service() -> DuelPerformanceService:
    """シングルトンな :class:`DuelPerformanceService` インスタンスを取得します。

    入力
        引数はありません。
    出力
        :class:`DuelPerformanceService`
            既存インスタンス。未生成の場合は初期化と :meth:`bootstrap` を実行します。
    処理概要
        1. グローバル変数 ``_SERVICE`` を確認し未設定なら新規生成。
        2. 起動時に :meth:`bootstrap` で状態を整え、インスタンスをキャッシュして返却します。
    """
    global _SERVICE
    if _SERVICE is None:
        service = DuelPerformanceService()
        service.bootstrap()
        _SERVICE = service
    return _SERVICE


def _format_timestamp() -> str:
    """ローカル時刻を UI 用の文字列に整形して返します。

    入力
        引数はありません。
    出力
        ``str``
            ``HH:MM:SS（YYYY/MM/DD）`` 形式の文字列。
    処理概要
        1. 現在日時を取得し所定のフォーマットで ``strftime`` します。
    """

    return datetime.now().strftime("%H:%M:%S（%Y/%m/%d）")


def _build_snapshot(state: Optional[AppState] = None) -> dict[str, Any]:
    """AppState から UI 用スナップショット辞書を構築します。

    入力
        state: ``Optional[AppState]``
            スナップショット化したい状態。未指定時は :func:`get_app_state` を利用します。
    出力
        ``dict[str, Any]``
            Eel へ返却する JSON 互換辞書。``ok`` や ``snapshot`` とは別管理です。
    処理概要
        1. 渡された状態もしくはグローバル状態から :meth:`AppState.clone` 相当の情報を取得。
        2. ``migration_result`` など UI で利用する補助情報も含めた辞書を返します。
    """
    snapshot_source = state or get_app_state()
    data = snapshot_source.snapshot()
    data["version"] = __version__
    return data


def _operation_response(service: DuelPerformanceService, func) -> dict[str, Any]:
    """操作実行とレスポンス整形を共通化します。

    入力
        service: :class:`DuelPerformanceService`
            スナップショット生成に利用するサービスインスタンス。
        func: ``Callable``
            実際の操作関数。戻り値は :class:`AppState` もしくはその他の値を想定します。
    出力
        ``dict[str, Any]``
            ``{"ok": True/False, ...}`` 形式のレスポンス辞書。
    処理概要
        1. 操作を実行し、想定済みの例外を捕捉してエラーメッセージへ変換。
        2. 成功時は :func:`_build_snapshot` を用いて最新状態を添付します。
    """
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
    """フロントエンドへ最新スナップショットを返します。

    入力
        引数はありません。
    出力
        ``dict[str, Any]``
            現在の状態を ``snapshot`` キーに含む辞書。
    処理概要
        1. :func:`_ensure_service` でサービスを取得。
        2. :meth:`DuelPerformanceService.refresh_state` の結果を :func:`_build_snapshot` に渡して返却します。
    """

    service = _ensure_service()
    state = service.refresh_state()
    return _build_snapshot(state)


@eel.expose
def register_deck(payload: dict[str, Any]) -> dict[str, Any]:
    """UI から送信されたデッキ登録要求を処理します。

    入力
        payload: ``dict[str, Any]``
            ``name`` と ``description`` を含むリクエスト辞書。
    出力
        ``dict[str, Any]``
            成功可否と最新スナップショットを含むレスポンス。
    処理概要
        1. サービスを取得し入力値を抽出。
        2. :func:`_operation_response` を介して例外処理とスナップショット生成を統一します。
    """
    service = _ensure_service()
    name = str(payload.get("name", "")) if payload else ""
    description = str(payload.get("description", "")) if payload else ""
    return _operation_response(
        service, lambda: service.register_deck(name, description)
    )


@eel.expose
def register_opponent_deck(payload: dict[str, Any]) -> dict[str, Any]:
    """UI からの対戦相手デッキ登録要求を処理します。

    入力
        payload: ``dict[str, Any]``
            ``name`` を含む辞書。
    出力
        ``dict[str, Any]``
            成功可否と最新スナップショット。
    処理概要
        1. サービスを取得し名前を抽出。
        2. :func:`_operation_response` で登録処理とレスポンス生成を行います。
    """
    service = _ensure_service()
    name = str(payload.get("name", "")) if payload else ""
    return _operation_response(service, lambda: service.register_opponent_deck(name))


@eel.expose
def prepare_match(payload: dict[str, Any]) -> dict[str, Any]:
    """対戦登録画面の事前情報を取得します。

    入力
        payload: ``dict[str, Any]``
            ``deck_name`` と任意の ``season_id`` を含む辞書。
    出力
        ``dict[str, Any]``
            ``ok`` フラグと対戦番号などのデータを格納。
    処理概要
        1. サービスへ委譲し対戦番号やタイムスタンプを算出。
        2. バリデーションエラーは ``ok=False`` とメッセージで返却します。
    """
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
    """対戦結果登録リクエストを処理します。

    入力
        payload: ``dict[str, Any]``
            対戦情報一式。
    出力
        ``dict[str, Any]``
            処理結果とスナップショット。
    処理概要
        1. サービスへ辞書を渡し :meth:`DuelPerformanceService.register_match` を実行。
        2. :func:`_operation_response` でエラー整形と状態更新を行います。
    """
    service = _ensure_service()
    return _operation_response(service, lambda: service.register_match(payload or {}))


@eel.expose
def delete_deck(payload: dict[str, Any]) -> dict[str, Any]:
    """デッキ削除リクエストを処理します。

    入力
        payload: ``dict[str, Any]``
            ``name`` を含む辞書。
    出力
        ``dict[str, Any]``
            成功可否とスナップショット。
    処理概要
        1. サービスへ削除対象名を渡し :func:`_operation_response` で結果を組み立てます。
    """
    service = _ensure_service()
    name = str(payload.get("name", "")) if payload else ""
    return _operation_response(service, lambda: service.delete_deck(name))


@eel.expose
def delete_opponent_deck(payload: dict[str, Any]) -> dict[str, Any]:
    """対戦相手デッキ削除リクエストを処理します。

    入力
        payload: ``dict[str, Any]``
            ``name`` を含む辞書。
    出力
        ``dict[str, Any]``
            成功可否とスナップショット。
    処理概要
        1. サービスへ削除対象名を渡し :func:`_operation_response` を適用します。
    """
    service = _ensure_service()
    name = str(payload.get("name", "")) if payload else ""
    return _operation_response(service, lambda: service.delete_opponent_deck(name))


@eel.expose
def register_keyword(payload: dict[str, Any]) -> dict[str, Any]:
    """キーワード登録リクエストを処理します。

    入力
        payload: ``dict[str, Any]``
            ``name`` と ``description`` を含む辞書。
    出力
        ``dict[str, Any]``
            成功可否とスナップショット。
    処理概要
        1. 入力値を抽出し :func:`_operation_response` で登録とレスポンス生成を行います。
    """
    service = _ensure_service()
    name = str(payload.get("name", "")) if payload else ""
    description = str(payload.get("description", "")) if payload else ""
    return _operation_response(
        service, lambda: service.register_keyword(name, description)
    )


@eel.expose
def delete_keyword(payload: dict[str, Any]) -> dict[str, Any]:
    """キーワード削除リクエストを処理します。

    入力
        payload: ``dict[str, Any]``
            ``identifier`` を含む辞書。
    出力
        ``dict[str, Any]``
            成功可否とスナップショット。
    処理概要
        1. サービスへ削除対象を渡し :func:`_operation_response` で処理結果を構築します。
    """
    service = _ensure_service()
    identifier = str(payload.get("identifier", "")) if payload else ""
    return _operation_response(service, lambda: service.delete_keyword(identifier))


@eel.expose
def set_keyword_visibility(payload: dict[str, Any]) -> dict[str, Any]:
    """キーワードの表示・非表示切り替えを処理します。"""

    service = _ensure_service()
    identifier = str(payload.get("identifier", "")) if payload else ""
    hidden_value = payload.get("hidden", False) if payload else False
    if isinstance(hidden_value, str):
        normalized = hidden_value.strip().lower()
        hidden_flag = normalized in {"1", "true", "yes", "on", "hidden"}
    else:
        hidden_flag = bool(hidden_value)
    return _operation_response(
        service, lambda: service.set_keyword_visibility(identifier, hidden_flag)
    )


@eel.expose
def register_season(payload: dict[str, Any]) -> dict[str, Any]:
    """シーズン登録リクエストを処理します。

    入力
        payload: ``dict[str, Any]``
            シーズン名・備考・開始/終了日時を含む辞書。
    出力
        ``dict[str, Any]``
            成功可否と最新スナップショット。
    処理概要
        1. 入力値を正規化し :meth:`DuelPerformanceService.register_season` を呼び出します。
        2. :func:`_operation_response` で結果を統一フォーマットに整形します。
    """
    service = _ensure_service()
    payload = payload or {}
    name = str(payload.get("name", ""))
    notes = str(payload.get("notes", ""))
    start_date = payload.get("start_date")
    start_time = payload.get("start_time")
    end_date = payload.get("end_date")
    end_time = payload.get("end_time")
    rank_statistics_target = payload.get("rank_statistics_target", False)
    return _operation_response(
        service,
        lambda: service.register_season(
            name,
            notes,
            rank_statistics_target=rank_statistics_target,
            start_date=start_date,
            start_time=start_time,
            end_date=end_date,
            end_time=end_time,
        ),
    )


@eel.expose
def delete_season(payload: dict[str, Any]) -> dict[str, Any]:
    """シーズン削除リクエストを処理します。

    入力
        payload: ``dict[str, Any]``
            ``name`` を含む辞書。
    出力
        ``dict[str, Any]``
            成功可否とスナップショット。
    処理概要
        1. 対象名を取得し :func:`_operation_response` で削除処理を行います。
    """
    service = _ensure_service()
    name = str(payload.get("name", "")) if payload else ""
    return _operation_response(service, lambda: service.delete_season(name))


@eel.expose
def get_match_detail(payload: dict[str, Any]) -> dict[str, Any]:
    """対戦詳細取得リクエストを処理します。

    入力
        payload: ``dict[str, Any]``
            ``id`` を含む辞書。
    出力
        ``dict[str, Any]``
            成功時は ``data`` に詳細辞書、失敗時は ``error``。
    処理概要
        1. ID の整数変換を試み、不正時は ``ok=False`` を返します。
        2. サービスへ委譲し DB 例外を捕捉してレスポンスへ変換します。
    """
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
    """対戦情報の更新リクエストを処理します。

    入力
        payload: ``dict[str, Any]``
            ``id`` と更新内容を含む辞書。
    出力
        ``dict[str, Any]``
            成功可否とスナップショット。
    処理概要
        1. 入力の存在と ID の整数変換を検証。
        2. サービスへ更新辞書を渡し :func:`_operation_response` でレスポンス化します。
    """
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
    """対戦記録の削除リクエストを処理します。

    入力
        payload: ``dict[str, Any]``
            ``id`` を含む辞書。
    出力
        ``dict[str, Any]``
            成功可否とスナップショット。
    処理概要
        1. ID を整数へ変換し、エラー時は ``ok=False`` を返却。
        2. サービスへ削除処理を委譲し :func:`_operation_response` で結果をまとめます。
    """
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
    """バックアップ出力リクエストを処理します。

    入力
        _: ``Optional[dict[str, Any]]``
            未使用。Eel 仕様上のプレースホルダーです。
    出力
        ``dict[str, Any]``
            成功時は ``data`` にファイル名と Base64 文字列を格納。
    処理概要
        1. サービスの :meth:`generate_backup_archive` を実行。
        2. 失敗時はログ出力し ``ok=False`` を返します。
    """
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
    """バックアップ取り込みリクエストを処理します。

    入力
        payload: ``dict[str, Any]``
            Base64 文字列 ``content`` を含む辞書。
    出力
        ``dict[str, Any]``
            成功時は ``restored`` 件数とスナップショット。
    処理概要
        1. Base64 デコードを試み形式不備を検出。
        2. サービスの :meth:`import_backup_archive` を実行し結果を返します。
    """
    service = _ensure_service()
    payload = payload or {}
    content = payload.get("content")
    if not content:
        return {"ok": False, "error": "バックアップデータが指定されていません"}
    try:
        archive_bytes = base64.b64decode(content)
    except (TypeError, ValueError) as exc:
        return {"ok": False, "error": f"バックアップデータの形式が不正です: {exc}"}
    mode = str(payload.get("mode", "full") or "full")
    dry_run = bool(payload.get("dry_run", False))
    try:
        report, state = service.import_backup_archive(
            archive_bytes, mode=mode, dry_run=dry_run
        )
    except DatabaseError as exc:
        log_db_error("Failed to import backup archive", exc)
        return {"ok": False, "error": str(exc)}
    snapshot = _build_snapshot(state)
    return {
        "ok": True,
        "restored": report.restored,
        "failures": len(report.failures),
        "log_path": str(report.log_path) if report.log_path else "",
        "snapshot": snapshot,
    }


@eel.expose
def reset_database(_: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """データベース初期化リクエストを処理します。

    入力
        _: ``Optional[dict[str, Any]]``
            未使用。Eel 呼び出し互換のためのプレースホルダーです。
    出力
        ``dict[str, Any]``
            成功可否と再構築されたスナップショット。
    処理概要
        1. サービスへ :meth:`DuelPerformanceService.reset_database` を委譲し結果を返します。
    """
    service = _ensure_service()
    return _operation_response(service, service.reset_database)


def main() -> None:
    """Eel アプリケーションを起動します。

    入力
        引数はありません。
    出力
        ``None``
            副作用として Eel のイベントループが開始されます。
    処理概要
        1. ロギング設定とサービス初期化を行います。
        2. フロントエンドリソースを読み込み :func:`eel.start` で UI を起動します。
    """

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
