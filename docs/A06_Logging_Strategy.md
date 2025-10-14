# A06. Logging Strategy
### ログ戦略の概要
DPL の可観測性を確保するために、ログ出力、ローテーション、監視とテレメトリ運用を統一します。英語で項目を明示し、日本語で背景や運用方法を補足します。

## Table of Contents / 目次
- [Logging Destinations / ログ出力先](#logging-destinations)
- [Log Format & Levels / ログフォーマットとレベル](#log-format-levels)
- [Rotation & Retention / ローテーションと保持](#rotation-retention)
- [Structured Events / 構造化イベント](#structured-events)
- [Monitoring & Telemetry / モニタリングとテレメトリ](#monitoring-telemetry)
- [Checklist / チェックリスト](#logging-checklist)

## <a id="logging-destinations"></a>Logging Destinations / ログ出力先
ランタイムとサポートが参照する主要なログの保存場所です。

- Standard output during development only。開発者のローカルデバッグで利用します。
- File: `%LOCALAPPDATA%/DuelPerformanceLogger/logs/app.log`。本番での一次情報源です。
- Critical events may be forwarded to Windows Event Log (`Application` source)。監査要件を満たします。
- Debug trace: `%LOCALAPPDATA%/DuelPerformanceLogger/logs/debug.log` (`DEBUG` level)。詳細追跡向けです。
- Updater log: `%LOCALAPPDATA%/DuelPerformanceLogger/logs/updater.log`。Updater.exe 専用ログです。
- Application-facing modules (anything under `app/function/`) must emit logs exclusively via `function/cmn_logger.py` helpers。アプリ領域のログ窓口を `cmn_logger` に集約します。
- Direct `logging` module usage is reserved for third-party libraries, bootstrap scripts, and migration scaffolding。標準 `logging` は外部/起動時の最小限ログのみに制限します。

## <a id="log-format-levels"></a>Log Format & Levels / ログフォーマットとレベル
統一された表記により、解析とアラート設定を容易にします。

```
[LEVEL] <ISO8601 timestamp> <component> message | key=value ...
```

- `component` values include `core.migrations`, `ui.menu`, `updater`。モジュール起点を特定します。
- Additional fields follow `key=value` separated by `|`。構造化データを保持します。
- Example: `[INFO] 2025-10-12T02:34:10Z updater Update scheduled | from=DPL.1.3.0 to=DPL.1.4.0`。

Log levels:

| Level | Purpose |
|-------|---------|
| DEBUG | Detailed traces, disabled in CI builds。|
| INFO | Normal operations such as migrations and updater start。|
| WARNING | Recoverable anomalies requiring retry or user notification。|
| ERROR | Failures preventing ongoing use but recoverable after restart。|
| CRITICAL | Catastrophic conditions requiring immediate shutdown。|

## <a id="rotation-retention"></a>Rotation & Retention / ローテーションと保持
ログ肥大化を防ぎ、サポートが必要な期間保管します。

- `app.log` rotates at 5 MB with five generations using `RotatingFileHandler`。容量を管理します。
- Retain logs for 30 days; older files are purged during startup cleanup jobs。保持期間を統一します。
- CI runs emit `logs/ci.log` and upload the file as an artifact。ビルド結果を追跡します。

## <a id="structured-events"></a>Structured Events / 構造化イベント
主要ドメインアクティビティのフィールド規約です。

- Updater events: include `updater.phase` with values `download`, `apply`, `restart`。進行状況を明確化します。
- Migrations: log `migration.step` and `migration.version` for each stage。履歴追跡を容易にします。
- Async tasks: emit `async.task_id` and `async.status` fields。スレッド処理を関連付けます。
- Exception logging must include `context`, `stack`, and `user_input_hash` fields when available。例外発生時はコンテキスト、スタック、ユーザー入力のハッシュを付与し、PII を含めずに追跡可能性を確保します。
- Persist failure payloads under `%LOCALAPPDATA%/DuelPerformanceLogger/logs/errors/` when `cmn_logger.log_exception` receives `persist=True`。重大障害時の添付資料として利用します。

## <a id="monitoring-telemetry"></a>Monitoring & Telemetry / モニタリングとテレメトリ
`docs/08_logging_monitoring.md` の内容を統合し、監視・可視化・メトリクスの指針をまとめます。

- **Alert thresholds**: trigger Slack `#dpl-ops` alerts when `CRITICAL` logs exceed 3 occurrences within 10 minutes or when `update_download_failed` telemetry fires more than twice per release。対応フローを迅速化します。
- **Metrics catalog**:
  - `logs.ingest.count` (per level) collected via Filebeat。
  - `updater.duration.seconds` exported from telemetry events。
  - `migrations.success.rate` derived from `migration_completed` events / attempts。
- **Log rotation alignment**: ensure `debug.log` shares the same retention policy as `app.log`, while `updater.log` keeps 7 generations due to lower volume。サポート時に必要履歴を保持します。
- **Retention policy**: archive logs older than 30 days into `%APPDATA%/DuelPerformanceLogger/archive/<YYYYMM>/` before deletion when `--archive-logs` flag is passed to maintenance scripts。証跡を保持する場合に活用します。
- **Dashboards**: maintain Azure Monitor workbooks `DPL/Logging` (level distribution) and `DPL/Updater` (update funnel)。ダッシュボードのブック ID は Ops チームの wiki で管理します。
- **Paths & collection agents**: Filebeat configuration points to `%LOCALAPPDATA%/DuelPerformanceLogger/logs/*.log` with multiline patterns for stack traces。アップデート時もパスを変更しません。
- **Operational checklist**: incident responders must package logs via `tools/support/package_logs.ps1`, update [`C28_Wiki_Overview.md`](C28_Wiki_Overview.md)#incident-response, and record mitigation history in this strategy file when thresholds change。運用記録を一元化します。

## <a id="logging-checklist"></a>Checklist / チェックリスト
ログ戦略に関連する変更を出す際は以下を確認してください。

- [ ] ログが定義済みフォーマットで出力されている。
- [ ] ローテーション/保持設定が `core.logging.setup()` に反映されている。
- [ ] 構造化フィールドが主要イベントに付与されている。
- [ ] モニタリング閾値とダッシュボードが最新情報に更新された。

**Last Updated:** 2025-10-12
