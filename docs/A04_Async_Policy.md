# A04. Async Policy

This policy unifies asynchronous tasks, progress feedback, cancellation, and updater integration in Duel Performance Logger.
このポリシーは、Duel Performance Logger における非同期タスク・進行表示・キャンセル・アップデーター連携を統一します。

## Table of Contents / 目次

The sections outline the runtime model, task registration, progress presentation, error handling, timeout and retry rules, cancellation behavior, testing, and review checks.
以下のセクションでは、ランタイムモデル・タスク登録・進行表示・エラーハンドリング・タイムアウトとリトライ・キャンセル挙動・テスト・確認事項を説明します。

- Runtime Model
  - ランタイムモデル
- Task Registration Flow
  - タスク登録フロー
- Progress Presentation
  - 進行表示
- Error Handling
  - エラーハンドリング
- Timeout & Retry Matrix
  - タイムアウトとリトライ
- Cancellation Policy
  - キャンセルポリシー
- Testing
  - テスト
- Checklist
  - チェックリスト

## <a id="runtime-model"></a>Runtime Model / ランタイムモデル

Clarify how the UI loop and background processing share responsibility.
UI ループとバックグラウンド処理の役割分担を明確にします。

- Run the main loop with Eel (Bottle + Chromium) synchronously on Python while the browser thread renders the UI to keep responsiveness high.
  - メインループは Eel（Bottle + Chromium）を Python 側で同期実行し、ブラウザスレッドで UI を描画して応答性を維持します。
- Prefer `concurrent.futures.ThreadPoolExecutor` over `asyncio` for background tasks and notify the UI with `eel.spawn` when work finishes.
  - バックグラウンドタスクには `asyncio` よりも `concurrent.futures.ThreadPoolExecutor` を優先し、完了時には `eel.spawn` で UI に通知します。
- Route blocking I/O to dedicated executors and refresh UI state via `notify()` or `fetch_snapshot` to avoid blocking rendering.
  - ブロッキング I/O は専用エグゼキューターに委譲し、`notify()` や `fetch_snapshot` で UI 状態を更新して描画ブロックを防ぎます。

## <a id="task-registration"></a>Task Registration Flow / タスク登録フロー

Register tasks through a shared API so progress and cancellation remain consistent.
共通 API を介してタスクを登録し、進行通知とキャンセル制御を統一します。

1. Register work with `core.async.run_in_executor(fn, *, progress_callback)` (planned shared API) to standardize entry points.
   1. 入口を標準化するために、`core.async.run_in_executor(fn, *, progress_callback)`（予定されている共通 API）でタスクを登録します。
2. Report progress by calling `eel.show_progress(progress)` from Python and rendering updates in JavaScript, keeping values between 0.0 and 1.0.
   2. 進行度は Python から `eel.show_progress(progress)` を呼び出し、JavaScript で描画して 0.0〜1.0 の範囲を保ちます。
3. Propagate cancellation tokens with `threading.Event` objects and let the UI invoke `eel.request_cancel()` when users cancel.
   3. `threading.Event` でキャンセルトークンを渡し、ユーザーが中断したときは UI から `eel.request_cancel()` を呼び出します。
4. Log task completion results and surface `notify()` messages to users.
   4. タスク完了結果をログに記録し、`notify()` メッセージでユーザーに知らせます。

## <a id="progress"></a>Progress Presentation / 進行表示

Provide feedback during long-running operations to reduce user uncertainty.
長時間処理でユーザーの不安を軽減するためにフィードバックを提供します。

- Feed values between 0.0 and 1.0 into the progress bar component in `resource/web/static/js/app.js` for consistent visuals.
  - 一貫した表示のために、`resource/web/static/js/app.js` のプログレスバーへ 0.0〜1.0 の値を渡します。
- Emit progress updates for operations longer than one second so the UI reflects ongoing work.
  - 1 秒を超える処理では進行更新を送信し、UI に実行中であることを示します。
- Increase DSL migration progress in increments of 0.1 per step to visualize staged work.
  - DSL マイグレーションではステップごとに 0.1 ずつ進行度を上げ、段階的な作業を可視化します。

## <a id="async-error-handling"></a>Error Handling / エラーハンドリング

Categorize asynchronous exceptions consistently and surface them to the UI and logs.
非同期例外を一貫して分類し、UI とログの双方に伝えます。

- Wrap tasks with the planned `core.errors.AsyncTaskError` before surfacing exceptions to the UI for easier categorization.
  - 例外を UI に渡す前に予定されている `core.errors.AsyncTaskError` でラップし、分類しやすくします。
- Follow [`A05_Error_Taxonomy.md`](A05_Error_Taxonomy.md) when handling updater-related failures to choose retries or fallbacks.
  - アップデーター関連の失敗は [`A05_Error_Taxonomy.md`](A05_Error_Taxonomy.md) に従い、リトライやフォールバックを適切に選択します。
- Log asynchronous exceptions to `logs/app.log` with an `ASYNC` tag and mirror the message on the JavaScript side.
  - 非同期例外は `ASYNC` タグ付きで `logs/app.log` に記録し、同じメッセージを JavaScript 側にも表示します。

## <a id="timeout-retry"></a>Timeout & Retry Matrix / タイムアウトとリトライ

Define allowable durations and retry policies for major processes.
主要処理の許容時間とリトライ方針を定義します。

| Process | Timeout | Retry |
|---------|---------|-------|
| Update package download | 120 seconds | 3 attempts with exponential backoff |
| Telemetry dispatch | 5 seconds | None; leave in queue |
| Migration execution | 60 seconds | Fail immediately and roll back |

## <a id="cancellation"></a>Cancellation Policy / キャンセルポリシー

Explain follow-up steps after a user cancels an operation.
ユーザーが操作をキャンセルした後の後処理を説明します。

- When users cancel, restore the previous state and display a "キャンセルしました" message in the UI.
  - ユーザーがキャンセルした場合は状態を復元し、UI に「キャンセルしました」と表示します。
- After cancellation, invoke scheduler cleanup handlers to remove partial artifacts.
  - キャンセル後はスケジューラのクリーンアップハンドラーを呼び出し、途中生成されたデータを削除します。
- Allow updater cancellation only during downloads; the apply phase must remain non-interruptible for integrity.
  - アップデーターのキャンセルはダウンロード中のみ許可し、適用フェーズは整合性確保のため中断不可とします。

## <a id="async-testing"></a>Testing / テスト

Maintain quality by covering asynchronous scenarios in automated tests.
自動化テストで非同期シナリオを網羅し、品質を維持します。

- Add unit tests under `tests/async/test_executor.py` (planned) for success, cancellation, and error cases.
  - 成功・キャンセル・エラーを対象とする単体テストを `tests/async/test_executor.py`（予定）に追加します。
- Run `pytest -m async` regularly in CI to focus on asynchronous behavior.
  - CI で `pytest -m async` を定期的に実行し、非同期挙動を重点的に確認します。
- Validate progress notifications via Playwright or other end-to-end tests to ensure DOM elements update correctly.
  - DOM 要素の更新を保証するため、Playwright などの E2E テストで進行通知を検証します。

## <a id="async-checklist"></a>Checklist / チェックリスト

Review the following items after updating asynchronous features.
非同期機能を更新した際には次の項目を確認してください。

- [ ] Long-running operations include progress feedback.
  - [ ] 長時間処理に進行表示が追加されている。
- [ ] Cancellation flows update the UI appropriately.
  - [ ] キャンセルフローが適切に UI に反映されている。
- [ ] Error handling aligns with the error taxonomy.
  - [ ] エラーハンドリングがエラーカタログと一致している。
- [ ] Async test markers cover the latest scenarios.
  - [ ] 非同期テストのマーキングが最新シナリオを網羅している。

**Last Updated:** 2025-10-12
**最終更新日:** 2025-10-12
