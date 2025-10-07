"""Application entry point wiring together the KivyMD screens."""

# NOTE: このファイルはアプリ全体のエントリーポイントです。Kivy/KivyMD の
# アプリケーション起動処理や、画面（Screen）の初期化・画面遷移設定などを
# まとめて定義しています。Python / Kivy 初心者向けに、各処理の意図が分かる
# ように詳細なコメントを付与しています。

from __future__ import annotations

import os
from pathlib import Path
from platform import system

from kivy.core.text import LabelBase, DEFAULT_FONT
from kivy.core.window import Window
from kivymd.app import MDApp
from kivymd.uix.screenmanager import MDScreenManager

from function import DatabaseManager, DatabaseError
from function.cmn_app_state import get_fallback_state
from function.cmn_config import load_config
from function.cmn_logger import log_db_error
from function.cmn_resources import get_text
from function.screen.deck_registration_screen import DeckRegistrationScreen
from function.screen.match_entry_screen import (
    MatchEntryBroadcastScreen,
    MatchEntryScreen,
)
from function.screen.match_setup_screen import (
    MatchSetupBroadcastScreen,
    MatchSetupScreen,
)
from function.screen.menu_screen import MenuScreen
from function.screen.season_list_screen import SeasonListScreen
from function.screen.season_registration_screen import SeasonRegistrationScreen
from function.screen.settings_screen import SettingsScreen
from function.screen.stats_screen import StatsScreen

if system() == "Windows":
    # Windows で日本語を含む文字列を正しく表示するため、利用可能なフォントを
    # 優先順位付きで探します。初めに見つかったフォントを Kivy のデフォルト
    # として登録します。存在しないファイルはスキップされるため安全です。
    _system_root = Path(os.environ.get("SystemRoot", "C:/Windows"))
    font_candidates = [
        _system_root / "Fonts" / "YuGothicUIRegular.ttf",
        _system_root / "Fonts" / "msgothic.ttc",
        _system_root / "Fonts" / "meiryo.ttc",
    ]
    for font_path in font_candidates:
        if font_path.exists():
            LabelBase.register(DEFAULT_FONT, str(font_path))
            break


class DeckAnalyzerApp(MDApp):
    """デュエル戦績管理アプリの KivyMD アプリケーションクラス。

    入力
        インスタンス生成時に特別な引数は必要ありません。
    出力
        :class:`MDApp` を継承したアプリケーションとして、画面遷移や DB 管理を
        司るメソッドを提供します。
    """

    def build(self):
        """アプリ起動時に UI 構築と初期データ読み込みを行います。

        入力
            追加の引数はありません。インスタンス属性を初期化します。
        出力
            ``MDScreenManager``
                画面を集約したマネージャを返し、Kivy がルートウィジェットとして
                使用します。
        """

        # テーマカラーなど、見た目に関する初期設定を行う。
        self.theme_cls.primary_palette = "BlueGray"
        self.config = load_config()
        self.default_window_size = Window.size

        # DatabaseManager は SQLite へのアクセスを司るユーティリティ。
        # 起動時に DB を確実に準備し、ユーザー設定（UI モードなど）を取得する。
        self.db = DatabaseManager()
        self.db.ensure_database()
        self.ui_mode = self.db.get_ui_mode()

        # コンフィグに定義されたスキーマバージョンと、実際の DB バージョンを照合。
        # 文字列が保存されている可能性もあるので、念のため int 化を試みる。
        expected_version_raw = self.config.get("database", {}).get(
            "expected_version", DatabaseManager.CURRENT_SCHEMA_VERSION
        )
        try:
            expected_version = int(expected_version_raw)
        except (TypeError, ValueError):
            expected_version = DatabaseManager.CURRENT_SCHEMA_VERSION
        current_version = self.db.get_schema_version()
        if current_version != expected_version:
            # バージョン不一致時はバックアップ作成 → 初期化 → 復元を試みる。
            self.migration_result = self._handle_version_mismatch(
                current_version, expected_version
            )
        else:
            self.migration_result = ""

        self.db.set_schema_version(expected_version)

        # アプリ内で使い回す主要データ（デッキ・シーズン・対戦ログ）をまとめて取得。
        self.decks = self.db.fetch_decks()
        self.seasons = self.db.fetch_seasons()
        self.match_records = self.db.fetch_matches()
        self.opponent_decks = self.db.fetch_opponent_decks()
        self.current_match_settings = None
        self.current_match_count = 0

        # アプリがまだ起動していない場面（例えばテストコード）でも画面が参照できる
        # よう、フォールバック用の状態オブジェクトにも同じ情報をコピーしておく。
        fallback = get_fallback_state()
        fallback.reset()
        fallback.theme_cls.primary_color = self.theme_cls.primary_color
        fallback.db = self.db
        fallback.decks = list(self.decks)
        fallback.seasons = list(self.seasons)
        fallback.match_records = list(self.match_records)
        fallback.opponent_decks = list(self.opponent_decks)
        fallback.config = dict(self.config)
        fallback.ui_mode = self.ui_mode
        fallback.default_window_size = self.default_window_size
        fallback.migration_result = self.migration_result

        # ここでは ScreenManager に各画面を登録している。`name` が画面遷移のキー。
        screen_manager = MDScreenManager()
        screen_manager.add_widget(MenuScreen(name="menu"))
        screen_manager.add_widget(DeckRegistrationScreen(name="deck_register"))
        screen_manager.add_widget(SeasonListScreen(name="season_list"))
        screen_manager.add_widget(SeasonRegistrationScreen(name="season_register"))
        screen_manager.add_widget(MatchSetupScreen(name="match_setup"))
        screen_manager.add_widget(
            MatchSetupBroadcastScreen(name="match_setup_broadcast")
        )
        screen_manager.add_widget(MatchEntryScreen(name="match_entry"))
        screen_manager.add_widget(
            MatchEntryBroadcastScreen(name="match_entry_broadcast")
        )
        screen_manager.add_widget(StatsScreen(name="stats"))
        screen_manager.add_widget(SettingsScreen(name="settings"))
        return screen_manager

    def _handle_version_mismatch(self, current_version: int, expected_version: int) -> str:
        """DB バージョン不一致時の対処処理を実行し、結果メッセージを返します。

        入力
            current_version: ``int``
                現在の DB スキーマバージョン。
            expected_version: ``int``
                コンフィグで想定される最新バージョン。
        出力
            ``str``
                バックアップや復元処理の結果を画面表示用にまとめた文字列。
        """

        # まず画面へ表示するメッセージ（ログ）を格納するリストを用意する。
        lines = [
            get_text("settings.db_migration_detected").format(
                current=current_version, expected=expected_version
            )
        ]

        try:
            # 現行 DB のバックアップを作成し、その結果をメッセージへ追加。
            backup_path = self.db.export_backup()
            lines.append(
                get_text("settings.db_migration_backup").format(path=str(backup_path))
            )
            self.db.record_backup_path(backup_path)

            # スキーマ初期化後、期待されるバージョンを設定する。
            self.db.initialize_database()
            self.db.set_schema_version(expected_version)

            try:
                # バックアップからデータを戻す。失敗したらログに残しつつ、
                # 画面にも失敗メッセージを表示する。
                restored = self.db.import_backup(backup_path)
            except DatabaseError as exc:
                log_db_error(
                    "Failed to restore database during migration", exc, backup=str(backup_path)
                )
                lines.append(
                    get_text("settings.db_migration_restore_failed").format(error=str(exc))
                )
                return "\n".join(
                    [get_text("settings.db_migration_failure").format(error=str(exc))]
                    + lines
                )
            else:
                # 復元成功時は件数を含むメッセージを追加。
                lines.append(
                    get_text("settings.db_migration_restore_success").format(
                        decks=restored.get("decks", 0),
                        seasons=restored.get("seasons", 0),
                        matches=restored.get("matches", 0),
                    )
                )

            return "\n".join([get_text("settings.db_migration_success")] + lines)
        except Exception as exc:  # pragma: no cover - defensive
            # 予期せぬ例外が発生した場合も、ユーザーに状況が伝わるよう文字列を返す。
            return "\n".join(
                [
                    get_text("settings.db_migration_failure").format(error=str(exc)),
                    *lines,
                ]
            )


if __name__ == "__main__":
    DeckAnalyzerApp().run()
