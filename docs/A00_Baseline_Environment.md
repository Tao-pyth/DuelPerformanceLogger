# A00. Baseline Environment & Toolchain
### 基盤環境とツールチェーンの概要
Duel Performance Logger (DPL) の開発者と CI が共有すべき環境前提を整理したリファレンスです。対応 OS や Python ツールチェーンなどのドメイン用語は英語で提示しつつ、必要な運用ポイントを日本語で補足します。

## Table of Contents / 目次
- [Supported Platforms / 対応プラットフォーム](#supported-platforms)
- [Development Dependencies / 開発依存関係](#development-dependencies)
- [Storage Layout / ストレージ配置](#storage-layout)
- [Updater Integration / アップデーター連携](#updater-integration)
- [CI Expectations / CI 想定事項](#ci-expectations)
- [Security Baseline / セキュリティ基準](#security-baseline)
- [Checklist / チェックリスト](#checklist)

## <a id="supported-platforms"></a>Supported Platforms / 対応プラットフォーム
Windows 10/11 を中心とした配布であり、PyInstaller one-folder 構成と Eel ランタイムの両立が前提です。下表で開発者が検証すべきバージョンを明示します。

| Component | Version | Notes |
|-----------|---------|-------|
| OS | Windows 10 22H2 / Windows 11 23H2 | Primary execution environment |
| Python | 3.13.x (CPython) | Used for development and PyInstaller builds |
| Eel | 0.16.x | UI bridge (Chromium/Edge runtime) |
| Web Assets | ES2020+, CSS Grid | Served from `resource/web/` |
| SQLite | 3.45+ | Embedded via Python stdlib |
| PyInstaller | 6.x | One-folder packaging |

## <a id="development-dependencies"></a>Development Dependencies / 開発依存関係
必須ツールの導入手順を英語のコマンドとともに日本語で補足します。

1. Install Python 3.13 and ensure `pip`, `venv`, and `wheel` are available。仮想環境の利用を徹底します。
2. Create a virtual environment: `python -m venv .venv`。作成後に `Scripts\activate` または `source` で有効化します。
3. Activate the environment and install requirements: `pip install -r requirements.txt`。プロキシ環境では `PIP_INDEX_URL` を設定します。
4. Install Windows 10 SDK command-line tools for signing and resource inspection。`signtool.exe` と `makeappx.exe` を利用できることを確認します。
5. Configure `pyinstaller` path in `PATH` or invoke via module (`python -m PyInstaller`)。CI ではモジュール呼び出しを推奨します。

## <a id="storage-layout"></a>Storage Layout / ストレージ配置
運用ディレクトリの場所を明示し、サポート担当者がログ収集しやすい状態を保ちます。

- Install directory: `%PROGRAMFILES%/DuelPerformanceLogger/` (one-folder)。
- Writable data: `%APPDATA%/DuelPerformanceLogger/` for config, DSL, and SQLite DB。ユーザープロファイルごとに分離されます。
- Logs: `%LOCALAPPDATA%/DuelPerformanceLogger/logs/app.log`。ローテーション対象となる主要ログです。

## <a id="updater-integration"></a>Updater Integration / アップデーター連携
Updater.exe との協調動作を維持するための項目をまとめています。

- `Updater.exe` ships alongside `Main.exe` within the one-folder output。整合したバージョンを常に同梱します。
- Updates are executed from `%TEMP%/DPL_Update_*` to allow self-replacement。アップデーターの一時フォルダーを監視ログに含めます。
- Command-line contract is versioned (`v1`) and must remain backward compatible。引数追加時は CLI 仕様書を同時更新します。

## <a id="ci-expectations"></a>CI Expectations / CI 想定事項
CI/CD で守るべき要件を列挙します。

- GitHub Actions workflow `windows-build.yml` provisions Python 3.13。ランナーの OS 更新に追随します。
- Cache `.venv` or `pip` packages via `actions/cache` keyed by `requirements.txt` hash。ビルド時間を短縮します。
- Produce artifact `DuelPerformanceLogger-<version>-win64.zip` containing the one-folder build。署名済みの EXE を含めること。
- Publish release notes referencing [`B10_Release_Management.md`](B10_Release_Management.md)。新名称へリンクを更新済みです。

## <a id="security-baseline"></a>Security Baseline / セキュリティ基準
更新配布の安全性を担保する最低要件を示します。

- Enforce TLS 1.2+ for update downloads。社内プロキシ設定にも同水準を求めます。
- Validate SHA256 signatures against values published in release notes。署名検証失敗時は自動でロールバックします。
- Store signing certificates in Azure Key Vault; pipeline retrieves via OIDC。資格情報をローカルに残さない運用を徹底します。

## <a id="checklist"></a>Checklist / チェックリスト
リリース前の最終確認として活用してください。

- [ ] Python 3.13.x installed and active。
- [ ] Requirements installed from lock-approved sources。
- [ ] Fonts validated with Japanese UI。
- [ ] CI artifacts include both `Main.exe` and `Updater.exe`。

**Last Updated:** 2025-10-12
