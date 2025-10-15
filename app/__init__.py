"""Duel Performance Logger アプリケーションのトップレベルパッケージ。

記載内容
    - ``__version__`` の再エクスポート。

想定参照元
    - アプリ起動スクリプトや外部モジュールからのバージョン取得。
"""

from app.function.core.version import __version__

__all__ = ["__version__"]
