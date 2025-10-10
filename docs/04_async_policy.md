# 04. 非同期処理ポリシー (Async Policy)

本ドキュメントは Duel Performance Logger における非同期処理の設計指針を定義します。進行表示、キャンセル制御、Updater 連携を含む全機能が対象です。

## ランタイムモデル

- メインループ: Kivy の UI スレッド上で動作。
- 非同期タスク: `asyncio` ベースで `core.async.scheduler` が管理。
- スレッド利用: ブロッキング I/O は `ThreadPoolExecutor` にオフロードし、UI 更新は `@mainthread` で復帰する。

## タスク登録フロー

1. `scheduler.enqueue(coro, *, progress_token, cancel_token)` でタスクを登録。
2. `progress_token` は `ui.events.bus` 経由で進行率を publish。
3. `cancel_token` は `ui.dialogs.confirm_cancel` などから設定され、タスクは `CancelledError` を発火する。
4. タスク完了時は `scheduler.finalize()` がログ出力し、必要に応じてトースト通知を表示。

## 進行表示 (Progress)

- `ProgressOverlay` は 0.0〜1.0 の値を受け取り、`Updater` 進行と共通の UI コンポーネントを使用。
- 長時間処理 (> 1s) は必ず進行表示を出す。
- DSL マイグレーションはステップ単位で 0.1 ずつ進行率を増加させる。

## エラーハンドリング

- すべてのタスクは `core.errors.AsyncTaskError` でラップされる。
- Updater 連携時のエラーは `[05_error_taxonomy](05_error_taxonomy.md)` に従いリトライ／フォールバック処理を実施。
- 非同期例外は `logs/app.log` に `ASYNC` タグ付きで出力。

## タイムアウトとリトライ

| 処理 | タイムアウト | リトライ |
|------|---------------|----------|
| 更新パッケージダウンロード | 120 秒 | 3 回 (指数バックオフ) |
| テレメトリ送信 | 5 秒 | なし、キューに残す |
| マイグレーション | 60 秒 | 即時失敗、ロールバック |

## キャンセルポリシー

- ユーザーがキャンセルした場合、状態を復元し UI に "キャンセルしました" を表示。
- キャンセル後は `scheduler` がクリーンアップハンドラを呼び、半端データを削除。
- Updater のキャンセルはダウンロード中のみ可能。適用フェーズでは不可。

## テスト

- `tests/async/test_scheduler.py` にユニットテストを追加し、成功・キャンセル・例外ケースを網羅。
- `pytest -m async` で非同期テストを実行。
- 進行通知は `tests/ui/test_progress_overlay.py` のスナップショットで検証。

## Checklist

- [ ] 長時間処理に進行表示を追加。
- [ ] キャンセルフローが UI に反映される。
- [ ] エラーハンドリングが分類表と一致。
- [ ] 非同期テストタグを更新。

**Last Updated:** 2025-10-12
