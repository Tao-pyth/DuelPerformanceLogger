# A03. Interface Control Core

This document clarifies contracts between subsystems such as configuration, migrations, telemetry, and the updater, pairing API names with operational guidance.
このドキュメントは、設定・マイグレーション・テレメトリー・アップデーターなどのサブシステム間契約を整理し、API 名称に運用ガイダンスを対応させます。

## Table of Contents / 目次

The sections cover module interfaces, configuration schema, migration flow, updater contracts, telemetry events, and review checkpoints.
以下のセクションでは、モジュールインターフェース・設定スキーマ・マイグレーション手順・アップデーター契約・テレメトリーイベント・確認項目を取り上げます。

- Module Interfaces
  - モジュール間インターフェース
- Configuration Schema
  - 設定スキーマ
- Migration Flow
  - マイグレーション手順
- Updater Contract
  - アップデーター契約
- Telemetry Events
  - テレメトリーイベント
- Checklist
  - チェックリスト

## <a id="module-interfaces"></a>Module Interfaces / モジュール間インターフェース

List the responsibilities each module provides and consumes so boundaries remain explicit.
各モジュールの提供責務と依存を整理し、境界を明確に保ちます。

| Module | Provides | Consumes | Notes |
|--------|----------|----------|-------|
| `core.paths` | `get_app_dir()`, `get_config_path()`, `get_db_path()` | `os`, `platform` | Serves as the single filesystem authority. |
| `core.config` | `load_config()`, `save_config()`, schema versioning | `core.paths`, `core.migrations` | Persists JSON with `app_version`. |
| `core.migrations.runner` | `run_migrations(from_version, to_version)` | `core.config`, `core.db` | Emits progress into `app.log`. |
| `core.db` | SQLite connection pool, query helpers | `core.paths` | Offers transaction context managers. |
| `core.version` | `__version__`, `parse_version()` | None | Defines the canonical semantic version. |
| `core.updater` | `schedule_update(package_path, target_version)` | `subprocess`, `core.paths`, `core.version` | Launches `Updater.exe` from `%TEMP%`. |

## <a id="configuration-schema"></a>Configuration Schema / 設定スキーマ

Describe required keys and formats in the configuration file along with handling tips.
構成ファイルで必須となるキーとフォーマット、および運用時の注意点を説明します。

```json
{
  "app_version": "DPL.1.4.0",
  "language": "ja-JP",
  "telemetry_opt_in": true,
  "last_migration": "2025-09-30T12:00:00Z"
}
```

- `app_version` compares to `core.version.__version__` on startup to trigger migrations when differences exist.
  - `app_version` は起動時に `core.version.__version__` と比較し、差異があればマイグレーションを起動します。
- `last_migration` uses ISO 8601 with the Zulu timezone to avoid confusion with local timestamps.
  - `last_migration` は Zulu タイムゾーンの ISO 8601 形式を使用し、ローカル時刻との混同を防ぎます。
- Any additional key must define defaults in `core.config.DEFAULTS` to prevent initialization failures when values are missing.
  - 追加するキーには必ず `core.config.DEFAULTS` の既定値を定義し、欠損時の初期化失敗を避けます。

## <a id="migration-flow"></a>Migration Flow / マイグレーション手順

Run migrations in the following sequence to preserve reliability.
信頼性を保つため、次の順序でマイグレーションを実行します。

1. Load configuration, compare versions, and continue only when a difference is detected.
   1. 設定を読み込みバージョンを比較し、差異が検出された場合のみ後続処理に進みます。
2. Back up the database and DSL directories to `%APPDATA%/DuelPerformanceLogger/backups/<timestamp>/` to keep a recovery point.
   2. 復旧ポイントを確保するために、データベースと DSL ディレクトリを `%APPDATA%/DuelPerformanceLogger/backups/<timestamp>/` にバックアップします。
3. Execute SQL migrations from `core.migrations.sql` in ascending order while keeping DDL idempotent.
   3. `core.migrations.sql` の SQL マイグレーションを昇順で実行し、DDL を冪等に保ちます。
4. Apply DSL migrations using YAML patch scripts under `core.migrations.dsl` so configuration data remains aligned.
   4. 設定差分を同期するために、`core.migrations.dsl` 配下の YAML パッチスクリプトで DSL マイグレーションを適用します。
5. Update configuration defaults and bump `app_version` before saving the result.
   5. 結果を保存する前に設定の既定値を更新し、`app_version` を引き上げます。
6. Log success and emit the `migration_completed` telemetry event with execution duration for support visibility.
   6. 成功をログに記録し、実行時間を含む `migration_completed` テレメトリーイベントを送信してサポートチームに可視化します。

## <a id="updater-contract"></a>Updater Contract / アップデーター契約

Keep the updater invocation consistent by standardizing arguments and exit codes.
引数と終了コードを標準化して、アップデーターの呼び出しを一貫させます。

- `core.updater.schedule_update()` stages files under `%TEMP%/DPL_Update_<uuid>` to reserve a collision-free workspace.
  - `core.updater.schedule_update()` は `%TEMP%/DPL_Update_<uuid>` にファイルを配置し、衝突のない作業領域を確保します。
- The function launches `Updater.exe` with the following arguments.
  - この関数は以下の引数で `Updater.exe` を起動します。

```
Updater.exe \
  --install "<install_dir>" \
  --staging "<staging_dir>" \
  --main-name "Main.exe" \
  --args "--via-updater --updated-from=<old> --updated-to=<new>"
```

- Exit codes map to standard outcomes: `0` success, `10` validation failure, `20` permission denied, and `30` rollback performed.
  - 終了コードは標準的な結果に対応し、`0` は成功、`10` は検証失敗、`20` は権限不足、`30` はロールバック実施を表します。

## <a id="telemetry-events"></a>Telemetry Events / テレメトリーイベント

Define telemetry events that maintain observability without blocking the UI.
UI をブロックせずに可観測性を確保するテレメトリーイベントを定義します。

| Event | Trigger | Payload |
|-------|---------|---------|
| `app_started` | Startup after migrations | `{ "version": __version__, "channel": build_channel }` |
| `migration_completed` | Successful migration | `{ "from": old, "to": new, "duration_ms": int }` |
| `update_download_failed` | HTTP download failure | `{ "status": code, "url": source }` |

Telemetry dispatch relies on `core.telemetry.queue` and must remain non-blocking to preserve UI responsiveness.
テレメトリー送信は `core.telemetry.queue` に依存し、UI の応答性を維持するため非ブロッキングである必要があります。

## <a id="checklist"></a>Checklist / チェックリスト

Review these items whenever interface contracts change.
インターフェース契約を変更する際は次の項目を確認してください。

- [ ] New configuration keys ship with defaults and migrations.
  - [ ] 新しい設定キーに既定値とマイグレーションが揃っている。
- [ ] Updater exit codes map to `core.errors.UpdaterError`.
  - [ ] アップデーターの終了コードが `core.errors.UpdaterError` に対応付けられている。
- [ ] Telemetry payloads follow the schemas defined in this document.
  - [ ] テレメトリーペイロードが本ドキュメントのスキーマに一致している。
- [ ] Backups exist before any destructive migration runs.
  - [ ] 破壊的マイグレーションを実行する前にバックアップが取得されている。

**Last Updated:** 2025-10-12
**最終更新日:** 2025-10-12
