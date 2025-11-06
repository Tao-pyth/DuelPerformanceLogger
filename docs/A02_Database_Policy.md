# A02. Database Policy

This policy standardizes how Duel Performance Logger manages its embedded SQLite schema, including governance, backups, access patterns, and testing.
このポリシーは、Duel Performance Logger が組み込み SQLite スキーマを管理する際の統制・バックアップ・アクセスパターン・テスト運用を標準化します。

## Table of Contents / 目次

The sections below describe schema governance, referential integrity, migration procedures, time handling, backups, access-layer conventions, fixtures, and review checks.
以下では、スキーマ統制・参照整合性・マイグレーション手順・時刻の扱い・バックアップ・アクセス層規約・フィクスチャ・レビュー確認事項を説明します。

- Schema Governance
  - スキーマ統制
- Referential Integrity
  - 参照整合
- Migration Procedure
  - マイグレーション基本則
- Date & Time Handling
  - 日付・時刻の扱い
- Schema Overview (v0.4.1)
  - スキーマ概要（v0.4.1）
- Backup Strategy
  - バックアップ戦略
- Access Layer Rules
  - アクセス層ルール
- Test Fixtures
  - テストフィクスチャ
- Checklist
  - チェックリスト

## <a id="schema-governance"></a>Schema Governance / スキーマ統制

Define how application code and migration chains stay aligned across releases.
アプリケーションコードとマイグレーションチェーンを各リリースで整合させる方法を定義します。

- Track the schema with semantic-version strings in `db_metadata.schema_version` (for example, `0.1.1`) to preserve migration order.
  - マイグレーション順序を保持するために、`db_metadata.schema_version` でセマンティックバージョン（例: `0.1.1`）を管理します。
- Update `app/function/core/version.py::__version__` and extend the migration chain whenever the schema changes so the app and database stay in sync.
  - スキーマ変更時には `app/function/core/version.py::__version__` を更新し、マイグレーションチェーンを拡張してアプリとデータベースの同期を保ちます。
- Keep migrations idempotent by using `IF NOT EXISTS` clauses and additive `ALTER TABLE` statements so that replays remain safe.
  - マイグレーションを安全に再実行できるように、`IF NOT EXISTS` 句や加算的な `ALTER TABLE` を用いて冪等性を確保します。
- Reference related entities through stable numeric identifiers (such as `deck_id`) and reserve string columns (such as `deck_name`) for presentation.
  - 関連エンティティは `deck_id` などの安定した数値 ID で参照し、`deck_name` などの文字列カラムは表示用途に限定します。
- Document foreign-key intentions in migrations and table definitions rather than relying on implicit behavior.
  - 参照整合性の意図は暗黙にせず、マイグレーションとテーブル定義の双方に明示します。

## Referential Integrity / 参照整合

Maintain referential integrity explicitly because SQLite disables foreign keys by default.
SQLite が外部キーを既定で無効にしているため、参照整合性を明示的に維持します。

- Enable `PRAGMA foreign_keys=ON` for every connection through `DatabaseManager.connect`, and assert this behavior during CI.
  - すべての接続で `DatabaseManager.connect` を通じて `PRAGMA foreign_keys=ON` を有効化し、CI で動作を検証します。
- Resolve human-readable keys (such as `deck_name` or `keyword.identifier`) to numeric IDs before performing writes, disallowing `NULL` placeholders.
  - 書き込み前に `deck_name` や `keyword.identifier` などの可読キーを数値 ID に解決し、`NULL` のままにしないようにします。
- Prefer `ON DELETE RESTRICT` and `ON UPDATE CASCADE` semantics to prevent orphaned records while permitting metadata updates.
  - 孤児レコードを防ぎつつメタデータの更新を許容するため、`ON DELETE RESTRICT` と `ON UPDATE CASCADE` の動作を優先します。
- Ship data-fix scripts when migrating from legacy name-based references to ID-based references so historical data remains usable.
  - 旧来の名称参照から ID 参照へ移行する際にはデータ修復スクリプトを同梱し、過去データの利用を保証します。

## Migration Procedure / マイグレーション基本則

Execute schema changes safely and provide a clear rollback path.
スキーマ変更を安全に実行し、明確なロールバック手順を提供します。

1. Create the new table (`*_new`) with `PRAGMA foreign_keys=OFF` to avoid intermediate constraint failures.
   1. 中間段階で制約違反が発生しないように、`PRAGMA foreign_keys=OFF` の状態で `*_new` テーブルを作成します。
2. Copy data via `INSERT ... SELECT`, resolving foreign keys inline and aborting if records cannot be matched, then validate the results.
   2. `INSERT ... SELECT` でデータをコピーし、外部キーをその場で解決して対応できないレコードがあれば処理を中止し、結果を検証します。
3. Drop the legacy table and rename the new table only after validation passes successfully.
   3. 検証が成功した場合に限り、旧テーブルを削除して新テーブルにリネームします。
4. Wrap the migration in a single transaction and document the inverse sequence (rename back and reinsert) for rollback readiness.
   4. マイグレーション全体を単一トランザクションで実施し、逆順手順（リネーム戻しと再挿入）を文書化してロールバックに備えます。
5. Update the migration index in `resource/db/migrations/` sequentially and bump `db_metadata.schema_version` during application bootstrap.
   5. `resource/db/migrations/` のインデックスを順番どおりに更新し、アプリ起動処理で `db_metadata.schema_version` を更新します。

## Date & Time Handling / 日付・時刻の扱い

Offer a consistent timeline for logs and analytics by standardizing timestamp behavior.
ログと分析で一貫した時間軸を提供するために、タイムスタンプの扱いを標準化します。

- Store canonical timestamps as UTC epoch seconds in `INTEGER` columns such as `created_at` and `updated_at`.
  - `created_at` や `updated_at` などの `INTEGER` カラムには UTC エポック秒で基準タイムスタンプを保存します。
- When string representations are required, serialise values as ISO 8601 UTC (`%Y-%m-%dT%H:%M:%SZ`) and document the timezone.
  - 文字列表現が必要な場合は ISO 8601 UTC (`%Y-%m-%dT%H:%M:%SZ`) でシリアライズし、タイムゾーンを明記します。
- Avoid persisting local time offsets in the database and convert to local time only at the presentation layer.
  - データベースにはローカル時刻のオフセットを保存せず、ローカル時刻への変換は表示レイヤーで行います。
- Include timezone awareness in migrations and fixtures to prevent accidental local-time inserts during testing.
  - テストで誤ってローカル時刻を挿入しないように、マイグレーションやフィクスチャでもタイムゾーン情報を考慮します。

## Schema Overview (v0.4.1) / スキーマ概要（v0.4.1）

The following tables are guaranteed after initial setup or migrations when `schema_version="0.4.1"`, which matches application version `0.4.1`.
初期セットアップやマイグレーション完了後に保証されるテーブル構成を以下に示します。`schema_version="0.4.1"` はアプリバージョン `0.4.1` と一致します。

| Table | Purpose | Key Columns | Notes | Defaults |
|-------|---------|-------------|-------|----------|
| `decks` | Deck registration | `name` (UNIQUE), `description` (TEXT), `usage_count` (INTEGER) | `usage_count` recalculates from match logs with default 0. | `usage_count=0` |
| `opponent_decks` | Opponent deck catalog | `name` (UNIQUE), `usage_count` (INTEGER) | Auto-added and incremented when matches are logged. | `usage_count=0` |
| `keywords` | Keyword management | `identifier` (UNIQUE), `name` (UNIQUE), `description` (TEXT), `usage_count` (INTEGER), `created_at` (UTC epoch) | `identifier` uses UUID; `usage_count` aggregates from match data. | `usage_count=0` |
| `matches` | Match records | `match_no`, `deck_name`, `turn` (先攻=True/後攻=False), `opponent_deck`, `keywords` (JSON), `result` (-1/0/1), `youtube_flag` (INTEGER), `youtube_url` (TEXT), `youtube_video_id` (TEXT), `youtube_checked_at` (UTC epoch), `favorite` (INTEGER), `created_at` (UTC epoch) | `keywords` stores a JSON array; `youtube_flag` encodes `YouTubeSyncFlag`; `youtube_checked_at` saves the last update time; `youtube_url` allows up to 2048 characters. | `created_at=STRFTIME('%s','now')` |
| `seasons` | Future season support | `name`, `description`, `start_date`, `start_time`, `end_date`, `end_time` | The table may remain empty until features ship. | `description=''` |
| `db_metadata` | Configuration metadata | `schema_version`, `ui_mode`, `last_backup` | `ui_mode` defaults to `normal`; migrations record `schema_version="0.4.1"`. | `ui_mode='normal'` |

`DatabaseManager.ensure_database()` performs the following tasks during startup.
`DatabaseManager.ensure_database()` は起動時に以下の処理を実行します。

1. Verify that required tables and columns (including `decks.usage_count` and `opponent_decks.usage_count`) exist.
   1. `decks.usage_count` や `opponent_decks.usage_count` などの必須テーブルとカラムの存在を確認します。
2. Run `ALTER TABLE` or `CREATE TABLE` statements when objects are missing.
   2. 対象が欠落している場合は `ALTER TABLE` または `CREATE TABLE` を実行します。
3. Recalculate `usage_count` values from `matches` to maintain consistency.
   3. 整合性を保つために `matches` を基準に `usage_count` を再計算します。
4. Persist the latest schema version (`"0.4.1"`) to metadata.
   4. 最新スキーマバージョン (`"0.4.1"`) をメタデータに保存します。

## <a id="backup-strategy"></a>Backup Strategy / バックアップ戦略

Standardize backup naming and validation to simplify restoration.
バックアップの命名と検証を標準化して、リストア作業を容易にします。

- Store ZIP backups in `%APPDATA%/DuelPerformanceLogger/backups/` with filenames `DPL_{app_version}_{timestamp}.zip` for unique identification.
  - ZIP バックアップは `%APPDATA%/DuelPerformanceLogger/backups/` に `DPL_{app_version}_{timestamp}.zip` 形式で保存し、一意に識別します。
- Run SQLite `VACUUM` before automated backups to reduce fragmentation and file size.
  - 自動バックアップ前に SQLite の `VACUUM` を実行し、断片化とファイルサイズを抑制します。
- Restore through a temporary directory, execute `PRAGMA integrity_check`, and replace the production database only after verification.
  - 一時ディレクトリで復元し、`PRAGMA integrity_check` を実行して検証後に本番データベースを置き換えます。

## <a id="access-layer-rules"></a>Access Layer Rules / アクセス層ルール

Unify database access APIs and maintain thread safety.
データアクセス API を統一してスレッド安全性を確保します。

- Manage connections with `contextlib.contextmanager` helpers in `DatabaseManager` to guarantee `commit` or `rollback` execution.
  - `DatabaseManager` の `contextlib.contextmanager` ヘルパーで接続を管理し、`commit` または `rollback` が必ず実行されるようにします。
- Use `?` placeholders for SQL parameter binding instead of string formatting to prevent injection risks.
  - SQL パラメータのバインディングには文字列フォーマットではなく `?` プレースホルダーを使用し、インジェクションを防止します。
- Delegate long-running queries to a thread pool so the UI thread remains responsive.
  - 長時間クエリはスレッドプールに委譲し、UI スレッドの応答性を維持します。

## <a id="test-fixtures"></a>Test Fixtures / テストフィクスチャ

Prepare fixtures that validate schema changes consistently across environments.
環境を問わずスキーマ変更を検証できるようフィクスチャを整備します。

- Maintain initialization scripts in `tests/fixtures/db/seed.sql` and update this document when differences arise to prevent drift.
  - 初期化スクリプトを `tests/fixtures/db/seed.sql` で管理し、差分が生じた際には本ドキュメントを更新して乖離を防ぎます。
- Execute `pytest --maxfail=1 -k db_migration` in CI at least once per day to detect migration regressions early.
  - マイグレーションの劣化を早期発見するため、CI で少なくとも 1 日 1 回 `pytest --maxfail=1 -k db_migration` を実行します。
- Store schema diagrams in `docs/resource/schema.drawio` and export updated PNGs alongside documentation changes.
  - スキーマ図は `docs/resource/schema.drawio` で管理し、更新時には PNG を書き出してドキュメントと同時に更新します。

## <a id="checklist"></a>Checklist / チェックリスト

Confirm the following before shipping database changes.
データベース変更をリリースする前に次を確認してください。

- [ ] `db_metadata` and application code report the same schema version.
  - [ ] `db_metadata` とアプリコードでスキーマバージョンが一致している。
- [ ] Backup ZIP files include the latest version number in their filenames.
  - [ ] バックアップ ZIP のファイル名に最新バージョン番号が含まれている。
- [ ] Migration tests run in CI without failures.
  - [ ] マイグレーションテストが CI で失敗せずに実行されている。

**Last Updated:** 2025-10-19
**最終更新日:** 2025-10-19
