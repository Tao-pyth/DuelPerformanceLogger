# A03. Interface Control Core
### コアインターフェース制御ドキュメント概要
サブシステム間の契約 (configuration、migrations、telemetry、updater) を整理し、英語の API 名称に日本語の運用解説を添えています。

## Table of Contents / 目次
- [Module Interfaces / モジュール間インターフェース](#module-interfaces)
- [Configuration Schema / 設定スキーマ](#configuration-schema)
- [Migration Flow / マイグレーション手順](#migration-flow)
- [Updater Contract / アップデーター契約](#updater-contract)
- [Telemetry Events / テレメトリーイベント](#telemetry-events)
- [Checklist / チェックリスト](#checklist)

## <a id="module-interfaces"></a>Module Interfaces / モジュール間インターフェース
各モジュールの提供/依存関係を表形式で整理し、境界が曖昧にならないようにします。

| Module | Provides | Consumes | Notes |
|--------|----------|----------|-------|
| `core.paths` | `get_app_dir()`, `get_config_path()`, `get_db_path()` | `os`, `platform` | Acts as the single filesystem authority。|
| `core.config` | `load_config()`, `save_config()`, schema versioning | `core.paths`, `core.migrations` | Persists JSON with `app_version`。|
| `core.migrations.runner` | `run_migrations(from_version, to_version)` | `core.config`, `core.db` | Emits progress to `app.log`。|
| `core.db` | SQLite connection pool, query helpers | `core.paths` | Offers transaction context managers。|
| `core.version` | `__version__`, `parse_version()` | None | Canonical semantic version。|
| `core.updater` | `schedule_update(package_path, target_version)` | `subprocess`, `core.paths`, `core.version` | Launches `Updater.exe` from `%TEMP%`。|

## <a id="configuration-schema"></a>Configuration Schema / 設定スキーマ
構成ファイルの必須キーとフォーマットを示します。日本語で扱う際の注意点も併記します。

```json
{
  "app_version": "DPL.1.4.0",
  "language": "ja-JP",
  "telemetry_opt_in": true,
  "last_migration": "2025-09-30T12:00:00Z"
}
```

- `app_version` compares against `core.version.__version__` during startup。バージョン差異でマイグレーションを起動します。
- `last_migration` uses ISO8601 with Zulu timezone。ローカル時刻と混同しないよう注意します。
- Additional keys must define defaults in `core.config.DEFAULTS`。欠損時の初期化エラーを防ぎます。

## <a id="migration-flow"></a>Migration Flow / マイグレーション手順
マイグレーション実行順序を 6 ステップで定義します。

1. Load configuration and compare versions。差異検出時のみ後続処理へ進みます。
2. Backup DB and DSL directories to `%APPDATA%/DuelPerformanceLogger/backups/<timestamp>/`。復旧ポイントを確保します。
3. Execute SQL migrations from `core.migrations.sql` in ascending order。DDL 操作は冪等に保ちます。
4. Apply DSL migrations using YAML patch scripts under `core.migrations.dsl`。設定差分も同期します。
5. Update config defaults and bump `app_version`。整合した状態で保存します。
6. Log success and emit telemetry event `migration_completed` with duration。サポート向けに記録を残します。

## <a id="updater-contract"></a>Updater Contract / アップデーター契約
アップデート適用時の引数契約と戻り値を統一します。

- `core.updater.schedule_update()` stages files under `%TEMP%/DPL_Update_<uuid>`。衝突しない一時領域を確保します。
- The function launches `Updater.exe` with:

```
Updater.exe \
  --install "<install_dir>" \
  --staging "<staging_dir>" \
  --main-name "Main.exe" \
  --args "--via-updater --updated-from=<old> --updated-to=<new>"
```

- Exit codes are standardised:
  - `0` success / 正常終了
  - `10` validation failure (hash mismatch) / 検証失敗
  - `20` permission denied / 権限不足
  - `30` rollback performed / ロールバック実施

## <a id="telemetry-events"></a>Telemetry Events / テレメトリーイベント
可観測性を高めるイベントを定義します。

| Event | Trigger | Payload |
|-------|---------|---------|
| `app_started` | Startup after migrations | `{ "version": __version__, "channel": build_channel }` |
| `migration_completed` | Successful migration | `{ "from": old, "to": new, "duration_ms": int }` |
| `update_download_failed` | HTTP error during download | `{ "status": code, "url": source }` |

Telemetry dispatch relies on `core.telemetry.queue` and must remain non-blocking。UI 応答性を損なわないよう設計します。

## <a id="checklist"></a>Checklist / チェックリスト
インターフェース変更時は必ず確認してください。

- [ ] 新規設定キーにデフォルト値とマイグレーションが揃っている。
- [ ] Updater の終了コードが `core.errors.UpdaterError` にマップされている。
- [ ] テレメトリーペイロードが本ドキュメントのスキーマに一致している。
- [ ] 破壊的マイグレーション前にバックアップが取得されている。

**Last Updated:** 2025-10-12
