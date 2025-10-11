# 00. Environment Baseline / 環境ベースライン

本書では、リポジトリに含まれる最新アセットと整合する開発環境ベースラインを定義し、追加で検証済みマシンのスナップショットを提示する。

| Item | Baseline | Asset / Notes |
| ---- | -------- | ------------- |
| Python | 3.10.x (shipping) | `requirements.txt` は Python 3.10 で `pip-compile` されたもの。3.13.7 でも検証済。 |
| Build Tooling | PyInstaller 6.x onefolder | `scripts/pyinstaller/duel_logger.spec` を利用。 |
| UI Toolkit | Kivy 2.3.x, KivyMD 1.2.0 | `kivy==2.3.1`, `kivymd==1.2.0` を想定ベースラインとして固定。 |
| Packaging Host | GitHub Actions `windows-latest` | Release Assets のみでバイナリ配布。 |

## 1. Python Runtime / Python ランタイム
- 仮想環境の利用を推奨。`python -m venv .venv && .venv\Scripts\activate`。
- 公式サポートは 3.10.x。CI での `pip-compile` も 3.10 系で実行される。
- 互換性確認済み構成として Windows 10/11 上の Python 3.13.7 を記録（詳細は §5.2）。
- `pip install -r requirements.txt` 実行後に `kivy` が GPU 対応バイナリ（SDL2/ANGLE）を解決しているか確認。
- Windows 開発時は `set KIVY_NO_CONSOLELOG=1` を `.env` に設定し、コンソールログを抑止。

## 2. Windows Prerequisites / Windows 依存関係
- Visual C++ 再頒布パッケージ 2019 以降を導入。
- SmartScreen や Defender でのブロック時は開発者署名のないバイナリを手動許可。
- `%APPDATA%/DuelPerformanceLogger/` 配下の DB/DSL は作業前にバージョン付きでバックアップ。

## 3. Tooling Matrix / 開発ツール構成
- テキストエディタは UTF-8 (BOM 無し) を前提。
- 静的検査: `black` 23.x、`ruff` 0.6.x、`mypy` 1.10.x。
- `pip-compile` により依存関係を固定。更新時は `requirements.in` を変更してから再生成する。
- UI レイアウト確認には `kivy_inspector` を使用可能。実機検証はウィンドウ 1280x720 以上を推奨。

## 4. Verification Checklist / 検証チェックリスト
1. `python -m compileall app/` が警告なしで完了すること。
2. `pytest` による単体テストを完了させること。
3. `function/cmn_resources.py` による mgenplus フォント登録が成功すること。
4. `DatabaseManager.ensure_database()` 呼び出しで schema version の差分が無いこと。

## 5. Package Snapshots / パッケージスナップショット

### 5.1 requirements.txt (pip-compile output)
`requirements.txt` は Python 3.10 で `pip-compile` を実行して生成している。UI レイヤの基幹依存は下記バージョンで固定している。

| Package | Version | Source |
| ------- | ------- | ------ |
| kivy | 2.3.1 | pip wheel (GPU 対応バイナリを同梱) |
| kivymd | 1.2.0 | pip wheel |

### 5.2 Verified Windows Host (2025-08-14)
開発チームの Windows 11 マシンにおいても、Kivy 2.3.1 および KivyMD 1.2.0 の組み合わせで UI レイヤを検証済み。Python 3.13.7 上で動作確認した結果、公式サポート対象である 3.10 系と挙動差は確認されていない。

> **Note:** 出荷アセットは常に §5.1 の Kivy 2.3.1 / KivyMD 1.2.0 を基準とする。追加依存のバージョン確認は個別案件に応じて実施すること。
