# A04. Async Policy
### 非同期処理ポリシーの概要
DPL における非同期タスク、進行表示、キャンセル制御、Updater 連携の統一指針です。英語の API 名称を保持しながら、日本語で設計意図を解説します。

## Table of Contents / 目次
- [Runtime Model / ランタイムモデル](#runtime-model)
- [Task Registration Flow / タスク登録フロー](#task-registration)
- [Progress Presentation / 進行表示](#progress)
- [Error Handling / エラーハンドリング](#async-error-handling)
- [Timeout & Retry Matrix / タイムアウトとリトライ](#timeout-retry)
- [Cancellation Policy / キャンセルポリシー](#cancellation)
- [Testing / テスト](#async-testing)
- [Checklist / チェックリスト](#async-checklist)

## <a id="runtime-model"></a>Runtime Model / ランタイムモデル
UI ループとバックグラウンド処理の役割分担を明確にします。

- Main loop: Eel (Bottle + Chromium) runs synchronously on Python while the browser thread renders the UI。UI の応答性を重視します。
- Async tasks: Prefer `concurrent.futures.ThreadPoolExecutor` instead of `asyncio` to align with Eel。完了後に `eel.spawn` で UI 通知します。
- Thread usage: Route blocking I/O to dedicated executors and refresh UI via `notify()` or `fetch_snapshot` re-fetch。描画をブロックしない設計です。

## <a id="task-registration"></a>Task Registration Flow / タスク登録フロー
共通 API を経由してタスクを登録し、進行通知とキャンセル制御を統一します。

1. Register tasks with `core.async.run_in_executor(fn, *, progress_callback)` (planned shared API)。導入準備としてインターフェースを固定します。
2. Report progress by invoking `eel.show_progress(progress)` from Python and render via JavaScript。進行率は 0.0〜1.0 を維持します。
3. Propagate cancellation tokens using `threading.Event` objects; UI triggers `eel.request_cancel()` when the user cancels。中断操作を可視化します。
4. Log task completion results and surface `notify()` messages to users。完了情報をロギングと UI の両方へ出力します。

## <a id="progress"></a>Progress Presentation / 進行表示
長時間処理でのフィードバック設計を定義します。

- Feed values between 0.0 and 1.0 into the progress bar component in `resource/web/static/js/app.js`。表示の統一感を保ちます。
- Emit progress updates for operations longer than one second。ユーザーの不安を軽減します。
- Increase DSL migration progress in 0.1 increments per step。段階的な可視化を実現します。

## <a id="async-error-handling"></a>Error Handling / エラーハンドリング
非同期例外の分類と通知方法を統一します。

- Wrap all tasks with `core.errors.AsyncTaskError` (planned) before surfacing to UI。分類しやすい共通例外に揃えます。
- Follow [`A05_Error_Taxonomy.md`](A05_Error_Taxonomy.md) when handling updater-related failures。再試行とフォールバックを適切に選択します。
- Log async exceptions to `logs/app.log` with an `ASYNC` tag and mirror the message on the JS side。サポートとユーザー双方に通知します。

## <a id="timeout-retry"></a>Timeout & Retry Matrix / タイムアウトとリトライ
主要処理の許容時間とリトライポリシーです。

| Process | Timeout | Retry |
|---------|---------|-------|
| Update package download | 120 seconds | 3 attempts (exponential backoff) |
| Telemetry dispatch | 5 seconds | None; leave in queue |
| Migration execution | 60 seconds | Fail immediately and rollback |

## <a id="cancellation"></a>Cancellation Policy / キャンセルポリシー
ユーザー操作に応じた後処理を定義します。

- When users cancel, restore state and display "キャンセルしました" on the UI。操作結果を明確に伝えます。
- After cancellation, invoke scheduler cleanup handlers to remove partial artefacts。中途半端なデータを残さないようにします。
- Allow updater cancellation only during download; applying phase is non-interruptible。整合性を優先します。

## <a id="async-testing"></a>Testing / テスト
非同期処理の品質を維持するためのテスト方針です。

- Add unit tests under `tests/async/test_executor.py` (planned) covering success, cancellation, and error cases。シナリオを網羅します。
- Run `pytest -m async` for targeted async tests。CI で定期的に確認します。
- Validate progress notifications via Playwright/E2E tests ensuring DOM bars update correctly。フロントエンド挙動を保証します。

## <a id="async-checklist"></a>Checklist / チェックリスト
非同期機能を更新した際に確認してください。

- [ ] 長時間処理へ進行表示が追加されている。
- [ ] キャンセルフローが UI に反映されている。
- [ ] エラーハンドリングがエラーカタログと一致する。
- [ ] 非同期テストタグが最新のケースを網羅している。

**Last Updated:** 2025-10-12
