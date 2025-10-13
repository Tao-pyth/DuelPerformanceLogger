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

- Track schema version via the `db_metadata.schema_version` column using semantic-version strings (e.g., `0.1.0`)。マイグレーションの順序性を担保します。
- When schema changes occur, update `app/function/core/version.py::__version__` and extend the migration chain。アプリバージョンとスキーマを同期させます。
- Keep migrations idempotent by relying on `IF NOT EXISTS` and additive `ALTER TABLE` statements。リプレイ可能な手順に限定します。

## Schema Overview (v0.1.0) / スキーマ概要（v0.1.0）
データベース初期構築およびマイグレーション後に保証されるテーブル構成を以下に示します。`schema_version="0.1.0"` は
アプリのセマンティックバージョン `0.1.0` を保持します。

| Table | 主用途 / Purpose | 主なカラム | 補足 | 初期値 |
|-------|------------------|------------|------|--------|
| `decks` | デッキ情報登録画面 | `name` (UNIQUE), `description` (TEXT), `usage_count` (INTEGER) | `usage_count` は登録済み対戦ログから再計算され、既定値は 0。| `usage_count=0` |
| `opponent_decks` | 対戦相手デッキ情報登録画面 | `name` (UNIQUE), `usage_count` (INTEGER) | プルダウン表示用。対戦登録時に自動追加・加算。| `usage_count=0` |
| `matches` | 対戦情報登録 | `match_no`, `deck_name`, `turn` (先攻=True/後攻=False), `opponent_deck`, `keywords` (JSON), `result` (-1/0/1), `created_at` (UTC epoch) | 直前に選択したデッキは `deck_name` と `match_no` で追跡。| `created_at=STRFTIME('%s','now')` |
| `seasons` | シーズン管理（将来拡張） | `name`, `description`, `start_date`, `start_time`, `end_date`, `end_time` | 空でも動作。 | `description=''` |
| `db_metadata` | 設定情報 | `schema_version`, `ui_mode`, `last_backup` | `ui_mode` は `normal` を既定値とし、マイグレーション完了後に `schema_version="0.1.0"` を記録。| `ui_mode='normal'` |

`DatabaseManager.ensure_database()` は起動時に以下を自動実施します。

1. 必須テーブルとカラム（`decks.usage_count`、`opponent_decks.usage_count` など）の存在チェック。
2. 欠落時の `ALTER TABLE` / `CREATE TABLE` 実行。
3. `matches` を基準に `usage_count` を再計算し整合性を確保。
4. メタデータへ最新スキーマバージョン (`"0.1.0"`) を保存。


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
