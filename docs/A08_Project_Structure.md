# A08. Project Structure
### プロジェクト構成の概要
リポジトリのレイアウトと所有範囲、PyInstaller one-folder パッケージングの考慮点を整理し、開発者が参照しやすいように英語名と日本語解説を併記します。

## Table of Contents / 目次
- [Directory Overview / ディレクトリ概要](#directory-overview)
- [Packaging Layout / パッケージ構成](#packaging-layout)
- [Data Ownership / データ所有範囲](#data-ownership)
- [Interface Contracts / インターフェース契約](#interface-contracts)
- [Dependency Boundaries / 依存境界](#dependency-boundaries)
- [Checklist / チェックリスト](#structure-checklist)

## <a id="directory-overview"></a>Directory Overview / ディレクトリ概要
主要ディレクトリと担当チーム、役割を表形式で示します。

| Path | Owner | Description |
|------|-------|-------------|
| `app/` | Core Engineering | Python/Eel orchestration code。|
| `app/function/core/` | Core Engineering | Paths, config, migrations, versioning services。|
| `app/function/web/` | UI Team | Eel bridge modules and exposed RPC handlers。|
| `app/resource/` | Core + UI | Runtime assets bundled into builds。|
| `resource/` | Content Team | Fonts, icons, localisation files, web assets。|
| `docs/` | Documentation Team | Authoritative policy and process manuals。|
| `scripts/pyinstaller/` | Build & Release | PyInstaller spec and packaging scripts。|
| `.github/workflows/` | DevOps | CI pipeline definitions。|

## <a id="packaging-layout"></a>Packaging Layout / パッケージ構成
PyInstaller one-folder 出力の構成を示します。

```
DuelPerformanceLogger/
├── Main.exe
├── Updater.exe
├── app/  (Python modules)
├── resource/  (bundled assets)
└── vcruntime140.dll ...
```

- `Main.exe` launches the Eel application via PyInstaller bootstrap。起動の入口です。
- `Updater.exe` ships alongside but executes from `%TEMP%` during updates。自己更新を成立させます。
- Python modules remain importable through `sys._MEIPASS` even when packaged。モジュール解決を保証します。

## <a id="data-ownership"></a>Data Ownership / データ所有範囲
データ配置と責任領域を明確にします。

- User data resides under `%APPDATA%/DuelPerformanceLogger/` including `config.json`, `dsl/`, `db/dpl.sqlite`。バックアップ対象です。
- Migration scripts in `app/function/core/migrations/` define schema evolution and remain the single source of truth。変更時はレビュー必須です。
- Logs route to `%LOCALAPPDATA%/DuelPerformanceLogger/logs/app.log` via `app/function/core/logging.py`。サポートが参照します。

## <a id="interface-contracts"></a>Interface Contracts / インターフェース契約
モジュール間の利用規約をまとめます。

- `app/function/core/paths.py` abstracts filesystem locations; all new modules should consume these helpers。パスの重複定義を避けます。
- Web assets under `resource/web/` load via the central Eel bootstrap in `app/main.py`。UI 初期化を統一します。
- Updater CLI contract is documented in [`A05_Error_Taxonomy.md`](A05_Error_Taxonomy.md) and [`B10_Release_Management.md`](B10_Release_Management.md)。仕様変更時は両方を更新します。

## <a id="dependency-boundaries"></a>Dependency Boundaries / 依存境界
責務分離を保つためのインポート規則です。

- Core modules must not import UI packages to keep headless testing viable。テストの独立性を確保します。
- UI modules may depend on core services but should interact via defined `service_*` modules。共通 API を活用します。
- External integrations (REST, telemetry) live under `app/function/integration/` and must expose async-friendly APIs。バックグラウンド処理と整合させます。

## <a id="structure-checklist"></a>Checklist / チェックリスト
新規コンポーネント追加時の確認項目です。

- [ ] 新規モジュールを必要に応じて `__all__` に登録した。
- [ ] 設定や KV ファイルが画面命名規則に従っている。
- [ ] パス解決に `core.paths` ヘルパーを利用している。
- [ ] Updater 参照が最新の CLI バージョンと整合している。

**Last Updated:** 2025-10-12
