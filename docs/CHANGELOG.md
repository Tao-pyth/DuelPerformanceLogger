# Duel Performance Logger - Changelog

All notable changes to this project are documented here. Version numbers follow `DPL.<MAJOR>.<MINOR>.<PATCH>`.

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

