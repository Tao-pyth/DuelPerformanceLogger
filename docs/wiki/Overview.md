# DuelPerformanceLogger Wiki / デュエルパフォーマンスロガー Wiki

## Project Snapshot / プロジェクトの概況
- **Purpose / 目的**: KivyMD 製のデスクトップアプリとしてデュエル（対戦）結果を記録・分析し、デッキ改善に役立てる。`main.py` の UI ロジックと `function` パッケージのユーティリティ群で構成される。
- **Current Focus / 現在の焦点**: デッキ・シーズン・対戦ログの登録と閲覧、データベースバックアップ、UI 表示モード切り替えなどの基盤機能を提供するためのインフラ整備。
- **Status / 状況**: UI 部品の共通化（ヘッダー生成など）、ローカライズ済み文字列リソース、設定・ログ・DB 周りの管理コードが実装済み。画面遷移や入力フォームのレイアウトは `main.py` に集約されている。

## Application Architecture / アプリケーションアーキテクチャ
### UI & State Management / UI と状態管理
- `main.py` は KivyMD アプリ本体であり、画面管理 (`MDScreenManager`) や各種レイアウト、トースト表示、ダイアログ制御を担う。
- `_FallbackAppState` により、`MDApp` が起動していない状態でも設定やデータベース接続などの属性へアクセス可能。テストやスクリプト実行時の安全装置として機能する。
- `build_header` のような UI ヘルパーで、画面上部の共通ヘッダー（タイトル、戻る・トップボタン）を再利用可能にしている。

### Localization Resources / ローカライズリソース
- `function.resources.get_text` は `resource/theme/json/strings.json` の辞書データからドット区切りキーで文言を取得。`lru_cache` により I/O を最小化。
- 文字列リソースは日本語中心で、UI のメニュー、トースト、ダイアログ文言を網羅する。

### Configuration Management / 設定管理
- `function.config` が設定 (`resource/theme/config.json`) の読み書きを担当。`DEFAULT_CONFIG` を基点に JSON ファイルをマージし、欠損や破損時には自動復旧する。
- UI モード（通常/配信向け）やデータベースの期待スキーマバージョン、バックアップ情報を保持。

### Database Layer / データベース層
- `DatabaseManager` (`function.database`) は SQLite3 を操作する高水準ラッパー。自動でフォルダ作成、外部キー ON、`sqlite3.Row` を dict に変換して返却。
- `initialize_database` は冪等なテーブル再作成を提供し、`ensure_database` でメタデータ確認と初期化を自動化。
- テーブル構成（概要）:
  - `decks`: デッキ名・説明の管理。
  - `seasons`: シーズン情報と開催期間。
  - `matches`: 試合結果（先攻/後攻、勝敗、相手デッキ、キーワード、タイムスタンプ）。
  - `db_metadata`: スキーマバージョン等のメタ情報。
- 例外設計として `DatabaseError`, `DuplicateEntryError` を用意し、UI 層から制御しやすいよう区別している。

### Logging / ログ管理
- `function.logger.log_error` はタイムスタンプ付きログを `resource/log` 配下に日別ファイルとして保存。例外スタックやコンテキスト情報を追記してトラブルシューティングを容易にする。

## Data Flow Overview / データフロー概要
1. ユーザーが UI でデッキやシーズンを登録すると、`DatabaseManager` を通じて SQLite に保存される。
2. 対戦結果入力画面では、設定されたデッキ・カウント情報をもとに試合データを記録し、最新入力内容を画面にフィードバックする構造。
3. 設定画面からは CSV バックアップやデータベース初期化を実行し、結果がトーストやダイアログで通知される。
4. エラー発生時には `log_error` が詳細をログファイルへ記録し、UI ではローカライズされたエラーメッセージを表示する。

## Existing Assets / 既存リソース
- `resource/theme/json/strings.json`: UI 用文言の定義。
- `resource/theme/config.json`: アプリ設定のデフォルトファイル。
- `resource/db/`: SQLite データベース保存先（`.gitkeep` で空ディレクトリを保持）。
- `resource/log/`: アプリケーションログの出力先。
- `resource/theme/font/`: 日本語フォント配置想定ディレクトリ（`main.py` で `mgenplus-1c-regular.ttf` を参照）。

## Developer Notes / 開発メモ
- KivyMD ベースのため、開発環境には Kivy/KivyMD と依存ライブラリのセットアップが必要。
- アプリ起動前に `DatabaseManager.ensure_database()` を呼び出しておくと、スキーマ整合性が保証される。
- ログディレクトリやテーマリソースは `Path.resolve()` を使ってルート相対で参照しており、配布パッケージ化する際は相対パス構成を維持すること。

## Next Documentation Steps / ドキュメントの次のステップ
- 画面ごとのスクリーンショットや UI フロー図の追記。
- データベーススキーマの ER 図やマイグレーション履歴の整理。
- テスト戦略（ユニットテスト/統合テスト）のドキュメント化。
