# A06. Logging Strategy

This strategy aligns logging outputs, rotation, monitoring, and telemetry so Duel Performance Logger remains observable.
この戦略は、Duel Performance Logger のログ出力・ローテーション・監視・テレメトリを統一し、可観測性を確保します。

## Table of Contents / 目次

The sections cover destinations, formats, rotation, structured events, monitoring guidance, and review checks.
以下のセクションでは、出力先・フォーマット・ローテーション・構造化イベント・監視指針・確認事項について説明します。

- Logging Destinations
  - ログ出力先
- Log Format & Levels
  - ログフォーマットとレベル
- Rotation & Retention
  - ローテーションと保持
- Structured Events
  - 構造化イベント
- Monitoring & Telemetry
  - モニタリングとテレメトリ
- Checklist
  - チェックリスト

## <a id="logging-destinations"></a>Logging Destinations / ログ出力先

Document where runtime and support teams can find primary logs.
ランタイムおよびサポート担当が主要ログを確認できる場所を明示します。

- Development uses standard output only; production relies on `%LOCALAPPDATA%/DuelPerformanceLogger/logs/app.log` as the primary source.
  - 開発時は標準出力のみを使用し、本番では `%LOCALAPPDATA%/DuelPerformanceLogger/logs/app.log` を一次情報源とします。
- Capture debug traces in `%LOCALAPPDATA%/DuelPerformanceLogger/logs/debug.log` and updater activity in `%LOCALAPPDATA%/DuelPerformanceLogger/logs/updater.log`.
  - 詳細なトレースは `%LOCALAPPDATA%/DuelPerformanceLogger/logs/debug.log`、アップデーターの挙動は `%LOCALAPPDATA%/DuelPerformanceLogger/logs/updater.log` に記録します。
- Application modules under `app/function/` must emit through `function/cmn_logger.py`; direct `logging` usage is reserved for bootstrap scripts and third-party libraries.
  - `app/function/` 配下のモジュールは `function/cmn_logger.py` からログを出力し、標準 `logging` の直接利用は起動スクリプトや外部ライブラリに限定します。

## <a id="log-format-levels"></a>Log Format & Levels / ログフォーマットとレベル

Standardize message structure and severity usage.
メッセージ構造と重要度の使い分けを標準化します。

```
[LEVEL] <ISO8601 timestamp> <component> message | key=value ...
```

- Components include names such as `core.migrations`, `ui.menu`, and `updater` so analysts can pinpoint sources.
  - `core.migrations`、`ui.menu`、`updater` などのコンポーネント名を付与し、解析者が発生源を特定できるようにします。
- Append structured fields as `key=value` segments separated by `|`, for example `[INFO] 2025-10-12T02:34:10Z updater Update scheduled | from=DPL.1.3.0 to=DPL.1.4.0`.
  - 構造化フィールドは `|` 区切りの `key=value` 形式で追加し、例として `[INFO] 2025-10-12T02:34:10Z updater Update scheduled | from=DPL.1.3.0 to=DPL.1.4.0` を利用します。
- Use DEBUG for detailed traces (disabled in CI), INFO for normal operations, WARNING for recoverable anomalies, ERROR for blocking failures, and CRITICAL for shutdown-level incidents.
  - DEBUG は詳細トレース（CI では無効）、INFO は通常処理、WARNING は復旧可能な異常、ERROR は継続不可の障害、CRITICAL は即時停止が必要な事象に使用します。

## <a id="rotation-retention"></a>Rotation & Retention / ローテーションと保持

Prevent uncontrolled log growth while preserving enough history for support.
ログの肥大化を防ぎつつ、サポートに必要な履歴を保持します。

- Rotate `app.log` at 5 MB with five generations using `RotatingFileHandler` and apply the same policy to `debug.log`.
  - `app.log` は `RotatingFileHandler` を用いて 5 MB ごとに 5 世代分ローテーションし、`debug.log` も同じ方針に従います。
- Keep updater logs for seven generations because of lower volume but longer investigative value.
  - アップデーターのログはボリュームが小さいため 7 世代保持し、調査時の価値を確保します。
- Retain logs for 30 days and archive older files to `%APPDATA%/DuelPerformanceLogger/archive/<YYYYMM>/` when maintenance scripts run with `--archive-logs`.
  - 保持期間は 30 日とし、メンテナンススクリプトを `--archive-logs` 付きで実行した場合は `%APPDATA%/DuelPerformanceLogger/archive/<YYYYMM>/` に古いファイルを保管します。

## <a id="structured-events"></a>Structured Events / 構造化イベント

Apply consistent fields to major activities to simplify analysis.
主要アクティビティに一貫したフィールドを適用し、解析を容易にします。

- Include `updater.phase` values (`download`, `apply`, `restart`) for updater events.
  - アップデーターイベントには `updater.phase`（`download`、`apply`、`restart`）を付与します。
- Record `migration.step` and `migration.version` during schema changes for reproducible history.
  - スキーマ変更時には `migration.step` と `migration.version` を記録して履歴を再現可能にします。
- When logging exceptions, supply `context`, `stack`, and `user_input_hash` where available, and persist payloads under `%LOCALAPPDATA%/DuelPerformanceLogger/logs/errors/` if `persist=True`.
  - 例外ログには可能な限り `context`・`stack`・`user_input_hash` を付与し、`persist=True` の場合は `%LOCALAPPDATA%/DuelPerformanceLogger/logs/errors/` にペイロードを保存します。

## <a id="monitoring-telemetry"></a>Monitoring & Telemetry / モニタリングとテレメトリ

Summarize alerting, metrics, and dashboards that rely on logging data.
ログデータを基盤とするアラート・メトリクス・ダッシュボードの要点をまとめます。

- Trigger Slack `#dpl-ops` alerts when CRITICAL logs exceed three within ten minutes or when `update_download_failed` telemetry fires more than twice per release.
  - 10 分間に CRITICAL ログが 3 件を超える、または `update_download_failed` テレメトリが 1 リリースで 2 回を超えた場合に Slack `#dpl-ops` へアラートを送信します。
- Track metrics such as `logs.ingest.count`, `updater.duration.seconds`, and `migrations.success.rate` via Filebeat and telemetry exports.
  - Filebeat やテレメトリから `logs.ingest.count`、`updater.duration.seconds`、`migrations.success.rate` などのメトリクスを収集します。
- Maintain Azure Monitor workbooks `DPL/Logging` and `DPL/Updater`, and package logs for incidents using `tools/support/package_logs.ps1` while updating [`C28_Wiki_Overview.md`](C28_Wiki_Overview.md).
  - Azure Monitor のワークブック `DPL/Logging` と `DPL/Updater` を維持し、インシデント時は `tools/support/package_logs.ps1` でログを収集して [`C28_Wiki_Overview.md`](C28_Wiki_Overview.md) を更新します。

## <a id="logging-checklist"></a>Checklist / チェックリスト

Verify these items before shipping logging-related changes.
ログ関連の変更をリリースする前に次の項目を確認してください。

- [ ] Logs follow the defined format.
  - [ ] ログが定義済みフォーマットで出力されている。
- [ ] Rotation and retention settings are reflected in `core.logging.setup()`.
  - [ ] ローテーションと保持設定が `core.logging.setup()` に反映されている。
- [ ] Structured fields are attached to major events.
  - [ ] 主要イベントに構造化フィールドが付与されている。
- [ ] Monitoring thresholds and dashboards are up to date.
  - [ ] モニタリング閾値とダッシュボードが最新情報に更新されている。

**Last Updated:** 2025-10-12
**最終更新日:** 2025-10-12
