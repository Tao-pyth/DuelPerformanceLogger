# 04. Async & Progress Policy / 非同期処理・進捗表示方針

## 1. Threading Rules
- UI スレッド (Kivy メインループ) で重い処理は実行しない。`function.cmn_async.run_in_executor` を利用。
- 同期 I/O は `ThreadPoolExecutor(max_workers=4)` に委譲し、戻り値は `Clock.schedule_once` で UI へ反映。
- Python の `asyncio` は採用しない。Kivy の event loop と整合しないため。

## 2. Progress Feedback
- 長時間処理 (> 500ms) は必ずプログレス表示 (ダイアログ or snackbar) を出す。
- 進捗率が不明な処理はインジケータをインデターミネイト表示に設定し、タイムアウト時はリトライ導線を用意。
- CSV エクスポートなど、完了時にはトースト通知で保存先パスを表示。

## 3. Cancellation & Retry
- Updater.exe 実行時はキャンセル不可。代わりに `--dry-run` オプションを提供し、検証モードで動作確認。
- DB マイグレーションは途中失敗時に自動ロールバックし、再実行は安全であることを保証。
- 非同期タスクは `function.cmn_async.AsyncJobRegistry` で追跡し、重複実行を防止。

## 4. Testing Guidance
- `tests/async/test_job_registry.py` を追加し、重複タスク抑止ロジックを単体テスト。
- UI からの操作は `pytest --kivy` プラグインを利用して自動化し、プログレスダイアログの表示/非表示を検証する。
