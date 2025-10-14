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

- Track schema version via the `db_metadata.schema_version` column using semantic-version strings (e.g., `0.1.1`)。マイグレーションの順序性を担保します。
- When schema changes occur, update `app/function/core/version.py::__version__` and extend the migration chain。アプリバージョンとスキーマを同期させます。
- Keep migrations idempotent by relying on `IF NOT EXISTS` and additive `ALTER TABLE` statements。リプレイ可能な手順に限定します。
- Prefer referencing related entities via stable numeric identifiers (e.g., `deck_id`) and limit string columns (e.g., `deck_name`) to presentation concerns。ID 参照を第一選択とし、文字列参照は表示用途に限定します。
- Document foreign-key intent in both migrations and table definitions; do not rely on implicit constraints。参照整合性の意図をマイグレーションとテーブル定義の双方で明示します。

## Referential Integrity / 参照整合
SQLite が標準で外部キー制約を無効化している点を踏まえ、アプリケーションとスキーマの双方で整合性を維持します。

- Enable `PRAGMA foreign_keys=ON` on every connection entry point (`DatabaseManager.connect`) and assert failures during CI。接続単位で FK が有効なことを前提にします。
- Model lookups must resolve human-readable keys (`deck_name`, `keyword.identifier`) to numeric IDs before write operations。書き込み前に ID 化し、`NULL` を許容しません。
- Prefer `ON DELETE RESTRICT` / `ON UPDATE CASCADE` semantics to prevent orphaned records while allowing metadata 修正。孤児レコードを防ぎつつ、名称更新を許容します。
- Provide data-fix scripts when migrating from legacy name-based references to ID-based references。文字列参照からの移行時はデータ修復スクリプトを同梱します。

## Migration Procedure / マイグレーション基本則
破壊的更新を避けるための標準手順とロールバック方法を定義します。

1. Create a new table with the desired schema (`*_new`) while `PRAGMA foreign_keys=OFF` to avoid intermediate failures。新テーブルは `*_new` サフィックスで作成します。
2. Copy data into the new table, resolving foreign keys inside the `INSERT ... SELECT` statement and aborting when 解決できないレコードが存在します。コピー後は検証を実施します。
3. Drop the legacy table and rename the new table once validation passes。成功時にのみ旧テーブルを廃棄します。
4. Wrap the above in a single transaction and provide the inverse steps (rename back + insert) in the migration notes for rollback readiness。単一トランザクションで実施し、ロールバック手順も文書化します。
5. Update the migration index (`resource/db/migrations/`) sequentially and bump `db_metadata.schema_version` via application bootstrap。マイグレーションチェーンとメタデータを同期させます。

## Date & Time Handling / 日付・時刻の扱い
ログと統計に整合した時間軸を提供するための規約です。

- Store canonical timestamps as UTC epoch seconds in `INTEGER` columns (`created_at`, `updated_at`)。基準タイムゾーンは UTC です。
- When string representations are required (e.g., legacy exports), serialise using ISO8601 UTC (`%Y-%m-%dT%H:%M:%SZ`) and note the timezone。文字列フィールドを利用する場合は UTC を明記します。
- Avoid storing local time offsets in the database; convert to local time only at the presentation layer。ローカル時刻への変換は UI レイヤーで行います。
- Include timezone awareness in migration scripts and fixtures to prevent accidental localtime inserts during テスト。テストデータでも UTC 変換を徹底します。

## Schema Overview (v0.1.1) / スキーマ概要（v0.1.1）
データベース初期構築およびマイグレーション後に保証されるテーブル構成を以下に示します。`schema_version="0.1.1"` は
アプリのセマンティックバージョン `0.1.1` を保持します。

| Table | 主用途 / Purpose | 主なカラム | 補足 | 初期値 |
|-------|------------------|------------|------|--------|
| `decks` | デッキ情報登録画面 | `name` (UNIQUE), `description` (TEXT), `usage_count` (INTEGER) | `usage_count` は登録済み対戦ログから再計算され、既定値は 0。| `usage_count=0` |
| `opponent_decks` | 対戦相手デッキ情報登録画面 | `name` (UNIQUE), `usage_count` (INTEGER) | プルダウン表示用。対戦登録時に自動追加・加算。| `usage_count=0` |
| `keywords` | 対戦キーワード管理 | `identifier` (UNIQUE), `name` (UNIQUE), `description` (TEXT), `usage_count` (INTEGER), `created_at` (UTC epoch) | `identifier` は内部用 UUID。`usage_count` は対戦データ登録時に集計。| `usage_count=0` |
| `matches` | 対戦情報登録 | `match_no`, `deck_name`, `turn` (先攻=True/後攻=False), `opponent_deck`, `keywords` (JSON), `result` (-1/0/1), `youtube_url` (TEXT), `favorite` (INTEGER), `created_at` (UTC epoch) | `keywords` は JSON 配列。`youtube_url` は長めの URL (最大 2048 文字) を許容。`favorite` は 1/0 のフラグ。| `created_at=STRFTIME('%s','now')` |
| `seasons` | シーズン管理（将来拡張） | `name`, `description`, `start_date`, `start_time`, `end_date`, `end_time` | 空でも動作。 | `description=''` |
| `db_metadata` | 設定情報 | `schema_version`, `ui_mode`, `last_backup` | `ui_mode` は `normal` を既定値とし、マイグレーション完了後に `schema_version="0.1.1"` を記録。| `ui_mode='normal'` |

`DatabaseManager.ensure_database()` は起動時に以下を自動実施します。

1. 必須テーブルとカラム（`decks.usage_count`、`opponent_decks.usage_count` など）の存在チェック。
2. 欠落時の `ALTER TABLE` / `CREATE TABLE` 実行。
3. `matches` を基準に `usage_count` を再計算し整合性を確保。
4. メタデータへ最新スキーマバージョン (`"0.1.1"`) を保存。


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
