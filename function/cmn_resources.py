"""Utility helpers for loading localized resources from JSON files."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


# NOTE: Kivy の UI テキストは JSON ファイルにまとめて保存しています。
# このモジュールではファイルの読み込み・キャッシュ・アクセス用ヘルパーを提供し、
# 画面側がシンプルな `get_text("menu.title")` といった呼び出しで文字列を取得できる
# ようにしています。

# 文字列リソースが格納されているディレクトリを事前に解決しておく。
_RESOURCE_DIR = Path(__file__).resolve().parent.parent / "resource" / "theme" / "json"


@lru_cache(maxsize=1)
def _load_strings() -> dict[str, Any]:
    """Load and cache the string resources from disk."""

    # `lru_cache` を使うことで 1 度読み込んだ JSON をメモリに保持し、
    # 毎回ディスクへアクセスするコストを削減している。
    strings_path = _RESOURCE_DIR / "strings.json"
    with strings_path.open(encoding="utf-8") as stream:
        return json.load(stream)


def get_text(path: str, default: Any | None = None) -> Any:
    """Retrieve a value from the string resources by dotted path."""

    # `path` に `.` 区切りで指定されたキーを辿り、対応する値を返す。
    data: Any = _load_strings()
    for segment in path.split("."):
        if isinstance(data, dict) and segment in data:
            data = data[segment]
        else:
            # 指定が誤っている場合は default、なければそのままキー文字列を返す。
            return default if default is not None else path
    return data
