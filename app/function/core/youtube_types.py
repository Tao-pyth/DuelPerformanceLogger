"""YouTube 連携で利用する定数や列挙型を定義するモジュール。

本モジュールでは、アップロード処理の状態管理で共通利用する
``YouTubeSyncFlag`` を提供します。整数値として SQLite に保存される
ため、アプリ内の各レイヤー（DB、サービス、UI）が同じ意味で扱える
ように列挙型で定義しています。
"""

from __future__ import annotations

from enum import IntEnum

__all__ = ["YouTubeSyncFlag"]


class YouTubeSyncFlag(IntEnum):
    """YouTube アップロード状態を表すフラグ値。"""

    NOT_REQUESTED = 0
    """未送信。録画ファイルはあるがアップロード未実施。"""

    NEEDS_RETRY = 1
    """失敗などにより再試行待ちの状態。"""

    IN_PROGRESS = 2
    """アップロード処理中。"""

    COMPLETED = 3
    """アップロード完了し YouTube URL が確定している。"""

    MANUAL = 4
    """手動で URL が登録された状態。"""

