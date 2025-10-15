"""ローカライズ文字列リソースを読み込むユーティリティ群。

記載内容
    - :func:`get_text`: UI テキストをキーで検索する公開 API。
    - 内部キャッシュ関数 :func:`_load_strings`。

想定参照元
    - :mod:`app.main` など、UI 文言を動的に取得するサービス層。
    - 将来的なバッチやテストで文字列存在チェックを行う処理。
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from app.function.core import paths


# NOTE: 旧 Kivy 版から継承した UI テキスト JSON を引き続き利用しています。
# このモジュールではファイルの読み込み・キャッシュ・アクセス用ヘルパーを提供し、
# Eel フロントエンドからもシンプルに `get_text("menu.title")` で文字列を取得できる
# ようにしています。

# 文字列リソースが格納されているファイルパスを centralized path helper から取得。
_STRINGS_PATH = paths.strings_path()


@lru_cache(maxsize=1)
def _load_strings() -> dict[str, Any]:
    """文字列リソースを読み込みキャッシュします。

    入力
        引数はありません。
    出力
        ``dict[str, Any]``
            JSON ファイルを辞書化したデータ。
    処理概要
        1. ``strings.json`` を開き JSON を読み込みます。
        2. ``lru_cache`` により 1 度読み込んだ内容を保持します。
    """

    # `lru_cache` を使うことで 1 度読み込んだ JSON をメモリに保持し、
    # 毎回ディスクへアクセスするコストを削減している。
    with _STRINGS_PATH.open(encoding="utf-8") as stream:
        return json.load(stream)


def get_text(path: str, default: Any | None = None) -> Any:
    """ドット記法で指定した文字列リソースを取得します。

    入力
        path: ``str``
            ``"settings.title"`` のようなドット区切りのキー。
        default: ``Any | None``
            見つからない場合に返す既定値。未指定時はパス文字列を返します。
    出力
        ``Any``
            該当する値。文字列が基本ですがネストされた辞書/配列も返る可能性があります。
    処理概要
        1. :func:`_load_strings` の結果をたどり ``path`` を段階的に探索。
        2. 見つからない場合は ``default`` もしくはパス文字列を返却します。
    """

    # `path` に `.` 区切りで指定されたキーを辿り、対応する値を返す。
    data: Any = _load_strings()
    for segment in path.split("."):
        if isinstance(data, dict) and segment in data:
            data = data[segment]
        else:
            # 指定が誤っている場合は default、なければそのままキー文字列を返す。
            return default if default is not None else path
    return data
