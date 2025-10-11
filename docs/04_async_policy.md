# 04. 非同期処理ポリシー (Async Policy)

本ドキュメントは Duel Performance Logger における非同期処理の設計指針を定義します。進行表示、キャンセル制御、Updater 連携を含む全機能が対象です。

## ランタイムモデル

- メインループ: Eel (Bottle + Chromium) が Python 側で同期実行し、UI はブラウザスレッドで描画。
- 非同期タスク: Python 側は `asyncio` ではなく `concurrent.futures.ThreadPoolExecutor` に集約し、完了後に `eel.spawn` で UI へ通知。
- スレッド利用: ブロッキング I/O は専用 Executor へ移し、UI 更新は `notify()` または `fetch_snapshot` 再実行で反映する。

## タスク登録フロー

1. `core.async.run_in_executor(fn, *, progress_callback)` でタスクを登録する（将来的な共通 API）。
2. 進行状況は Python 側から `eel.show_progress(progress)` を呼び出し、JS でレンダリングする。
3. キャンセルは共有 `threading.Event` を引数に受け渡し、UI のボタンから `eel.request_cancel()` を発火させる。
4. タスク完了時はロガーへ結果を書き込み、`notify()` でユーザーへ完了メッセージを送る。

## 進行表示 (Progress)

- `resource/web/static/js/app.js` の進行バーコンポーネントに 0.0〜1.0 の値を渡す。
- 長時間処理 (> 1s) は必ずフロントエンドへ進行率を送出する。
- DSL マイグレーションは各ステップ完了ごとに 0.1 ずつ進行率を増加させる。

## エラーハンドリング

- すべてのタスクは `core.errors.AsyncTaskError` （予定）でラップし、UI へは一般化したエラーメッセージを送る。
- Updater 連携時のエラーは `[05_error_taxonomy](05_error_taxonomy.md)` に従いリトライ／フォールバック処理を実施。
- 非同期例外は `logs/app.log` に `ASYNC` タグ付きで出力し、JS 側にも通知する。

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

- `tests/async/test_executor.py`（予定）にユニットテストを追加し、成功・キャンセル・例外ケースを網羅。
- `pytest -m async` で非同期テストを実行。
- 進行通知は Playwright/E2E テストで検証し、DOM の進行バーが更新されることを確認する。

## Checklist

- [ ] 長時間処理に進行表示を追加。
- [ ] キャンセルフローが UI に反映される。
- [ ] エラーハンドリングが分類表と一致。
- [ ] 非同期テストタグを更新。

**Last Updated:** 2025-11-05
