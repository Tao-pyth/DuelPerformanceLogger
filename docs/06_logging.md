# 06. ロギング戦略 (Logging Strategy)

ロギングはマイグレーション、Updater、非同期処理の可観測性を担保するための最重要コンポーネントです。本ドキュメントではログ構造、保持ポリシー、分析手法を定義します。

## ログ出力先

- アプリ稼働中の標準出力 (開発時のみ)。
- ファイル: `%LOCALAPPDATA%/DuelPerformanceLogger/logs/app.log`。
- 重要イベントは Windows Event Log (`Application` ソース) にもレポート可能。

## ログフォーマット

```
[LEVEL] <ISO8601 timestamp> <component> message | key=value ...
```

- `component` は `core.migrations`, `ui.menu`, `updater` などのモジュール名。
- 追加フィールドは `key=value` 形式で `|` 区切り。
- 例: `[INFO] 2025-10-12T02:34:10Z updater Update scheduled | from=DPL.1.3.0 to=DPL.1.4.0`。

## ログレベル

| レベル | 用途 |
|--------|------|
| DEBUG | 開発・詳細トレース。CI では無効。|
| INFO | 正常系の重要イベント。マイグレーション成功、Updater 起動など。|
| WARNING | リカバリ可能な異常。リトライやユーザ通知が必要。|
| ERROR | ユーザ操作継続不能だが再起動で回復可能。|
| CRITICAL | 即座にアプリ終了が必要な致命的状況。|

## ローテーションと保持

- `app.log` は 5MB を上限とし、`RotatingFileHandler` で 5 世代保持。
- ログ保存期間は 30 日。古いファイルは起動時のクリーンアップジョブで削除。
- CI 実行時は `logs/ci.log` を生成し、Artifacts に添付。

## 構造化イベント

- Updater イベント: `updater.phase` フィールドに `download`, `apply`, `restart` を設定。
- マイグレーション: `migration.step` にステップ名、`migration.version` に対象バージョンを記録。
- 非同期タスク: `async.task_id`, `async.status` を出力。

## 監視と分析

- Windows 上では `powershell Get-Content -Wait app.log` でリアルタイム監視。
- サポート問い合わせではログの ZIP を受領し、`scripts/tools/log_analyzer.py` で解析。
- 重大インシデントは Azure Monitor に転送し、アラートを発報。

## Checklist

- [ ] ログは規定フォーマットで出力される。
- [ ] ローテーション設定が `core.logging.setup()` に反映。
- [ ] 構造化フィールドが主要イベントに付与される。
- [ ] CI ログがアーティファクト化される。

**Last Updated:** 2025-10-12
