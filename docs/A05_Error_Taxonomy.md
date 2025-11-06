# A05. Error Taxonomy

This taxonomy standardizes Duel Performance Logger error codes so logs, UI, and telemetry treat issues consistently.
この分類表は、Duel Performance Logger のエラーコードを標準化し、ログ・UI・テレメトリで一貫した取り扱いを実現します。

## Table of Contents / 目次

The sections describe error codes, log formatting, UI messaging, updater-specific mappings, telemetry usage, and review checks.
以下のセクションでは、エラーコード一覧・ログフォーマット・UI メッセージ・アップデーターの対応付け・テレメトリ活用・確認事項を説明します。

- Error Codes
  - エラーコード一覧
- Log Format
  - ログ出力フォーマット
- UI Messaging Guide
  - UI メッセージガイド
- Updater-specific Errors
  - Updater 特有のエラー
- Telemetry
  - テレメトリ
- Checklist
  - チェックリスト

## <a id="error-codes"></a>Error Codes / エラーコード一覧

Use the standardized table below to align log levels and UI responses.
以下の標準化テーブルを利用して、ログレベルと UI 対応を揃えます。

| コード | 名前 | 原因 | UI 対応 | ログレベル |
|--------|------|------|----------|------------|
| `CFG-001` | ConfigLoadError | `config.json` corruption or JSON decode failure | Show reinitialization dialog | ERROR |
| `CFG-010` | VersionMismatch | `app_version` mismatch requiring migration | Display progress dialog and auto-run | INFO |
| `DB-100` | MigrationFailed | SQL migration failure | Prompt restart after rollback | CRITICAL |
| `UP-200` | UpdateValidationFailed | Download hash mismatch | Offer retry button | WARNING |
| `UP-210` | UpdaterLaunchFailed | Unable to launch `Updater.exe` | Provide manual update guidance | ERROR |
| `UP-230` | UpdaterRollbackApplied | Rollback executed after failure | Inform rollback completion | WARNING |
| `NET-300` | NetworkUnavailable | Network is offline | Show offline banner and use cache | INFO |
| `ASY-400` | AsyncCancelled | User cancelled async task | Toast "キャンセルしました" | INFO |

## <a id="log-format"></a>Log Format / ログ出力フォーマット

Fix the log pattern so analysis teams can search codes efficiently.
分析担当がコード検索しやすいようにログの書式を固定します。

```
[LEVEL] <timestamp> <code> <component> message | context
```

Example: `[ERROR] 2025-10-02T04:30:21Z CFG-001 core.config Failed to load config | path=C:\Users\...`; timestamps use UTC.
例: `[ERROR] 2025-10-02T04:30:21Z CFG-001 core.config Failed to load config | path=C:\Users\...`。タイムスタンプは UTC を使用します。

## <a id="ui-messaging"></a>UI Messaging Guide / UI メッセージガイド

Explain how to present errors and manage translations.
エラーの表示方法と翻訳管理を説明します。

- Display WARNING-or-higher severities with modal dialogs in Japanese and include English glosses in parentheses.
  - 重大度が WARNING 以上のエラーは日本語のモーダルダイアログで表示し、括弧内に英語注釈を添えます。
- Present INFO-level notifications with toasts or the status bar to avoid interrupting user flows.
  - INFO レベルの通知はトーストやステータスバーで表示し、ユーザーの操作を妨げないようにします。
- Define UI strings under `strings.errors.<code>` using the format `"設定を再生成します (Recreate settings)."` to minimize translation drift.
  - 翻訳差分を抑えるため、`strings.errors.<code>` に `"設定を再生成します (Recreate settings)."` の形式で UI 文言を定義します。

## <a id="updater-errors"></a>Updater-specific Errors / Updater 特有のエラー

Map updater exit codes to taxonomy entries so behavior remains predictable.
アップデーターの終了コードを分類に対応させ、挙動を予測可能にします。

- Map exit code 10 to `UP-200`, 20 to `UP-210`, and 30 to `UP-230`; update this mapping whenever the updater changes.
  - 終了コード 10 は `UP-200`、20 は `UP-210`、30 は `UP-230` に対応させ、アップデーター変更時には必ず更新します。
- When a rollback occurs (`UP-230`), log with level WARNING and show "更新をロールバックしました" to the user.
  - ロールバック (`UP-230`) 発生時は WARNING レベルで記録し、UI に「更新をロールバックしました」と表示します。
- Persist updater diagnostics in `%LOCALAPPDATA%/DuelPerformanceLogger/logs/updater.log` for escalation.
  - 追加調査に備えて `%LOCALAPPDATA%/DuelPerformanceLogger/logs/updater.log` にアップデーターの診断情報を保存します。

## <a id="telemetry"></a>Telemetry / テレメトリ

Define telemetry events that capture error activity without blocking the UI.
UI を妨げずにエラー状況を把握できるテレメトリーイベントを定義します。

| Event | Error Codes | Payload |
|-------|-------------|---------|
| `error_raised` | Any | `{ "code": str, "component": str, "fatal": bool }` |
| `update_failed` | `UP-*` | `{ "code": str, "version": target }` |
| `migration_failed` | `DB-100` | `{ "from": old, "to": new }` |

Telemetry dispatch relies on `core.telemetry.queue` and must remain non-blocking to avoid UI delays.
テレメトリー送信は `core.telemetry.queue` に依存し、UI 遅延を防ぐため非ブロッキングを維持します。

## <a id="error-checklist"></a>Checklist / チェックリスト

Review these items when introducing new error codes.
新しいエラーコードを追加する際は次の項目を確認してください。

- [ ] The new error code appears in the table and has registered UI text.
  - [ ] 新しいエラーコードが表に追記され、UI 文言が登録されている。
- [ ] Log output follows the prescribed format.
  - [ ] ログ出力が規定のフォーマットに従っている。
- [ ] Telemetry events satisfy the defined schemas.
  - [ ] テレメトリイベントが定義済みスキーマを満たしている。
- [ ] Mappings to updater exit codes are up to date.
  - [ ] アップデーター終了コードとの対応表が最新化されている。

**Last Updated:** 2025-10-12
**最終更新日:** 2025-10-12
