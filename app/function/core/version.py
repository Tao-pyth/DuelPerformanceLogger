"""Duel Performance Logger の正規バージョン情報を提供するモジュール。

記載内容
    - ``__version__``: アプリケーションのセマンティックバージョン文字列。

想定参照元
    - :mod:`app.__init__` や UI 表示でのバージョン表記。
    - テストコードによるバージョン検証。
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.4.1"
