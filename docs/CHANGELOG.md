# Duel Performance Logger - Changelog

All notable changes to this project are documented here. Version numbers follow `DPL.<MAJOR>.<MINOR>.<PATCH>`.

## [0.4.0] - 2025-10-27
### Added
- EN: FFmpeg recording core capable of handling consent-based auto-download, start/stop controls, and screenshots from the desktop capture pipeline.
- JP: 同意後の自動ダウンロードに対応した FFmpeg 録画コアを追加し、デスクトップキャプチャからの開始・停止およびスクリーンショット取得を実装しました。
- EN: Recording profiles for 16:9, 21:9, and 32:9 aspect ratios with integrity checks and a single retry to guard against corruption.
- JP: 16:9・21:9・32:9 の録画プロファイルを追加し、破損検知と 1 回の再試行による保護を組み込みました。

### Changed
- EN: The recording settings UI now persists save directory, bitrate, and FPS values to `app_settings.json`, keeping the desktop client and backend in sync.
- JP: 録画設定 UI が保存先ディレクトリ・ビットレート・FPS を `app_settings.json` に保存し、フロントエンドとバックエンドの設定を同期するようになりました。
- EN: FFmpeg session logs are rotated per session under `/log/recording/`, and migration logs surface the single-line `[DB] current=... target=...` status during startup.
- JP: FFmpeg セッションログを `/log/recording/` 配下でセッション単位に出力し、起動ログに `[DB] current=... target=...` の単一行を表示するよう変更しました。

## [0.3.3] - 2025-10-18
### Added
- EN: Introduced a command line restore tool with `full`/`upsert` modes, dry-run support, and detailed reporting for backup archives.
- JP: バックアップアーカイブを復元する CLI ツールを追加し、`full`/`upsert` モードやドライラン、詳細レポートに対応しました。

### Changed
- EN: Database schema checks now rely on semantic version utilities that run forward migrations while safely skipping downgrades.
- JP: データベーススキーマ判定でセマンティックバージョンユーティリティを用い、順方向マイグレーションのみを実行してダウングレードを安全にスキップするよう変更しました。
- EN: The backup restore workflow processes typed CSV content in a fixed table order under a single transaction and surfaces progress/results in the UI.
- JP: バックアップ復元処理でテーブル順序と型復元を固定し、単一トランザクションで実行して UI に進捗・結果を表示するよう更新しました。

### Fixed
- EN: CSV/ZIP restores now disable foreign key checks during import, verify integrity before commit, and emit failure diagnostics for troubleshooting.
- JP: CSV/ZIP 復元でインポート中に外部キー制約を無効化し、コミット前に整合性検証を行って失敗時の診断情報を出力するよう修正しました。

### Note on Follow-up (v0.3.3-1)
- EN: A follow-up hotfix ensures `current > target` database versions are treated as **no-op** (skip migration entirely) and updates UI/log messages accordingly.
- JP: 追補Hotfixでは、DBが **期待値より上位** の場合は **完全no-op**（マイグレーションを一切実行しない）とし、UI/ログ文言も「上位DB検出：マイグレーション不要」に統一します。

## [0.3.2] - 2025-10-17
### Added
- EN: Users can record per-match memos from entry and edit screens and review them in the match detail view for later reference.
- JP: 対戦情報の登録・編集画面でメモを入力し、詳細画面で確認できる対戦メモ機能を追加しました。
- EN: Added deck and opponent deck analysis dashboards with season filters, rank totals, and combined charts for usage counts and win rates.
- JP: デッキタイプ別・対戦相手デッキタイプ別の分析画面を追加し、シーズンフィルターや使用数/勝率の複合グラフを実装しました。

### Changed
- EN: Seeded protected default keywords, introduced visibility toggles, and refreshed the match entry layout with compact controls and keyword buttons.
- JP: 削除不可の初期キーワードを自動登録し、表示切替ボタンを備えたキーワード管理と対戦登録レイアウトの再構成を行いました。
- EN: Bumped the schema/application version to 0.3.2 and extended migrations to add the match memo column and keyword flags.
- JP: マイグレーションに対戦メモ列とキーワードフラグを追加し、スキーマおよびアプリケーションのバージョンを 0.3.2 に更新しました。

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

