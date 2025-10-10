# 07. テスト計画 (Test Plan)

このテスト計画は Duel Performance Logger の品質保証プロセスを定義し、PyInstaller one-folder ビルドおよび Updater.exe の検証を含みます。

## テストスコープ

- コアロジック (migrations, config, updater scheduling)
- UI (Kivy/KivyMD screens, KV bindings)
- 非同期処理 (scheduler, progress updates)
- リリースパッケージ (Main.exe, Updater.exe)

## テストタイプ

| タイプ | コマンド | 説明 |
|--------|----------|------|
| 単体テスト | `pytest` | `tests/core`, `tests/async`, `tests/ui` |
| スナップショット | `pytest -m snapshot` | UI ツリーチェック |
| マイグレーション | `pytest -m migration` | バージョンアップ・ダウングレード検証 |
| E2E (Windows) | `scripts/tests/run_e2e.ps1` | PyInstaller ビルドと Updater シナリオ |

## バージョンマトリクス

| 旧バージョン | 新バージョン | 目的 |
|---------------|--------------|------|
| DPL.1.2.0 | DPL.1.3.0 | DB schema v5 → v6 |
| DPL.1.3.0 | DPL.1.4.0 | DSL キー追加確認 |
| DPL.1.4.0 | DPL.1.4.1 | パッチ検証 (config 変更のみ) |

## Updater 検証

1. `python scripts/tools/build.py --mode onefolder` でビルド。
2. `scripts/tests/run_updater_cycle.ps1` を実行し、ステージング更新→再起動を確認。
3. `Updater.exe` の exit code をチェックし、`app.log` に `update_completed` が出力されることを確認。

## 自動化

- GitHub Actions で `pytest` を並列実行 (core/ui, async/migration)。
- Nightly で E2E テストを Windows ランナーにて実施。
- 成果物の SHA256 を算出し、`artifacts/checksums.txt` に記録。

## 手動テストチェックリスト

- [ ] 新規インストールで初回起動が成功。
- [ ] マイグレーション後もユーザーデータが保持。
- [ ] Updater による自動再起動が成功。
- [ ] UI の日本語表示を目視確認。

**Last Updated:** 2025-10-12
