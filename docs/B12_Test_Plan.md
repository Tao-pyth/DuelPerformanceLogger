# B12. テスト計画 (Test Plan)
Duel Performance Logger の品質保証プロセスを日本語主体で整理し、PyInstaller one-folder ビルドや Updater.exe 検証を含めた計画を提示します。

## 目次 / Table of Contents
- [テストスコープ (Test Scope)](#test-scope)
- [テストタイプ (Test Types)](#test-types)
- [バージョンマトリクス (Version Matrix)](#version-matrix)
- [Updater 検証 (Updater Validation)](#updater-validation)
- [自動化 (Automation)](#automation)
- [手動テストチェックリスト (Manual Checklist)](#manual-checklist)

## <a id="test-scope"></a>テストスコープ (Test Scope)
- コアロジック (migrations, config, updater scheduling)
- UI (Eel Web フロントエンド、DOM レンダリング)
- 非同期処理 (scheduler, progress updates)
- リリースパッケージ (Main.exe, Updater.exe)

## <a id="test-types"></a>テストタイプ (Test Types)
| タイプ | コマンド | 説明 |
|--------|----------|------|
| 単体テスト | `pytest` | `tests/core`, `tests/async`, `tests/web` |
| スナップショット | `npx playwright test --grep @ui-snapshot` | DOM スナップショット比較 |
| マイグレーション | `pytest -m migration` | バージョンアップ・ダウングレード検証 |
| E2E (Windows) | `scripts/tests/run_e2e.ps1` | PyInstaller ビルドと Updater シナリオ |

## <a id="version-matrix"></a>バージョンマトリクス (Version Matrix)
| 旧バージョン | 新バージョン | 目的 |
|---------------|--------------|------|
| DPL.1.2.0 | DPL.1.3.0 | DB schema v5 → v6 |
| DPL.1.3.0 | DPL.1.4.0 | DSL キー追加確認 |
| DPL.1.4.0 | DPL.1.4.1 | パッチ検証 (config 変更のみ) |

## <a id="updater-validation"></a>Updater 検証 (Updater Validation)
1. `python scripts/tools/build.py --mode onefolder` でビルドします。
2. `scripts/tests/run_updater_cycle.ps1` を実行し、ステージング更新から再起動までを検証します。
3. `Updater.exe` の exit code を確認し、`app.log` に `update_completed` が出力されることを確認します。

## <a id="automation"></a>自動化 (Automation)
- GitHub Actions で `pytest` を並列実行します (core/web, async/migration)。
- Nightly Windows ランナーで E2E テストを実施します。
- 成果物の SHA256 を算出し、`artifacts/checksums.txt` に記録します。

## <a id="manual-checklist"></a>手動テストチェックリスト (Manual Checklist)
- [ ] 新規インストールで初回起動が成功した。
- [ ] マイグレーション後もユーザーデータが保持されている。
- [ ] Updater による自動再起動が成功した。
- [ ] UI の日本語表示を目視確認した。

**最終更新日 (Last Updated):** 2025-10-12
