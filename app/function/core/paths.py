"""パス計算ロジックを集約したヘルパーモジュール。

記載内容
    - プロジェクト/アプリ/リソース各種ディレクトリを返す関数群。
    - ユーザーデータ用ディレクトリの生成とキャッシュ。

想定参照元
    - 設定読み込み、DB/ログファイル操作などの共通基盤コード。
    - テストでのファイル配置確認。
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from platform import system


_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_APP_ROOT = _PROJECT_ROOT / "app"
_PACKAGE_ROOT = _APP_ROOT / "function"
_RESOURCE_ROOT = _PROJECT_ROOT / "resource"


def project_root() -> Path:
    """リポジトリルートの絶対パスを返します。

    入力
        引数はありません。
    出力
        ``Path``
            ``DuelPerformanceLogger`` プロジェクトのルートパス。
    処理概要
        1. モジュールロード時に計算した ``_PROJECT_ROOT`` をそのまま返却します。
    """

    return _PROJECT_ROOT


def app_root() -> Path:
    """アプリケーションソースのルートディレクトリを返します。

    入力
        引数はありません。
    出力
        ``Path``
            ``app`` ディレクトリの絶対パス。
    処理概要
        1. ``_APP_ROOT`` を返却します。
    """

    return _APP_ROOT


def package_root() -> Path:
    """``app.function`` パッケージルートを返します。

    入力
        引数はありません。
    出力
        ``Path``
            ``app/function`` ディレクトリの絶対パス。
    処理概要
        1. ``_PACKAGE_ROOT`` を返却します。
    """

    return _PACKAGE_ROOT


def resource_root() -> Path:
    """同梱リソースのルートディレクトリを返します。

    入力
        引数はありません。
    出力
        ``Path``
            ``resource`` ディレクトリの絶対パス。
    処理概要
        1. ``_RESOURCE_ROOT`` を返却します。
    """

    return _RESOURCE_ROOT


def resource_path(*parts: str) -> Path:
    """リソースルート配下で追加パスを結合して返します。

    入力
        *parts: ``str``
            結合したいパス要素。
    出力
        ``Path``
            ``resource`` 配下の目的パス。
    処理概要
        1. :func:`resource_root` の結果に ``joinpath`` でパーツを結合します。
    """

    return resource_root().joinpath(*parts)


def theme_path(*parts: str) -> Path:
    """テーマリソース配下のパスを返します。

    入力
        *parts: ``str``
            テーマ内で辿りたいパス要素。
    出力
        ``Path``
            ``resource/theme`` 以下のパス。
    処理概要
        1. :func:`resource_path` に ``"theme"`` と追加パーツを渡して生成します。
    """

    return resource_path("theme", *parts)


def web_path(*parts: str) -> Path:
    """Web(Eel) 資産ディレクトリ内のパスを返します。

    入力
        *parts: ``str``
            Web アセット内で辿るパス要素。
    出力
        ``Path``
            ``resource/web`` 配下のパス。
    処理概要
        1. :func:`resource_path` に ``"web"`` と追加パーツを渡して生成します。
    """

    return resource_path("web", *parts)


@lru_cache(maxsize=1)
def user_data_root() -> Path:
    """ユーザーデータを書き込むルートディレクトリを返し、存在を保証します。

    入力
        引数はありません。
    出力
        ``Path``
            OS ごとのユーザーデータルート。
    処理概要
        1. OS 判定に応じたベースディレクトリを決定。
        2. ``DuelPerformanceLogger`` ディレクトリを作成し、パスを返却します。
    """

    platform_name = system()
    if platform_name == "Windows":
        base_dir = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif platform_name == "Darwin":
        base_dir = Path.home() / "Library" / "Application Support"
    else:
        base_dir = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    target = base_dir / "DuelPerformanceLogger"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _ensure_subdir(name: str) -> Path:
    """ユーザーデータ配下に指定サブディレクトリを用意します。

    入力
        name: ``str``
            作成したいサブディレクトリ名。
    出力
        ``Path``
            作成済みサブディレクトリのパス。
    処理概要
        1. :func:`user_data_root` の配下に ``name`` を結合し ``mkdir`` で生成します。
    """

    path = user_data_root() / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_dir() -> Path:
    """SQLite データベースファイルを保存するディレクトリを返します。

    入力
        引数はありません。
    出力
        ``Path``
            ``user_data_root/db`` のパス。
    処理概要
        1. :func:`_ensure_subdir` で ``db`` ディレクトリを作成し返します。
    """

    return _ensure_subdir("db")


def log_dir() -> Path:
    """アプリケーションログを格納するディレクトリを返します。

    入力
        引数はありません。
    出力
        ``Path``
            ``user_data_root/logs`` のパス。
    処理概要
        1. :func:`_ensure_subdir` で ``logs`` ディレクトリを作成し返します。
    """

    return _ensure_subdir("logs")


def youtube_log_dir() -> Path:
    """YouTube 連携専用のログディレクトリを返します。

    入力
        引数はありません。
    出力
        ``Path``
            ``log_dir()/youtube`` のパス。
    処理概要
        1. :func:`log_dir` で親ディレクトリを生成し、その配下に ``youtube`` を作成します。
    """

    path = log_dir() / "youtube"
    path.mkdir(parents=True, exist_ok=True)
    return path


def recording_dir() -> Path:
    """録画ファイルを保存するディレクトリを返します。

    入力
        引数はありません。
    出力
        ``Path``
            ``user_data_root/recordings`` のパス。
    処理概要
        1. :func:`_ensure_subdir` を利用して ``recordings`` ディレクトリを生成します。
    """

    return _ensure_subdir("recordings")


def backup_dir() -> Path:
    """バックアップファイルを格納するディレクトリを返します。

    入力
        引数はありません。
    出力
        ``Path``
            ``user_data_root/backups`` のパス。
    処理概要
        1. :func:`_ensure_subdir` で ``backups`` ディレクトリを用意して返します。
    """

    return _ensure_subdir("backups")


def config_dir() -> Path:
    """ユーザーが編集可能な設定ファイルのディレクトリを返します。

    入力
        引数はありません。
    出力
        ``Path``
            ``user_data_root/config`` のパス。
    処理概要
        1. :func:`_ensure_subdir` で ``config`` ディレクトリを用意します。
    """

    return _ensure_subdir("config")


def config_path(filename: str = "config.conf") -> Path:
    """指定ファイル名の設定ファイルパスを返します。

    入力
        filename: ``str``
            設定ファイル名。既定は ``config.conf``。
    出力
        ``Path``
            ``config_dir`` 配下の絶対パス。
    処理概要
        1. :func:`config_dir` の結果と ``filename`` を結合します。
    """

    return config_dir() / filename


def default_config_path() -> Path:
    """同梱されている既定設定ファイルのパスを返します。

    入力
        引数はありません。
    出力
        ``Path``
            ``resource/theme/config.conf`` のパス。
    処理概要
        1. :func:`theme_path` を用いて ``config.conf`` の場所を返します。
    """

    return theme_path("config.conf")


def strings_path() -> Path:
    """同梱のローカライズ文字列 JSON のパスを返します。

    入力
        引数はありません。
    出力
        ``Path``
            ``resource/theme/json/strings.json`` のパス。
    処理概要
        1. :func:`theme_path` に ``("json", "strings.json")`` を渡して生成します。
    """

    return theme_path("json", "strings.json")


def web_root() -> Path:
    """同梱 Web アセットのルートディレクトリを返します。

    入力
        引数はありません。
    出力
        ``Path``
            ``resource/web`` のパス。
    処理概要
        1. :func:`web_path` を引数なしで呼び、ルートパスを取得します。
    """

    return web_path()


__all__ = [
    "app_root",
    "backup_dir",
    "config_dir",
    "config_path",
    "database_dir",
    "default_config_path",
    "log_dir",
    "youtube_log_dir",
    "package_root",
    "project_root",
    "recording_dir",
    "resource_path",
    "resource_root",
    "strings_path",
    "theme_path",
    "web_path",
    "web_root",
    "user_data_root",
]
