# 05. エラー分類表 (Error Taxonomy)

Duel Performance Logger における主要エラーの分類とハンドリング指針を定義します。エラーはログ、UI、テレメトリで一貫したコードを使用します。

## エラーコード一覧

| コード | 名前 | 原因 | UI 対応 | ログレベル |
|--------|------|------|----------|------------|
| `CFG-001` | ConfigLoadError | `config.json` が破損、JSON decode 失敗 | 設定初期化ダイアログを表示し再生成 | ERROR |
| `CFG-010` | VersionMismatch | `app_version` 不一致でマイグレーション必要 | 進行ダイアログを表示して自動実行 | INFO |
| `DB-100` | MigrationFailed | SQL 実行失敗 | ロールバック後に再起動促す | CRITICAL |
| `UP-200` | UpdateValidationFailed | ダウンロードハッシュ不一致 | 再試行ボタンを表示 | WARNING |
| `UP-210` | UpdaterLaunchFailed | `Updater.exe` 起動不能 | 手動更新案内 | ERROR |
| `UP-220` | UpdaterStagingCleanup | 一時ディレクトリ削除失敗 | 無視しログのみ | WARNING |
| `NET-300` | NetworkUnavailable | ネットワーク未接続 | オフライン表示しキャッシュ使用 | INFO |
| `ASY-400` | AsyncCancelled | ユーザーキャンセル | トースト「キャンセルしました」 | INFO |

## ログ出力フォーマット

```
[LEVEL] <timestamp> <code> <component> message | context
```

例: `[ERROR] 2025-10-02T04:30:21Z CFG-001 core.config Failed to load config | path=C:\\Users\\...`

## UI メッセージガイド

- 重大度が WARNING 以上の場合、ダイアログで日本語メッセージを表示。
- INFO レベルはトースト通知またはステータスバーで表示。
- UI 文言は `strings.errors.<code>` に定義し、英訳は括弧内に記載 (例: `"設定を再生成します (Recreate settings)."`).

## Updater 特有のエラー

- `UP-200`〜`UP-230` は `Updater.exe` の exit code と連携。
- Exit code 10 → `UP-200`、20 → `UP-210`、30 → `UP-230 (RollbackApplied)`。
- Rollback 成功時はログレベル WARNING、ユーザーには「更新をロールバックしました」を表示。

## テレメトリ

| イベント | エラーコード | フィールド |
|----------|--------------|-----------|
| `error_raised` | 任意 | `{ "code": str, "component": str, "fatal": bool }` |
| `update_failed` | `UP-*` | `{ "code": str, "version": target }` |
| `migration_failed` | `DB-100` | `{ "from": old, "to": new }` |

## Checklist

- [ ] 新しいエラーコードは表に追加し、UI 文言を用意。
- [ ] ログ出力がフォーマット規約に準拠。
- [ ] テレメトリイベントが schema を満たす。
- [ ] Updater exit code のマッピングを更新。

**Last Updated:** 2025-10-12
