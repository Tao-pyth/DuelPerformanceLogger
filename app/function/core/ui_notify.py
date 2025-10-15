"""Eel ベース UI へのトースト通知送信ヘルパー。

記載内容
    - :func:`notify`: UI へ非同期通知を送る関数。

想定参照元
    - :mod:`app.main` 内での操作結果通知。
    - 将来的なバックグラウンド処理からの利用。
"""

from __future__ import annotations

import logging

try:  # pragma: no cover - import guard for optional dependency
    import eel  # type: ignore
except Exception:  # pragma: no cover - defensive fallback if Eel is unavailable
    eel = None  # type: ignore

logger = logging.getLogger(__name__)


def notify(text: str, duration: float = 1.5) -> None:
    """Web フロントエンドに非同期トースト通知を表示します。

    入力
        text: ``str``
            表示したいメッセージ本文。
        duration: ``float``
            表示時間（秒）。マイナス値は 0 として扱います。
    出力
        ``None``
            副作用として UI 通知を送信します。
    処理概要
        1. 受け取った秒数をミリ秒へ変換。
        2. Eel が利用可能なら ``show_notification`` を呼び出し、失敗時はログ出力します。
    """

    duration_ms = max(int(duration * 1000), 0)

    if eel is not None:
        try:
            eel.show_notification(text, duration_ms)
            return
        except AttributeError:
            logger.debug("Eel has no 'show_notification'; text=%r", text)
        except (RuntimeError, ConnectionError) as exc:  # pragma: no cover - runtime specific
            logger.warning(
                "Eel notify failed: %s; text=%r",
                type(exc).__name__,
                text,
                exc_info=True,
            )

    logger.info("UI notification: %s", text)


__all__ = ["notify"]
