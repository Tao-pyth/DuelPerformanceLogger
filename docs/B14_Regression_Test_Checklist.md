# B14. 回帰テスト実行チェックリスト (Regression Test Execution Checklist)

Duel Performance Logger に対して仕様変更やバグ修正を実施した後、品質を担保するためのテストおよびスモークテストの必須項目をまとめます。優先度の高いテストスイートを明確化し、結果の記録と問題発生時の対応フローを標準化することが目的です。

## 1. 優先度の高いテストスイート (High-Impact Test Suites)
変更内容にかかわらず、以下のテストはリグレッションリスクが高いため実行を推奨します。複数の観点で機能劣化を検出できるよう、テストケースの期待値と対象モジュールを併記しています。

| コマンド | カバレッジの要点 | 実行タイミング |
|----------|------------------|----------------|
| `pytest tests/test_versioning.py` | DB スキーマバージョンの正規化、ターゲットバージョン解決、マイグレーションディレクトリの走査処理。 | マイグレーション追加、`app/function/core/versioning.py` の変更、環境変数 `DPL_MIGRATIONS_ROOT` を扱うロジック変更時。 |
| `pytest tests/test_csv_restore.py` | CSV バックアップの復元、ドライラン挙動、エラーログ生成、YouTube 連携フィールドの整合性。 | バックアップ/リストア処理 (`app/function/core/backup_restore.py`, `DatabaseManager`) の変更時。 |
| `pytest tests/test_cmn_database.py` | 共通 DB マネージャの接続初期化、テーブル作成、例外ハンドリング。 | DB 接続レイヤ (`app/function/DatabaseManager`) の更新時。 |
| `pytest tests/test_recording_features.py` | 対戦記録エクスポート、統計計算、タグ/メモ処理。 | 対戦記録 UI/API (`app/function/recording_features.py` など) の変更時。 |
| `pytest tests/test_youtube_uploader.py` | YouTube アップロードフラグ、キュー管理、API レスポンス処理。 | YouTube 連携 (`app/function/core/youtube_uploader.py` など) の変更時。 |

> **補足:** フル回帰として `pytest` をルートで実行することが望ましいが、時間制約がある場合も上記 5 コマンドは必須とします。

## 2. CLI / PyInstaller 向けスモークテスト (CLI & PyInstaller Smoke Tests)
CLI ツールおよび PyInstaller ビルド成果物について、最小限の起動確認コマンドを定義します。新規開発や依存ライブラリ更新後に必ず実行してください。

| ツール / 成果物 | コマンド | 確認ポイント |
|------------------|----------|--------------|
| バックアップ復元 CLI | `python -m cli.restore_from_backup --help` | オプションヘルプが表示されること、依存モジュールの ImportError が発生しないこと。 |
| PyInstaller one-folder ビルド | `dist/DuelPerformanceLogger/Main.exe --version` | バージョン情報が出力されること。`Main.exe` が起動しない場合は `dist/` 生成プロセス (`python scripts/tools/build.py --mode onefolder`) を再確認。 |
| Updater 実行ファイル | `dist/DuelPerformanceLogger/Updater.exe --check-only` | 更新確認が成功し終了コード 0 を返すこと。CI で PowerShell スクリプト `scripts/tests/run_updater_cycle.ps1` を併用。 |

## 3. テスト結果の記録とマッピング表の見直しルール (Operational Rules)
1. すべての実行コマンドと結果 (成功/失敗、日時、担当者) を `docs/test_runs/` 配下のテキストファイル、もしくはチケット管理ツールに記録します。テンプレート例:
   ```text
   [2025-02-14 18:30 JST] pytest tests/test_versioning.py … PASS
   [2025-02-14 18:45 JST] python -m cli.restore_from_backup --help … PASS
   ```
2. いずれかのコマンドが失敗した場合は、直近のマッピング表 (例: スキーマバージョン対応表、CSV 列マッピング表) を確認し、更新漏れやフィールド名の齟齬がないか検証します。必要に応じて該当ドキュメント (例: `docs/C29_CMN_Module_Rename.md`) を更新し、変更履歴に記録します。
3. マッピング表更新後は、失敗したテストを再実行し、修正が妥当であることを確認した上で結果ログを追記します。
4. 連続して 2 回以上同一テストが失敗した場合は、Issue を発行し原因分析・恒久対応をトラッキングします。

**最終更新日 (Last Updated):** 2025-02-14
