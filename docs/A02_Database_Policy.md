# A02. Database Policy
### データベース運用方針の概要
DPL が組み込む SQLite スキーマの維持、バックアップ、テスト運用を共通化するための基準を示します。主要な概念は英語で保持し、日本語で補足説明を提供します。

## Table of Contents / 目次
- [Schema Governance / スキーマ統制](#schema-governance)
- [Backup Strategy / バックアップ戦略](#backup-strategy)
- [Access Layer Rules / アクセス層ルール](#access-layer-rules)
- [Test Fixtures / テストフィクスチャ](#test-fixtures)
- [Checklist / チェックリスト](#checklist)

## <a id="schema-governance"></a>Schema Governance / スキーマ統制
アプリとマイグレーションチェーンが整合するよう、バージョン管理の前提を定義します。

- Track schema version via the `db_metadata.schema_version` column using SemVer-like integers (e.g., `10203`)。マイグレーションの順序性を担保します。
- When schema changes occur, update `app/function/core/version.py::__version__` and extend the migration chain。アプリバージョンとスキーマを同期させます。
- Keep migrations idempotent by relying on `IF NOT EXISTS` and additive `ALTER TABLE` statements。リプレイ可能な手順に限定します。

## <a id="backup-strategy"></a>Backup Strategy / バックアップ戦略
バックアップの命名や整合性確認を標準化します。

- Store ZIP backups under `%APPDATA%/DuelPerformanceLogger/backups/` with filenames `DPL_{app_version}_{timestamp}.zip`。リストア対象を一意に識別できます。
- Run SQLite `VACUUM` before automated backups to minimise file fragmentation。バックアップ容量を削減します。
- Restore via a temporary directory, execute `PRAGMA integrity_check`, then replace the production DB。破損リスクを低減します。

## <a id="access-layer-rules"></a>Access Layer Rules / アクセス層ルール
データアクセスの API を統一して、スレッド安全性を確保します。

- Manage `DatabaseManager` connections with `contextlib.contextmanager` to guarantee `commit`/`rollback` execution。例外発生時でも状態を戻します。
- Use `?` placeholders for parameter binding instead of string formatting。SQL インジェクションを防ぎます。
- Delegate long-running queries to a thread pool to avoid blocking the UI thread。ユーザー操作のレスポンスを維持します。

## <a id="test-fixtures"></a>Test Fixtures / テストフィクスチャ
スキーマ変更を確実に検証するための最低限の準備です。

- Maintain initialisation scripts in `tests/fixtures/db/seed.sql` and update the history section of this file when diffs appear。文書と実装の差異を防ぎます。
- Execute `pytest --maxfail=1 -k db_migration` in CI at least once per day。移行チェーンの劣化を早期検出します。
- Store schema diagrams in `docs/resource/schema.drawio` and export PNGs alongside updates。ビジュアル資料の同期を保ちます。

## <a id="checklist"></a>Checklist / チェックリスト
変更前に次を満たしているか確認してください。

- [ ] スキーマバージョンが `db_metadata` とコードの両方で一致している。
- [ ] バックアップ ZIP に最新バージョン番号が含まれている。
- [ ] マイグレーションテストが CI で実行されている。

**Last Updated:** 2025-10-12
