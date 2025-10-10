# 01. Coding Guidelines / コーディング規約

## 1. General Style
- `function/` 配下は **domain-first** でモジュールを分割する。`cmn_*.py` は共通ヘルパーのみに限定。
- Import 文では `try/except` を禁止。依存欠如はインストール手順側で解決する。
- `Path` を直接連結せず、`function.core.paths` に定義したファクトリを経由する。
- Kivy プロパティは `StringProperty` 等の型を明示し、`ObjectProperty(None)` の濫用を避ける。

## 2. Naming Rules
- 画面クラスは `<Feature>NameScreen` (例: `MatchEntryScreen`) とし、対応する KV は `resource/theme/gui/screens/<Feature>NameScreen.kv`。
- DB アクセサは `fetch_*`, `insert_*`, `update_*`, `delete_*` の 4 系列に揃える。
- DSL (YAML) のキーは `snake_case`、UI に表示する識別子は `Sentence case` を採用。

## 3. Error Handling
- UI 層で捕捉する例外は `function.cmn_error` に定義したカスタム例外へラップ。
- 重大な失敗は `function.cmn_logger.log_error` を経由して `%LOCALAPPDATA%/DuelPerformanceLogger/logs/app.log` に出力。
- CLI/バッチ実行時は `sys.exit(1)` を返す前に必ずエラーログへ書き込む。

## 4. Testing Discipline
- 機能追加時は `tests/` に回帰テストを追加し、**少なくとも 1 つ**のハッピーパスと 1 つの異常系をカバーする。
- UI 変更時は `resource/theme/gui/screens/` 配下の KV を `kivy_parser` で lint し、無効なプロパティを検出する。
- マイグレーション実装時は `tests/migration` にスナップショット DB を追加し、`pytest -k migration` を実行する。

## 5. Documentation
- PR には `docs/wiki/Overview.md` を更新し、変更点のスクリーンショットを添付。
- 規約変更は本ドキュメントを更新し、最新版のハッシュを `docs/VERSION` に記録する。
- 翻訳追加時は英語と日本語を同じ段落に併記し、読み手が選択できるようにする。
