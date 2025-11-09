"""Development metadata for Duel Performance Logger.

このモジュールで公開する ``__version__`` は、パッケージングやテスト用の
開発メタデータとしてのみ利用します。UI 表示やログ出力でのバージョン表記は
データベースの ``app_meta`` テーブルに保存された値を参照してください。
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.4.2"
