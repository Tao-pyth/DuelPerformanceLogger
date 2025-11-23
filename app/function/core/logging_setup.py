"""ロギング設定をまとめて初期化するためのユーティリティ。"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from . import paths

LOG_FILE_NAME = "app.log"


def log_file_path() -> Path:
    """アプリ標準のログファイルパスを返します。"""

    return paths.log_dir() / LOG_FILE_NAME


def configure_logging(debug_mode: bool = False) -> Path:
    """アプリ全体のロガーを初期化します。

    ルートロガーにコンソールとローテーション付きファイルの 2 系統を設定し、
    モジュール・関数名・行番号を含んだフォーマットで出力します。デバッグモード
    有効時はより詳細な処理遷移を追えるよう、ログレベルを DEBUG に切り替えます。
    """

    log_path = log_file_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    level = logging.DEBUG if debug_mode else logging.INFO
    formatter = logging.Formatter(
        fmt=(
            "%(asctime)s [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d - "
            "%(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(level)

    file_handler = RotatingFileHandler(
        log_path, maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)
    root_logger.addHandler(stream_handler)
    root_logger.addHandler(file_handler)

    # トレースに寄与しない冗長なサードパーティロガーは沈黙させる。
    logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)

    return log_path


def logging_snapshot(debug_mode: bool) -> dict[str, str | bool]:
    """ロギング状態のスナップショットを辞書で返します。"""

    return {"debug_mode": debug_mode, "log_path": str(log_file_path())}


__all__ = [
    "configure_logging",
    "log_file_path",
    "logging_snapshot",
]
