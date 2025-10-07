"""アプリケーション設定ファイルを扱うユーティリティ群。

``resource/theme/config.conf`` に保存された設定を読み込み、辞書形式で返却する
ヘルパーをまとめています。設定が存在しない場合は、既定値を含む辞書を返します。
"""

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
    """設定ファイルを読み込み、辞書に変換して返します。

    入力
        引数はありません。
    出力
        ``dict[str, Any]``
            ファイルに保存された設定を既定値 ``DEFAULT_CONFIG`` とマージした辞書。
    """

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
    """``ConfigParser`` オブジェクトをネストした辞書へ変換します。

    入力
        parser: ``configparser.ConfigParser``
            INI 形式の設定を保持したパーサー。
    出力
        ``dict[str, Any]``
            セクションをキー、各キー/値をネストした辞書として持つ Python 辞書。
    """

    data: dict[str, Any] = {}
    for section in parser.sections():
        items = {}
        for key, value in parser.items(section):
            items[key] = value
        data[section] = items
    return data


def _deep_update(base: MutableMapping[str, Any], updates: MutableMapping[str, Any]) -> None:
    """ネストした辞書同士を再帰的にマージします。

    入力
        base: ``MutableMapping[str, Any]``
            マージ結果を書き込む側の辞書。呼び出し後に上書きされます。
        updates: ``MutableMapping[str, Any]``
            反映したい値を保持する辞書。``base`` と同じ階層構造を想定します。
    出力
        ``None``
            返り値はありません。副作用として ``base`` が更新されます。
    """

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
    """設定ファイルの実体パスを返します。

    入力
        引数はありません。
    出力
        ``Path``
            ``config.conf`` の絶対パスを表す ``pathlib.Path`` オブジェクト。
    """

    return _CONFIG_PATH

