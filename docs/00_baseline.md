# 00. Environment Baseline / 環境ベースライン

| Item | Baseline | Notes |
| ---- | -------- | ----- |
| Python | 3.10.x | Windows 10/11 (64bit) を想定した Kivy/KivyMD ランタイム。 |
| Pip | pip >= 23 | `requirements.txt` を `--constraint` なしでインストール。 |
| Build Tooling | PyInstaller 6.x onefolder | `scripts/pyinstaller/duel_logger.spec` を使用。 |
| UI Toolkit | Kivy 2.3.x, KivyMD 1.1.x | SDL2 / ANGLE バイナリ依存を事前に取得。 |
| Packaging Host | GitHub Actions `windows-latest` | ビルド成果物は Release Assets のみに配置。 |

## 1. Python Setup
- 仮想環境を推奨。`python -m venv .venv && .venv\Scripts\activate`。
- `pip install -r requirements.txt` 実行後に `kivy` が GPU 対応のバイナリを参照しているか確認。
- Windows では `set KIVY_NO_CONSOLELOG=1` を `.env` に設定し、ログノイズを抑止。

## 2. OS Dependencies
- Visual C++ 再頒布パッケージ 2019 以降をインストール。
- Windows Defender / SmartScreen でブロックされないよう、未署名バイナリは手動で許可。
- 開発時は `%APPDATA%/DuelPerformanceLogger/` 配下の DB/DSL を versioned backup する。

## 3. Tooling Matrix
- テキストエディタは UTF-8 (BOM 無し) 固定。
- `black` 23.x, `ruff` 0.6.x, `mypy` 1.10.x を静的検査ツールとして採用。
- UI レイアウト確認用に `kivy_inspector` を利用可。実機動作は常にウィンドウサイズ 1280x720 以上で確認する。

## 4. Verification Checklist
1. `python -m compileall app/` でバイトコード生成が警告なく通るか。
2. `pytest` によるユニットテストが完了するか。
3. `function/cmn_resources.py` が mgenplus フォントを正常に登録できるか。
4. `DatabaseManager.ensure_database()` 呼び出しで schema version の差分が無いことを確認。
