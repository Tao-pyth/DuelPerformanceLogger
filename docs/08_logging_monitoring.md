# 03. Logging & Monitoring / ログと監視

## 1. Logging Channels
- アプリログ: `%LOCALAPPDATA%/DuelPerformanceLogger/logs/app.log` (1 日 1 ファイル, UTF-8)。
- デバッグログ: `%LOCALAPPDATA%/DuelPerformanceLogger/logs/debug.log`。`DEBUG` レベル以上を記録。
- 更新ログ: `%LOCALAPPDATA%/DuelPerformanceLogger/logs/updater.log`。Updater.exe の実行記録専用。

## 2. Format & Retention
- ログ形式は `[YYYY-MM-DD HH:MM:SS][LEVEL][module] message`。
- 30 日より古いログは起動時に自動削除。閾値は `config["logging"]["retention_days"]` で変更可。
- 重大障害 (`CRITICAL`) 発生時は Windows イベントログにも転送する (pywin32 `win32evtlogutil.ReportEvent`)。

## 3. Monitoring Hooks
- `function.cmn_logger` は `logging.LoggerAdapter` を返し、`extra={"request_id": str(uuid4())}` を付与。
- UI のトースト通知と同期させるため、`log_info` `log_warning` `log_error` ヘルパーを利用する。
- Updater.exe からの進行状況は `%LOCALAPPDATA%/DuelPerformanceLogger/status/update.json` に JSON で出力。

## 4. Incident Response
1. ログを収集し、`tools/support/package_logs.ps1` で ZIP 化。
2. 発生バージョン・OS ビルド・再現手順を `docs/wiki/Overview.md#Incident-Report` に追記。
3. `docs/03_logging_monitoring.md` に対応状況を履歴として更新。
