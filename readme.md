# DuelPerformanceLogger

DuelPerformanceLogger は、デスクトップ向けのトレーディングカード対戦記録アプリです。Python バックエンドと Eel を介したフロントエンドを統合し、対戦結果の収集、デッキ管理、バックアップ/リストア、YouTube 連携といった日常運用を 1 つのワークフローにまとめます。

## 主な機能
- **データ管理**: `DatabaseManager` を中心に、デッキ・シーズン・対戦ログ・キーワード・アップロードジョブの CRUD、履歴管理、マイグレーション、バックアップ/リストアを提供します。
- **録画ユーティリティ**: `FFmpegRecorder` により、FFmpeg を呼び出して録画・スクリーンショットを取得。リトライ制御やファイル命名、ログ記録を一元管理します。
- **YouTube 連携**: YouTube Data API へのアップロード、OAuth トークンの暗号化保存、資格情報チェック、ブラウザフローをサポートします。
- **バックアップ API**: Eel から呼び出せるバックアップ生成/復元 API とデータベース初期化 API を備え、UI から即時にスナップショットを返せます。
- **CLI ツール**: `cli/restore_from_backup.py` でバックアップ ZIP のフルリストア/マージ/ドライランを実施可能です。

## アーキテクチャ
- `app/`: Python/Eel の調停コード。`DuelPerformanceService` が SQLite とアプリ状態を管理し、UI からの `@eel.expose` API を通じて操作されます。
- `resource/`: フロントエンド資産や設定ファイルなどのバンドルリソース。
- `db/`: `migrations/` にスキーマ進化を格納。SQLite データベースとそのマイグレーションロジックを提供します。
- `docs/`: 運用ポリシーや開発規約など補助ドキュメント。
- `tests/`: `pytest` ベースのテスト。DB マイグレーションや録画ユーティリティ、YouTube 連携を検証します。

`paths.py` でプロジェクトルートやユーザーデータディレクトリ (Windows の `%APPDATA%/DuelPerformanceLogger` 等) を抽象化し、各モジュールが共有します。PyInstaller one-folder 配布時の構成や依存境界も整理されています。

## データモデル
SQLite の初期スキーマは以下を含みます。
- デッキ、シーズン、キーワード、対戦ログ、アップロードジョブの各テーブル
- 外部キー制約や CHECK 制約
- YouTube 連携用のカラム群

設定値は `config.conf` を読み込み既定値とマージする仕組みで、データベース期待バージョンや YouTube 用テンプレートが含まれます。

## 環境構築
1. Python 3.10 以上を用意します。
2. 仮想環境を作成しアクティベートします。
3. 依存関係をインストールします。

```bash
pip install -r requirements.txt
```

開発時には `requirements-dev.txt` の利用も検討してください (`pip install -r requirements-dev.txt`)。

## 実行方法
UI を起動するには以下を使用します。

```bash
python -m app.main
```

環境変数で挙動を調整できます。
- `DPL_EEL_MODE`: ブラウザモードの切り替え。
- `DPL_NO_UI`: ノンブロッキング起動の制御。

起動フローはサービス初期化 → `eel.init` → `eel.start` の順で進みます。

## CLI: バックアップのリストア
`cli/restore_from_backup.py` では ZIP 形式のバックアップを以下のモードで処理できます。

```bash
python -m cli.restore_from_backup <path-to-zip> --mode {full|upsert} [--dry-run]
```

- `--mode full`: 既存データを全て置き換え。
- `--mode upsert`: 既存データを保持しつつ差分をマージ。
- `--dry-run`: 実際の書き込みを行わず検証のみ。

## テスト
`pytest` が想定テストランナーです。

```bash
pytest
```

YouTube 関連のテストは `googleapiclient` が利用できない環境では `importorskip` によりスキップされます。

## ユーザーデータとバックアップ
設定・データベース・ログ・YouTube 資産は、`paths` ヘルパー経由でユーザーデータディレクトリ (例: `%APPDATA%/DuelPerformanceLogger`) に保存されます。バックアップ対象や保存先を README から確認できるようにしてください。PyInstaller one-folder 配布時も同じレイアウトが適用されます。

## 追加ドキュメント
詳細な開発ポリシーや命名規則は `docs/` にあります。必要に応じて参照してください。
