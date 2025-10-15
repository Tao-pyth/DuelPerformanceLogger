"""アプリケーション状態 (:class:`AppState`) の定義と管理ヘルパー。

記載内容
    - :class:`AppState`: UI へ渡すスナップショットのデータクラス。
    - グローバル状態の取得・更新関数 (:func:`get_app_state` など)。
    - DB から最新情報を集約する :func:`build_state`。

想定参照元
    - :mod:`app.main` での状態更新と Eel への返却処理。
    - テストコードでのモック状態生成。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, TYPE_CHECKING

from .cmn_config import load_config

if TYPE_CHECKING:  # pragma: no cover - import guard for type checking only
    from .cmn_database import DatabaseManager


@dataclass
class AppState:
    """アプリ全体の状態を保持するデータクラス。

    役割
        - デッキ・シーズン・対戦履歴など UI が必要とする情報を集約します。
        - メタ情報（マイグレーション結果やバックアップ状況）も同時に保持します。

    想定利用箇所
        - :mod:`app.main` 内でのスナップショット生成やシリアライズ。
        - テストコードでの状態比較。
    """

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
        """現在の状態を JSON 化しやすい辞書に変換します。

        入力
            引数はありません。
        出力
            ``dict[str, Any]``
                UI へ返却する際に利用する辞書形式のデータ。
        処理概要
            1. データクラスの各フィールドを辞書へ集約します。
        """

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
        """状態の安全なコピーを生成します。

        入力
            引数はありません。
        出力
            :class:`AppState`
                リストや辞書を浅いコピーした新しいインスタンス。
        処理概要
            1. 各フィールドを ``dict``/``list`` ベースで複製し、新しい :class:`AppState` を生成します。
        """

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
    """現在のグローバル状態を返します。

    入力
        引数はありません。
    出力
        :class:`AppState`
            グローバルに保持している状態参照。
    処理概要
        1. モジュールレベル変数 ``_state`` をそのまま返却します。
    """

    return _state


def set_app_state(state: AppState) -> AppState:
    """グローバル状態を差し替えて返します。

    入力
        state: :class:`AppState`
            設定したい状態オブジェクト。
    出力
        :class:`AppState`
            代入後の状態（引数と同じインスタンス）。
    処理概要
        1. グローバル変数 ``_state`` を更新し、新しい参照を返します。
    """

    global _state
    _state = state
    return _state


def reset_app_state() -> AppState:
    """グローバル状態を初期化します。

    入力
        引数はありません。
    出力
        :class:`AppState`
            初期化後の状態。
    処理概要
        1. 設定を再読み込みし新しい :class:`AppState` を生成します。
        2. グローバル変数 ``_state`` を更新して返します。
    """

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
    """データベースから最新情報を集約し :class:`AppState` を生成します。

    入力
        db: :class:`DatabaseManager`
            データ取得に利用する DB マネージャー。
        config: ``Mapping[str, Any]``
            設定値。状態へコピーされます。
        migration_result: ``str``
            直近マイグレーションの結果メッセージ。
        migration_timestamp: ``str``
            マイグレーション実行時刻の文字列。
    出力
        :class:`AppState`
            DB スナップショットを反映した状態。
    処理概要
        1. DB からデッキや対戦ログを取得し辞書へ格納します。
        2. メタデータやファイルパスを含めて :class:`AppState` を生成します。
    """

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
