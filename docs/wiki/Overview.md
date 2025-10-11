# DuelPerformanceLogger Wiki / デュエルパフォーマンスロガー Wiki

## Project Snapshot / プロジェクトの概況
- **Purpose / 目的**: Eel ベースのデスクトップアプリとしてデュエル（対戦）結果を記録・分析し、デッキ改善に役立てる。`main.py` が Python/Eel ブリッジを起動し、フロントエンドは `resource/web/` 内の HTML/CSS/JS で構成される。
- **Current Focus / 現在の焦点**: デッキ・シーズン・対戦ログの登録と閲覧、データベースバックアップ、UI 表示モード切り替えなどの基盤機能を提供するためのインフラ整備。
- **Status / 状況**: UI コンポーネントは `resource/web/static/` に集約され、ローカライズ済み文字列リソース、設定・ログ・DB 周りの管理コードが実装済み。`main.py` は Eel ブートストラップと状態スナップショット API (`fetch_snapshot`) を提供する。

## Application Architecture / アプリケーションアーキテクチャ
### UI & State Management / UI と状態管理
- `main.py` は Eel を初期化し、`fetch_snapshot` を通じて最新のアプリ状態 (`AppState`) をフロントエンドへ提供する。
- `function.cmn_app_state.AppState` がアプリ全体の状態を保持し、デッキ/シーズン/対戦ログの一覧や DB ハンドルを統合管理する。
- フロントエンドは `resource/web/static/js/app.js` で DOM を更新し、Eel 経由で Python と通信する。通知は `show_notification` を公開して受け取る。
- 共通スタイルは `resource/web/static/css/` の CSS 変数で統一し、HTML テンプレートは `resource/web/index.html` を起点に構成する。

### Localization Resources / ローカライズリソース
- `function.cmn_resources.get_text` は `resource/theme/json/strings.json` の辞書データからドット区切りキーで文言を取得。`lru_cache` により I/O を最小化。
- 文字列リソースは日本語中心で、UI のメニュー、トースト、ダイアログ文言を網羅する。

### Configuration Management / 設定管理
- `function.cmn_config` が設定 (`resource/theme/config.conf`) の読み取りを担当。`configparser` ベースで既定値 (`DEFAULT_CONFIG`) とマージし、ファイルは読み取り専用運用とする。
- UI モードは DB メタデータ (`db_metadata`) で管理し、設定ファイルにはデータベースの期待スキーマバージョンなどの静的値のみを保持する。

### Database Layer / データベース層
- `DatabaseManager` (`function.cmn_database`) は SQLite3 を操作する高水準ラッパー。自動でフォルダ作成、外部キー ON、`sqlite3.Row` を dict に変換して返却。
- `initialize_database` は冪等なテーブル再作成を提供し、`ensure_database` でメタデータ確認と初期化を自動化。
- テーブル構成（概要）:
  - `decks`: デッキ名・説明の管理。
  - `seasons`: シーズン情報と開催期間。
  - `matches`: 試合結果（先攻/後攻、勝敗、相手デッキ、キーワード、タイムスタンプ）。
  - `db_metadata`: スキーマバージョン等のメタ情報。
- 例外設計として `DatabaseError`, `DuplicateEntryError` を用意し、UI 層から制御しやすいよう区別している。

### Logging / ログ管理
- `function.cmn_logger.log_error` はタイムスタンプ付きログを `resource/log` 配下に日別ファイルとして保存。例外スタックやコンテキスト情報を追記してトラブルシューティングを容易にする。

## Data Flow Overview / データフロー概要
1. ユーザーが UI でデッキやシーズンを登録すると、`DatabaseManager` を通じて SQLite に保存される。
2. 対戦結果入力画面では、設定されたデッキ・カウント情報をもとに試合データを記録し、最新入力内容を画面にフィードバックする構造。
3. 設定画面からは CSV バックアップやデータベース初期化を実行し、結果がトーストやダイアログで通知される。
4. エラー発生時には `log_error` が詳細をログファイルへ記録し、UI ではローカライズされたエラーメッセージを表示する。

## Existing Assets / 既存リソース
- `resource/theme/json/strings.json`: UI 用文言の定義。
- `resource/theme/config.conf`: アプリ設定のデフォルトファイル（INI 形式、読み取り専用）。
- `resource/web/`: HTML/CSS/JS などのフロントエンド資産。
- `resource/db/`: SQLite データベース保存先（`.gitkeep` で空ディレクトリを保持）。
- `resource/log/`: アプリケーションログの出力先。

## Developer Notes / 開発メモ
- Eel ベースのため、開発環境には Python ランタイムと Chromium/Edge WebView2 の利用可能なブラウザが必要。`requirements.txt` で指定した Eel バージョンをインストールする。
- アプリ起動前に `DatabaseManager.ensure_database()` を呼び出しておくと、スキーマ整合性が保証される。
- ログディレクトリやテーマリソースは `Path.resolve()` を使ってルート相対で参照しており、配布パッケージ化する際は相対パス構成を維持すること。

## Next Documentation Steps / ドキュメントの次のステップ
- 画面ごとのスクリーンショットや UI フロー図の追記。
- データベーススキーマの ER 図やマイグレーション履歴の整理。
- テスト戦略（ユニットテスト/統合テスト）のドキュメント化。

**Last Updated:** 2025-11-05
