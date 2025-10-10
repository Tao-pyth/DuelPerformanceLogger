# 08. Release Management / リリース管理

## 1. Versioning
- バージョンスキームは `DPL.<MAJOR>.<MINOR>.<PATCH>`。
- 破壊的変更: MAJOR++ / MINOR, PATCH を 0 にリセット。
- 後方互換追加: MINOR++ / PATCH を 0 にリセット。
- バグ修正: PATCH++。

## 2. Release Checklist
1. `app/function/core/version.py` の `__version__` を更新。
2. `docs/wiki/Overview.md` の「Project Snapshot」を最新化。
3. マイグレーションを実行し、`logs/app.log` に結果を記録。
4. `pytest`, `ruff`, `mypy` を実行。
5. `pyinstaller -y scripts/pyinstaller/duel_logger.spec`。
6. `tools/release/verify_update.py` で Updater の replace-and-relaunch を検証。
7. GitHub Release を作成し、ZIP と SHA256 を添付。

## 3. Communication
- Release Notes は日本語/英語併記で記述。テンプレートは `docs/resource/release_note_template.md`。
- 既知の問題 (Known Issues) は release note の末尾に掲載し、回避策を記載。
- 重大バグ発生時はホットフィックス版を 24 時間以内に配布。

## 4. Post Release Tasks
- Issue Tracker へ「リリース済み」ラベルを追加し、フィードバックを収集。
- 収集したログやクラッシュダンプは 14 日で破棄。
- 次期開発用の `work` ブランチを `main` から再作成し、マージキューをクリア。
