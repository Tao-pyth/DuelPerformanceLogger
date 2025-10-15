"""UI/基盤向けコアユーティリティを束ねるパッケージ。

記載内容
    - :mod:`.paths`、:mod:`.ui_notify`、:mod:`.version` の公開。

想定参照元
    - ``app.function`` パッケージを通じた一括インポート。
    - UI/サービス層からの直接利用。
"""

__all__ = ["ui_notify", "paths", "version"]
