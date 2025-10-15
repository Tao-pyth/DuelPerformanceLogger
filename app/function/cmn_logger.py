"""アプリ全体で共通利用するログ出力ユーティリティ。

記載内容
    - :func:`log_error`: 任意のエラー情報をテキストログへ記録。
    - :func:`log_db_error`: データベース関連エラーのラッパー。

想定参照元
    - :mod:`app.main` や :mod:`app.function.cmn_database` の例外ハンドリング部分。
    - 障害調査用スクリプトからの直接利用。
"""

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
    """詳細なエラーログを出力しファイルパスを返します。

    入力
        message: ``str``
            ログ行に残したいメッセージ。
        exc: ``BaseException | None``
            例外オブジェクト。指定時はトレースバックを記録します。
        **context: ``Any``
            追加で残したい情報。``key=value`` 形式で整形されます。
    出力
        ``Path``
            追記されたログファイルのパス。
    処理概要
        1. 日付単位でログファイルを切り替え、ヘッダー行・コンテキスト・トレースバックを書き込みます。
        2. 最終的にログファイルパスを返却します。
    """

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
    """データベースエラーの詳細をログに記録します。

    入力
        context: ``str``
            エラー発生箇所や状況を表すメッセージ。
        exc: ``Exception | None``
            捕捉した例外。任意。
        **info: ``Any``
            補足情報を ``key=value`` で記録。
    出力
        ``Path``
            記録先ファイルのパス。
    処理概要
        1. :func:`log_error` を呼び出しデータベース固有の情報も含めて記録します。
    """

    # DB 関連のエラーでも基本的な処理は `log_error` と同じなのでラップする。
    return log_error(context, exc, **info)


__all__ = ["log_error", "log_db_error"]
