"""Common logging utilities used across the application."""

from __future__ import annotations

import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from app.function.core import paths

# NOTE: 例外情報や追加コンテキストをテキストファイルとして出力する小さな
# ロガーです。標準ライブラリのみで動作し、アプリ固有のログ出力仕様に合わせて
# シンプルに実装しています。

_LOG_DIR = paths.log_dir()


def log_error(message: str, exc: BaseException | None = None, **context: Any) -> Path:
    """Write a detailed error log entry and return the written file path."""

    # 日付単位でログファイルを分ける。例: 20240101.log
    timestamp = datetime.now()
    log_path = _LOG_DIR / f"{timestamp:%Y%m%d}.log"
    lines = [f"[{timestamp:%Y-%m-%d %H:%M:%S}] {message}"]

    # 任意キーワード引数として渡されたコンテキスト情報を 1 行にまとめる。
    if context:
        context_repr = ", ".join(f"{key}={value!r}" for key, value in context.items())
        lines.append(f"Context: {context_repr}")

    # 例外オブジェクトがある場合はトレースバック全文を記録し、ない場合は明示。
    if exc is not None:
        lines.append("Traceback:")
        lines.extend(traceback.format_exception(type(exc), exc, exc.__traceback__))
    else:
        lines.append("No exception information available.")

    # 追記モードでファイルへ書き込み。`with` 文により自動的にクローズされる。
    with log_path.open("a", encoding="utf-8") as stream:
        stream.write("\n".join(lines))
        stream.write("\n")

    return log_path


def log_db_error(context: str, exc: Exception | None = None, **info: Any) -> Path:
    """Persist database error details to the log folder."""

    # DB 関連のエラーでも基本的な処理は `log_error` と同じなのでラップする。
    return log_error(context, exc, **info)


__all__ = ["log_error", "log_db_error"]
