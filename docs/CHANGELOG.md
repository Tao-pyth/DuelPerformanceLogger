# Duel Performance Logger - Changelog

All notable changes to this project are documented here. Version numbers follow `DPL.<MAJOR>.<MINOR>.<PATCH>`.

## [0.3.1] - 2025-10-16
### Added
- EN: Seasons can now be registered with a "Rank Statistics" flag so only competitive data is tracked for analytics.
- JP: シーズン登録時に「ランク統計対象」フラグを設定できるようにし、ランク戦データのみを分析対象として扱えるようにしました。

### Changed
- EN: The dashboard's recent match list now filters to seasons marked for rank statistics, and the schema migration adds the supporting column.
- JP: ダッシュボードの直近対戦記録はランク統計対象シーズンの対戦だけを表示し、スキーママイグレーションで対応カラムを追加しました。

## [0.3.0] - 2025-10-15
### Added
- EN: Introduced semantic version utilities and a chained migration scaffold to coordinate schema upgrades step by step.
- JP: セマンティックバージョンのユーティリティと逐次マイグレーションの枠組みを追加し、スキーマ更新を段階的に管理できるようにしました。

### Changed
- EN: Database initialization now verifies SQLite integrity, backs up corrupted files, and rebuilds the schema before applying defaults.
- JP: データベース初期化時に SQLite の整合性を検証し、破損時はバックアップ退避後にスキーマを再構築してから既定値を適用するようにしました。
- EN: Schema migrations traverse the semantic chain to reach and record the new `v0.3.0` target, and the application version strings now reflect `0.3.0`.
- JP: マイグレーションがセマンティックチェーンを辿って新しい `v0.3.0` に到達・記録し、アプリケーションの表示バージョンも `0.3.0` に更新しました。

### Fixed
- EN: Fetching matches now retries once after running migrations when the `matches` table is missing, avoiding crashes during upgrades.
- JP: アップグレード中に `matches` テーブルが見つからない場合でもマイグレーション後に 1 度再試行し、取得処理が落ちないようにしました。

## [0.2.1] - 2025-10-14
### Changed
- EN: Enforced a database preflight during service bootstrap so migrations finish before the initial state is built.
- JP: サービス起動時にプリフライトを必ず実行し、初期状態構築前にマイグレーション完了を保証するようにしました。

### Fixed
- EN: Added a self-healing retry when fetching matches detects a missing table by running migrations and reissuing the query once.
- JP: matches テーブル欠如を検知した際にマイグレーションを行い 1 回だけ再実行する自己修復リトライを追加しました。

## [0.2.0] - 2025-10-13
### Added
- EN: Introduced season management across the database, API, and UI including a dedicated registration view and season selection during match entry.
- JP: シーズン登録画面を新設し、データベースおよび UI/API 全体でシーズン情報を扱えるようにしました。
- EN: Added manual CSV-Zip backup export, archive import/restore, and database reset controls in the settings view.
- JP: 設定画面に手動 CSV-Zip バックアップ出力、アーカイブからのインポート復元、データベース初期化操作を追加しました。

### Changed
- EN: Enhanced the match entry layout (larger clock with date line, wider opponent/keyword fields, slimmer keyword selector) and enabled free-text opponent deck entry with automatic registration.
- JP: 対戦登録画面で時計表示の拡大・日付追加、項目幅やキーワード選択の調整を行い、対戦相手デッキの自由入力登録を可能にしました。
- EN: Match listings now support inline deletion while keeping match numbers stable and recalculating usage counts for decks, opponent decks, and keywords.
- JP: 対戦情報一覧から削除操作が可能になり、対戦番号を維持したままデッキ・相手デッキ・キーワードの使用回数が再計算されます。

## [0.1.1] - 2025-10-12
### Added
- Keyword management (create/delete, usage counts) with dedicated screens and navigation.
- Match listing, detail, and edit flows including YouTube URL storage and favorite flag editing.
- Multi-select keyword input during match registration and keyword aware summaries.
- Database schema support for keywords table plus `youtube_url` and `favorite` columns on matches.
- UI actions for deleting registered decks and opponent decks directly from their lists.
- Placeholder statistics screen accessible from the top menu.

### Changed
- Application version bumped to `0.1.1` with configuration defaults aligned to the new schema.

### Notes
- Database migrations automatically add the new tables/columns and backfill metadata to schema `0.1.1`.

