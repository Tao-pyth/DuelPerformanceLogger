# A00. Baseline Environment & Toolchain

This reference outlines the environment prerequisites that Duel Performance Logger (DPL) developers and CI pipelines must share, covering supported operating systems, Python toolchains, and operational expectations.
このリファレンスは、Duel Performance Logger (DPL) の開発者と CI パイプラインが共通で把握すべき環境前提をまとめたものであり、対応 OS・Python ツールチェーン・運用上の期待事項を網羅します。

## Table of Contents / 目次

The following sections describe the baseline assumptions for platforms, dependencies, storage, updater integration, CI, security, and release checklists.
以下のセクションでは、プラットフォーム・依存関係・ストレージ・アップデーター連携・CI・セキュリティ・リリースチェックリストに関する前提条件を説明します。

- Supported Platforms
  - 対応プラットフォーム
- Development Dependencies
  - 開発依存関係
- Storage Layout
  - ストレージ配置
- Updater Integration
  - アップデーター連携
- CI Expectations
  - CI 想定事項
- Security Baseline
  - セキュリティ基準
- Checklist
  - チェックリスト

## <a id="supported-platforms"></a>Supported Platforms / 対応プラットフォーム

DPL is primarily distributed for Windows 10/11 with a PyInstaller one-folder layout and relies on the Eel runtime; the versions in the table must be validated during development.
DPL は Windows 10/11 向けの配布を前提とし、PyInstaller のワンフォルダー構成と Eel ランタイムに依存するため、下表のバージョンを開発時に必ず検証する必要があります。

| Component | Version | Notes |
|-----------|---------|-------|
| OS | Windows 10 22H2 / Windows 11 23H2 | Primary execution environment |
| Python | 3.13.x (CPython) | Used for development and PyInstaller builds |
| Eel | 0.16.x | UI bridge (Chromium/Edge runtime) |
| Web Assets | ES2020+, CSS Grid | Served from `resource/web/` |
| SQLite | 3.45+ | Embedded via Python stdlib |
| PyInstaller | 6.x | One-folder packaging |

## <a id="development-dependencies"></a>Development Dependencies / 開発依存関係

Install the required tools alongside their commands while enforcing consistent virtual-environment usage.
必須ツールの導入にはコマンドを併せて提示し、仮想環境の利用を徹底します。

1. Install Python 3.13 and ensure `pip`, `venv`, and `wheel` are available; always work inside a virtual environment.
   1. Python 3.13 をインストールし、`pip`・`venv`・`wheel` が利用できることを確認し、常に仮想環境で作業します。
2. Create a virtual environment with `python -m venv .venv`, then activate it via `Scripts\\activate` or `source`.
   2. `python -m venv .venv` で仮想環境を作成し、`Scripts\\activate` または `source` で有効化します。
3. Install dependencies by running `pip install -r requirements.txt`, configuring `PIP_INDEX_URL` if you are behind a proxy.
   3. `pip install -r requirements.txt` を実行して依存関係を導入し、プロキシ環境では `PIP_INDEX_URL` を設定します。
4. Add Windows 10 SDK command-line tools for signing and resource inspection, verifying access to `signtool.exe` and `makeappx.exe`.
   4. 署名とリソース検査のために Windows 10 SDK のコマンドラインツールを導入し、`signtool.exe` と `makeappx.exe` にアクセスできることを確認します。
5. Place `pyinstaller` on the `PATH` or invoke it as a module (`python -m PyInstaller`), preferring module invocation on CI.
   5. `pyinstaller` を `PATH` に配置するか `python -m PyInstaller` として呼び出し、CI ではモジュール呼び出しを推奨します。

## <a id="storage-layout"></a>Storage Layout / ストレージ配置

Document the operational directories so that support staff can readily collect logs and user data.
サポート担当者がログやユーザーデータを容易に収集できるよう、運用ディレクトリを明示します。

- Install directory: `%PROGRAMFILES%/DuelPerformanceLogger/` (one-folder output).
  - インストールディレクトリ: `%PROGRAMFILES%/DuelPerformanceLogger/`（ワンフォルダー出力）。
- Writable data: `%APPDATA%/DuelPerformanceLogger/` stores configuration, DSL files, and the SQLite database per user profile.
  - 書き込みデータ: `%APPDATA%/DuelPerformanceLogger/` に設定・DSL ファイル・SQLite データベースをユーザープロファイルごとに保存します。
- Logs: `%LOCALAPPDATA%/DuelPerformanceLogger/logs/app.log` is the primary log subject to rotation.
  - ログ: `%LOCALAPPDATA%/DuelPerformanceLogger/logs/app.log` を主要ログとし、ローテーション対象とします。

## <a id="updater-integration"></a>Updater Integration / アップデーター連携

Maintain compatibility with `Updater.exe` by shipping aligned binaries and tracking temporary workspace behavior.
`Updater.exe` との互換性を維持するために、整合したバイナリの配布と一時ワークスペースの挙動管理を行います。

- Distribute `Updater.exe` alongside `Main.exe` within the one-folder output so versions remain aligned.
  - ワンフォルダー出力内で `Main.exe` と並列に `Updater.exe` を配布し、バージョン整合性を保ちます。
- Execute updates from `%TEMP%/DPL_Update_*` to enable self-replacement and include the temporary folder in support logs.
  - 自己入れ替えを可能にするため `%TEMP%/DPL_Update_*` から更新処理を実行し、一時フォルダーをサポートログに含めます。
- Keep the versioned command-line contract (`v1`) backward compatible and update the CLI specification whenever arguments change.
  - バージョン管理されたコマンドライン仕様 (`v1`) の後方互換性を維持し、引数変更時には CLI 仕様書を必ず更新します。

## <a id="ci-expectations"></a>CI Expectations / CI 想定事項

Define the CI/CD requirements that guarantee reproducible builds and release outputs.
再現性のあるビルドとリリース成果物を確保するための CI/CD 要件を定義します。

- The GitHub Actions workflow `windows-build.yml` must provision Python 3.13 and track runner OS updates.
  - GitHub Actions のワークフロー `windows-build.yml` で Python 3.13 を用意し、ランナー OS の更新に追随します。
- Cache `.venv` or `pip` packages with `actions/cache`, keyed by the `requirements.txt` hash to shorten build time.
  - `actions/cache` を使って `.venv` または `pip` パッケージを `requirements.txt` のハッシュでキャッシュし、ビルド時間を短縮します。
- Produce the artifact `DuelPerformanceLogger-<version>-win64.zip` that contains the one-folder build and signed executables.
  - ワンフォルダー構成と署名済み実行ファイルを含む `DuelPerformanceLogger-<version>-win64.zip` を成果物として生成します。
- Publish release notes referencing [`B10_Release_Management.md`](B10_Release_Management.md) and keep the link updated when names change.
  - [`B10_Release_Management.md`](B10_Release_Management.md) を参照するリリースノートを公開し、名称変更時はリンクを更新します。

## <a id="security-baseline"></a>Security Baseline / セキュリティ基準

Outline the minimum safeguards required to distribute secure updates.
安全な更新配布を実現するために必要な最低限の保護策を示します。

- Require TLS 1.2 or higher for update downloads, enforcing the same level on corporate proxies.
  - 更新ダウンロードには TLS 1.2 以上を必須とし、社内プロキシにも同等の水準を求めます。
- Validate SHA256 signatures against values published in the release notes and roll back automatically on failure.
  - リリースノートに掲載した値と照合して SHA256 署名を検証し、失敗時には自動的にロールバックします。
- Store signing certificates in Azure Key Vault and retrieve them through OIDC so credentials are never left on local machines.
  - 署名証明書は Azure Key Vault に保管し、OIDC を介して取得してローカルに資格情報を残さないようにします。

## <a id="checklist"></a>Checklist / チェックリスト

Use the following checklist for final verification before releases.
リリース前の最終確認として次のチェックリストを使用します。

- [ ] Python 3.13.x installed and active.
  - [ ] Python 3.13.x がインストールされ有効化されている。
- [ ] Requirements installed from lock-approved sources.
  - [ ] 承認済みソースから依存関係をインストールしている。
- [ ] Fonts validated with Japanese UI.
  - [ ] 日本語 UI でフォント検証を完了している。
- [ ] CI artifacts include both `Main.exe` and `Updater.exe`.
  - [ ] CI 成果物に `Main.exe` と `Updater.exe` の両方が含まれている。

**Last Updated:** 2025-10-12
**最終更新日:** 2025-10-12
