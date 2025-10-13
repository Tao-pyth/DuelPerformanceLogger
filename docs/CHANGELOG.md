# Duel Performance Logger - Changelog

All notable changes to this project are documented here. Version numbers follow `DPL.<MAJOR>.<MINOR>.<PATCH>`.

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

