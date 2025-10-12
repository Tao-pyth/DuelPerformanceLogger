# A05. Error Taxonomy
### エラー分類表の概要
DPL の主要エラーコードを定義し、ログ・UI・テレメトリ間で一貫した取り扱いを実現します。分類名は英語を保ち、日本語で運用指針を補足します。

## Table of Contents / 目次
- [Error Codes / エラーコード一覧](#error-codes)
- [Log Format / ログ出力フォーマット](#log-format)
- [UI Messaging Guide / UI メッセージガイド](#ui-messaging)
- [Updater-specific Errors / Updater 特有のエラー](#updater-errors)
- [Telemetry / テレメトリ](#telemetry)
- [Checklist / チェックリスト](#error-checklist)

## <a id="error-codes"></a>Error Codes / エラーコード一覧
ログレベルと UI 対応を含む標準化されたエラーコードのテーブルです。

| コード | 名前 | 原因 | UI 対応 | ログレベル |
|--------|------|------|----------|------------|
| `CFG-001` | ConfigLoadError | `config.json` corruption or JSON decode failure | Show reinitialisation dialog | ERROR |
| `CFG-010` | VersionMismatch | `app_version` mismatch requiring migration | Display progress dialog and auto-run | INFO |
| `DB-100` | MigrationFailed | SQL migration failure | Prompt restart after rollback | CRITICAL |
| `UP-200` | UpdateValidationFailed | Download hash mismatch | Offer retry button | WARNING |
| `UP-210` | UpdaterLaunchFailed | Unable to launch `Updater.exe` | Provide manual update guidance | ERROR |
| `UP-230` | UpdaterRollbackApplied | Rollback executed after failure | Inform rollback completion | WARNING |
| `NET-300` | NetworkUnavailable | Network is offline | Show offline banner and use cache | INFO |
| `ASY-400` | AsyncCancelled | User cancelled async task | Toast "キャンセルしました" | INFO |

## <a id="log-format"></a>Log Format / ログ出力フォーマット
ログ表記を固定し、解析時にコード検索しやすくします。

```
[LEVEL] <timestamp> <code> <component> message | context
```

Example: `[ERROR] 2025-10-02T04:30:21Z CFG-001 core.config Failed to load config | path=C:\Users\...`。タイムスタンプは UTC で記録します。

## <a id="ui-messaging"></a>UI Messaging Guide / UI メッセージガイド
ユーザーへの表示方法と翻訳方針です。

- Display WARNING-or-higher severities via modal dialogs in Japanese with English glosses in parentheses。重大度を明確に伝えます。
- Present INFO-level notifications via toasts or the status bar to avoid interrupting flows。軽微な情報は非モーダルで通知します。
- Define UI strings under `strings.errors.<code>` with format `"設定を再生成します (Recreate settings)."`。翻訳差分を最小化します。

## <a id="updater-errors"></a>Updater-specific Errors / Updater 特有のエラー
Updater.exe の終了コードとエラーコードを対応付けます。

- Map exit code 10 → `UP-200`, 20 → `UP-210`, 30 → `UP-230`。アップデーター側変更時はこの表を更新します。
- On rollback (`UP-230`), log with level WARNING and present "更新をロールバックしました" to users。状態を明示します。
- Persist updater diagnostics under `%LOCALAPPDATA%/DuelPerformanceLogger/logs/updater.log` for escalation。調査に活用します。

## <a id="telemetry"></a>Telemetry / テレメトリ
テレメトリで送信するイベントとペイロードを定義します。

| Event | Error Codes | Payload |
|-------|-------------|---------|
| `error_raised` | Any | `{ "code": str, "component": str, "fatal": bool }` |
| `update_failed` | `UP-*` | `{ "code": str, "version": target }` |
| `migration_failed` | `DB-100` | `{ "from": old, "to": new }` |

Telemetry is dispatched via `core.telemetry.queue` and must be non-blocking。UI 遅延を防ぐためバックグラウンドで送信します。

## <a id="error-checklist"></a>Checklist / チェックリスト
エラーコード追加時の確認項目です。

- [ ] 新しいエラーコードを表へ追記し UI 文言を登録した。
- [ ] ログ出力がフォーマット規約に従っている。
- [ ] テレメトリイベントが定義済みスキーマを満たしている。
- [ ] Updater exit code とのマッピングを更新した。

**Last Updated:** 2025-10-12
