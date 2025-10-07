"""Application configuration management utilities."""

# NOTE: 設定ファイル（`resource/theme/config.conf`）を読み込み、辞書形式で
# 返すためのヘルパーをまとめています。設定が存在しない場合でも安全に
# 既定値で動作するよう、読み込み → マージ処理を行います。

from __future__ import annotations

import configparser
from pathlib import Path
from typing import Any, MutableMapping


# 設定ファイルの実体はプロジェクト内の `resource/theme/config.conf` にあります。
_CONFIG_PATH = Path(__file__).resolve().parent.parent / "resource" / "theme" / "config.conf"


DEFAULT_CONFIG: dict[str, Any] = {
    "database": {
        "expected_version": 3,
    },
}


def load_config() -> dict[str, Any]:
    """Return the persisted configuration or the defaults when missing."""

    # `ConfigParser` で INI 形式の設定を読み込む。ファイルがなければ空のまま。
    parser = configparser.ConfigParser()
    if _CONFIG_PATH.exists():
        parser.read(_CONFIG_PATH, encoding="utf-8")

    # 読み込んだ結果を通常の辞書へ変換し、`DEFAULT_CONFIG` を土台として上書き。
    config = _configparser_to_dict(parser)
    merged = dict(DEFAULT_CONFIG)
    _deep_update(merged, config)
    return merged


def _configparser_to_dict(parser: configparser.ConfigParser) -> dict[str, Any]:
    """ConfigParser オブジェクトをネストした辞書へ変換する。"""

    data: dict[str, Any] = {}
    for section in parser.sections():
        items = {}
        for key, value in parser.items(section):
            items[key] = value
        data[section] = items
    return data


def _deep_update(base: MutableMapping[str, Any], updates: MutableMapping[str, Any]) -> None:
    """ネストした辞書同士を再帰的にマージする小さなユーティリティ。"""

    for key, value in updates.items():
        if (
            key in base
            and isinstance(base[key], MutableMapping)
            and isinstance(value, MutableMapping)
        ):
            _deep_update(base[key], value)
        else:
            base[key] = value


def get_config_path() -> Path:
    """Expose the configuration path for informational purposes."""

    return _CONFIG_PATH

