# 02. Database Policy / データベース運用方針

## 1. Schema Governance
- スキーマバージョンは `db_metadata` テーブルの `schema_version` カラムで管理し、SemVer 互換の整数 3 桁 (例: 10203)。
- 変更時は `app/function/core/version.py` の `__version__` を更新し、マイグレーションチェーンに追記する。
- マイグレーションは冪等性を重視し、`IF NOT EXISTS` / `ALTER TABLE ADD COLUMN` のみを利用する。

## 2. Backup Strategy
- `%APPDATA%/DuelPerformanceLogger/backups/` に ZIP バックアップを保存。ファイル名は `DPL_{app_version}_{timestamp}.zip`。
- 自動バックアップ前に SQLite の `VACUUM` を実施し、ファイル断片化を防止。
- 復元時は一時ディレクトリへ展開後、整合性チェック (`PRAGMA integrity_check`) を実行してから本番 DB と置換。

## 3. Access Layer Rules
- `DatabaseManager` のコネクションは `contextlib.contextmanager` で扱い、`commit` / `rollback` を確実に発火。
- クエリ文字列は `?` プレースホルダでパラメータバインディングを徹底し、フォーマット文字列は使用しない。
- 長時間実行クエリはスレッドプールへ委譲し、UI スレッドでブロックしない。

## 4. Test Fixtures
- `tests/fixtures/db/seed.sql` に初期化スクリプトを配置し、差分が出た際は `docs/02_database_policy.md` の履歴を更新。
- マイグレーションテストは `pytest --maxfail=1 -k db_migration` を最低 1 日 1 回 CI で実行。
- スキーマ図は `docs/resource/schema.drawio` に保存し、更新時は PNG もエクスポートする。
