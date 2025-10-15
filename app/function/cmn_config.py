"""アプリケーション設定ファイルを扱うユーティリティ群。

ユーザーデータディレクトリ（例: ``%APPDATA%/DuelPerformanceLogger``）に保存された
設定を読み込み、辞書形式で返却するヘルパーをまとめています。設定が存在しない
場合は、パッケージ同梱の既定設定とマージした辞書を返します。
"""

# NOTE: 設定ファイルをユーザーデータディレクトリから読み込み、存在しない場合は
# パッケージ同梱の既定設定をフォールバックとして利用します。設定が存在しなくて
# も安全に既定値で動作するよう、読み込み → マージ処理を行います。

from __future__ import annotations

import configparser
from typing import Any, MutableMapping

from app.function.core import paths


# 設定ファイルはユーザーデータディレクトリ配下に配置し、パッケージ同梱の既定値も参照可能にする。
_CONFIG_PATH = paths.config_path()
_DEFAULT_CONFIG_PATH = paths.default_config_path()


DEFAULT_CONFIG: dict[str, Any] = {
    "database": {
        # Schema version is tracked as a semantic-version string (e.g., "0.1.1").
        "expected_version": "0.3.1",
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
    paths.config_dir()  # ensure directory exists for potential writes
    if _CONFIG_PATH.exists():
        parser.read(_CONFIG_PATH, encoding="utf-8")
    elif _DEFAULT_CONFIG_PATH.exists():
        parser.read(_DEFAULT_CONFIG_PATH, encoding="utf-8")

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

