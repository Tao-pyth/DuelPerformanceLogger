"""画面間で共有するアプリケーション状態ユーティリティ。

このモジュールは Kivy/KivyMD の ``MDApp`` インスタンスが取得できない状況
（ユニットテストなど）でも、画面ロジックから共通状態へ安全にアクセスするための
フォールバックを提供します。
"""

# NOTE: Kivy では `MDApp.get_running_app()` を通してアプリ全体の状態へアクセス
# しますが、テストや一部のモジュールではアプリがまだ起動していない場合も
# あります。そのようなケースでも安全に値へアクセスできるよう、フォール
# バック用の状態オブジェクトを提供しています。

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Optional

from kivy.core.window import Window
from kivymd.app import MDApp

from .cmn_config import load_config
from .cmn_database import DatabaseManager


class _FallbackAppState:
    """稼働中の ``MDApp`` が存在しない場合に利用する擬似状態オブジェクト。

    説明
        Kivy/KivyMD の画面クラスから共通的に参照される属性群を保持します。
        実アプリケーションの状態が存在しない場合でも、既定値を返すことで
        例外を発生させずに処理を継続できます。
    入力
        生成時に特別な引数はありません。
    出力
        インスタンスは ``theme_cls`` や ``decks`` などの属性を保持し、
        それらを通じて状態を提供します。
    """

    def __init__(self) -> None:
        """インスタンス生成時に既定属性を作成します。

        入力
            追加の引数はありません。
        出力
            ``None`` を返します。副作用として ``theme_cls`` の擬似オブジェクトと
            各種リスト属性を初期化します。
        """
        # `theme_cls` など KivyMD で一般的に参照される属性を SimpleNamespace で
        # 疑似的に用意しておく。これにより、画面クラスはアプリが未起動でも
        # 例外を出さずに参照を行える。
        self.theme_cls = SimpleNamespace(primary_color=(0.2, 0.6, 0.86, 1))
        self.reset()

    def reset(self) -> None:
        """擬似状態を初期化し、各属性を既定値に戻します。

        入力
            追加の引数は取りません。内部状態のみを更新します。
        出力
            返り値は ``None`` で、副作用として ``config`` や ``decks`` などの
            属性がリセットされます。
        """
        # 初期状態をまとめてリセットする。辞書やリストは都度新しいインスタンスを
        # 作成し、外部からの変更が内部状態に影響しないようにしている。
        self.config = load_config()
        self.ui_mode = "normal"
        self.decks: list[dict[str, Any]] = []
        self.seasons: list[dict[str, Any]] = []
        self.match_records: list[dict[str, Any]] = []
        self.current_match_settings: Optional[dict[str, Any]] = None
        self.current_match_count = 0
        self.db: Optional[DatabaseManager] = None
        self.opponent_decks: list[str] = []
        self.default_window_size = Window.size
        self.migration_result: str = ""


_fallback_app_state = _FallbackAppState()


def get_app_state():
    """稼働中の ``MDApp`` を返し、存在しない場合はフォールバックを返します。

    入力
        引数はありません。
    出力
        ``MDApp`` が起動中であればそのインスタンス、未起動の場合は
        :class:`_FallbackAppState` インスタンスを返します。
    """

    # MDApp が起動済みならそのインスタンスを返し、そうでなければフォールバックを返す。
    app = MDApp.get_running_app()
    if app is None:
        return _fallback_app_state
    return app


def get_fallback_state() -> _FallbackAppState:
    """フォールバック状態そのものを直接取得します。

    入力
        引数はありません。
    出力
        :class:`_FallbackAppState` インスタンスを返します。テストコードなどが
        擬似状態へ直接アクセスしたい場合に利用してください。
    """

    # 直接フォールバック状態を扱いたい（テストなど）場面のために公開。
    return _fallback_app_state


__all__ = ["get_app_state", "get_fallback_state"]
