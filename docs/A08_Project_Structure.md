# A08. Project Structure

This document explains the repository layout, ownership areas, and PyInstaller considerations for Duel Performance Logger.
このドキュメントは、Duel Performance Logger のリポジトリ構成・担当範囲・PyInstaller の考慮点を説明します。

## Table of Contents / 目次

The sections cover directory overviews, packaging, data ownership, interface contracts, dependency boundaries, and review checks.
以下のセクションでは、ディレクトリ概要・パッケージ構成・データ所有範囲・インターフェース契約・依存境界・確認事項を扱います。

- Directory Overview
  - ディレクトリ概要
- Packaging Layout
  - パッケージ構成
- Data Ownership
  - データ所有範囲
- Interface Contracts
  - インターフェース契約
- Dependency Boundaries
  - 依存境界
- Checklist
  - チェックリスト

## <a id="directory-overview"></a>Directory Overview / ディレクトリ概要

Summarize major directories with owners and responsibilities.
主要ディレクトリの担当者と責務をまとめます。

| Path | Owner | Description |
|------|-------|-------------|
| `app/` | Core Engineering | Python/Eel orchestration code |
| `app/function/core/` | Core Engineering | Paths, config, migrations, versioning |
| `app/function/web/` | UI Team | Eel bridge modules and exposed RPC handlers |
| `app/resource/` | Core + UI | Runtime assets bundled into builds |
| `resource/` | Content Team | Fonts, icons, localization files, web assets |
| `docs/` | Documentation Team | Policy and process manuals |
| `scripts/pyinstaller/` | Build & Release | PyInstaller specifications and packaging scripts |
| `.github/workflows/` | DevOps | CI pipeline definitions |

## <a id="packaging-layout"></a>Packaging Layout / パッケージ構成

Describe the PyInstaller one-folder output and key binaries.
PyInstaller のワンフォルダー出力と主要バイナリを説明します。

```
DuelPerformanceLogger/
├── Main.exe
├── Updater.exe
├── app/  (Python modules)
├── resource/  (bundled assets)
└── vcruntime140.dll ...
```

- `Main.exe` launches the Eel application through the PyInstaller bootstrap.
  - `Main.exe` は PyInstaller のブートストラップを介して Eel アプリを起動します。
- `Updater.exe` ships with the package but executes from `%TEMP%` during updates to enable self-replacement.
  - `Updater.exe` はパッケージに同梱され、更新時には `%TEMP%` から実行されて自己更新を成立させます。
- Packaged Python modules remain importable through `sys._MEIPASS` so module resolution continues to work.
  - パッケージ化された Python モジュールは `sys._MEIPASS` を通じて読み込まれ、モジュール解決が継続します。

## <a id="data-ownership"></a>Data Ownership / データ所有範囲

Clarify where runtime data lives and who maintains it.
実行時データの配置と担当者を明確にします。

- Store user data under `%APPDATA%/DuelPerformanceLogger/`, including `config.json`, `dsl/`, and `db/dpl.sqlite`, and treat these as backup targets.
  - ユーザーデータは `config.json`、`dsl/`、`db/dpl.sqlite` を含めて `%APPDATA%/DuelPerformanceLogger/` に保存し、バックアップ対象とします。
- Maintain migration scripts in `app/function/core/migrations/` as the single source of truth for schema evolution.
  - スキーマ変更は `app/function/core/migrations/` のスクリプトを唯一の情報源として管理します。
- Send logs to `%LOCALAPPDATA%/DuelPerformanceLogger/logs/app.log` via `app/function/core/logging.py` for support access.
  - ログは `app/function/core/logging.py` を通じて `%LOCALAPPDATA%/DuelPerformanceLogger/logs/app.log` に出力し、サポートが参照できるようにします。

## <a id="interface-contracts"></a>Interface Contracts / インターフェース契約

Outline usage rules between modules to prevent drift.
モジュール間の利用規約を整理し、責務の逸脱を防ぎます。

- `app/function/core/paths.py` abstracts filesystem locations; all new modules should consume these helpers instead of redefining paths.
  - `app/function/core/paths.py` はファイルパスを抽象化するため、新規モジュールはパスを再定義せずヘルパーを利用します。
- Web assets under `resource/web/` load through the centralized Eel bootstrap in `app/main.py`.
  - `resource/web/` 配下の Web アセットは `app/main.py` の Eel ブートストラップを経由して読み込みます。
- Keep the updater CLI contract aligned with [`A05_Error_Taxonomy.md`](A05_Error_Taxonomy.md) and [`B10_Release_Management.md`](B10_Release_Management.md) whenever specifications change.
  - アップデーターの CLI 契約を更新する際は [`A05_Error_Taxonomy.md`](A05_Error_Taxonomy.md) と [`B10_Release_Management.md`](B10_Release_Management.md) を同時に整合させます。

## <a id="dependency-boundaries"></a>Dependency Boundaries / 依存境界

Preserve separation of concerns by enforcing import rules.
責務分離を維持するため、インポート規則を適用します。

- Core modules must not import UI packages so that headless testing remains viable.
  - コアモジュールは UI パッケージをインポートせず、ヘッドレステストの実行性を保ちます。
- UI modules may depend on core services but should interact through defined `service_*` modules.
  - UI モジュールはコアサービスに依存できますが、定義済みの `service_*` モジュールを介して連携します。
- Place external integrations (REST, telemetry) in `app/function/integration/` and provide async-friendly APIs.
  - 外部連携（REST やテレメトリ）は `app/function/integration/` に配置し、非同期に適した API を提供します。

## <a id="structure-checklist"></a>Checklist / チェックリスト

Use the following checks when adding new components.
新しいコンポーネントを追加する際に次の項目を確認してください。

- [ ] New modules are registered in `__all__` when appropriate.
  - [ ] 必要に応じて新規モジュールを `__all__` に登録している。
- [ ] Configuration or key-value files follow screen naming conventions.
  - [ ] 設定や KV ファイルが画面命名規則に従っている。
- [ ] Path resolution relies on `core.paths` helpers.
  - [ ] パス解決に `core.paths` のヘルパーを利用している。
- [ ] Updater references align with the current CLI version.
  - [ ] アップデーターの参照が最新の CLI バージョンと一致している。

**Last Updated:** 2025-10-12
**最終更新日:** 2025-10-12
