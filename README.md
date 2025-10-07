# DuelPerformanceLogger

## Approach & Policy / 対応方針
- **Consolidate a reliable core before feature expansion. / 新機能の拡張前に信頼性の高い基盤を固める。**
  - Stabilize the KivyMD UI flows defined in `main.py`, ensuring reusable components (headers, dialogs, menus) work consistently across screens.
  - `main.py` に定義された KivyMD の画面遷移と共通部品（ヘッダー、ダイアログ、メニュー）がすべての画面で一貫して動作するよう整備する。
- **Protect data integrity with strict database routines. / 厳密なデータベース運用でデータ整合性を守る。**
  - Keep `DatabaseManager` as the single entry point for persistence, leveraging schema version checks and defensive initialization.
  - スキーマバージョンの確認や自動初期化を活用し、永続化処理は `DatabaseManager` に一本化する。
- **Use localized resources and configuration defaults as contract. / ローカライズ文言と既定設定を契約として扱う。**
  - Any new UI copy or setting should extend the existing resource JSON/Config structures to prevent drift.
  - 新しい UI 文言や設定は既存の JSON／設定構造を拡張し、整合性を崩さないようにする。
- **Observe explicit error handling. / 明示的なエラーハンドリングを徹底する。**
  - Route failures through `log_error` for traceability while surfacing user-friendly messages from `strings.json`.
  - 障害は必ず `log_error` に記録しつつ、`strings.json` の文言でユーザーに分かりやすく通知する。

## Next Tasks & Challenges / 今後の課題
### Short Term / 短期的
- **Implement the remaining KivyMD screens. / 未実装の画面ロジックを完成させる。**
  - Wire the deck/season registration and match entry screens to actual database CRUD operations.
  - デッキ・シーズン登録、対戦入力画面をデータベース CRUD に接続する。
- **Add automated tests. / 自動テストを追加する。**
  - Cover `function` パッケージのユーティリティをユニットテストで保証し、DB 操作や設定読み書きのリグレッションを防ぐ。
- **Document setup & deployment. / セットアップとデプロイ手順を整備する。**
  - Provide environment requirements (Python, Kivy/KivyMD) and packaging strategy for desktop distribution.
  - Python・Kivy/KivyMD の依存関係やデスクトップ配布のパッケージ戦略を記載する。

### Mid Term / 中期的
- **Enhance analytics. / 分析機能を強化する。**
  - Build statistics views using aggregated match data (win-rate trends, opponent distribution).
  - 集計データを活用し、勝率推移や対戦相手分布などの統計画面を作成する。
- **Improve user experience. / ユーザー体験の改善。**
  - Introduce search/filter enhancements and keyboard-friendly workflows for rapid data entry.
  - 検索・絞り込み強化やキーボード中心の操作性向上を行う。
- **Prepare backup & migration tooling. / バックアップと移行ツールを整備する。**
  - Automate CSV export/import and future schema migrations beyond version 3.
  - CSV エクスポート／インポートやバージョン 3 以降のスキーマ移行を自動化する。

## Documentation Links / ドキュメントリンク
- [Project Wiki Overview / プロジェクト概要](docs/wiki/Overview.md)

## GUI Layout Guidelines / GUI 配置ルール
- すべての `.kv` ファイルは `resource/theme/gui/` 配下に集約します。構成は次のとおりです。
  ```text
  resource/theme/gui/
  ├── app.kv             # includes styles → components → screens
  ├── styles/            # トークン・タイポグラフィ等のスタイル定義
  ├── components/        # 複数画面で共有するウィジェット
  └── screens/           # 画面クラス名と 1:1 に対応する kv
  ```
- `screens/` 内のファイル名は Python 側のクラス名と一致させ、`<ClassName>:` から始めます。
- 新しい画面を追加する際は次の手順に従います。
  1. `function/screen/FooScreen.py` に `class FooScreen(MDScreen)` を定義する。
  2. `resource/theme/gui/screens/FooScreen.kv` を作成し、`<FooScreen>:` ルートでレイアウトを記述する。
  3. `resource/theme/gui/app.kv` へ `#:include screens/FooScreen.kv` を追加する。
  4. `main.py` で `ScreenManager` に `FooScreen(name="foo")` を登録する。
- Python クラスは状態・イベント処理のみを保持し、ウィジェットツリーやスタイルは KV ファイルへ集約します。`MatchEntryScreen` を参考
  に、`BooleanProperty` や `ListProperty` で UI 状態を公開し、KV 側で `disabled:` や `text:` をバインドしてください。
- 例: フィールド有効/無効を判定する場合は Python 側で `can_save = BooleanProperty(False)` を宣言し、KV で `disabled: not root.can_save`
  と記述します。ロジック側でウィジェットを生成・追加する実装は避けてください。
- スタイルを共通化したい場合は `styles/` に `.kv` を追加し、`app.kv` の include 順序（styles → components → screens）を守ります。
- PyInstaller などでバンドルする際は、`--add-data "resource;resource"` を付与し、リソースが同梱されるようにしてください。

## Environment Requirements / 必要環境
- **Python**: 3.10.x / 3.11.x（動作確認済み）
- **Kivy**: 2.2.1（`requirements.txt` に固定）
- **KivyMD**: 1.1.1（`requirements.txt` に固定）
- Windows 10/11 または最新の Ubuntu（GitHub Actions CI で検証）

## Setup / セットアップ手順
1. Python 3.10 を用意し、仮想環境を作成します。
   ```bash
   python3.10 -m venv .venv
   source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
   ```
2. `pip`, `setuptools`, `wheel` を最新化します。
   ```bash
   python -m pip install --upgrade pip setuptools wheel
   ```
3. ランタイム依存をインストールします。
   ```bash
   pip install --extra-index-url https://kivy.org/downloads/simple/ -r requirements.txt
   ```
4. 開発用ツールを併せて導入する場合は以下を実行します。
   ```bash
   pip install -r requirements-dev.txt
   pre-commit install
   ```

## Verified Environment
- Python 3.10 / 3.11
- Kivy 2.2.1
- KivyMD 1.1.1

> `requirements.in` / `requirements-dev.in` を更新した場合は、 `pip-compile` でロックファイルを再生成してください。

## CI / 自動テスト
- GitHub Actions にて Ubuntu / Windows のマトリクスで `from kivymd.uix.button import MDIconButton` のサニティテストを実行し、依存バージョン崩れを検知します。
- Lint は `pre-commit` で `ruff` と KivyMD の誤った import 検出を実施し、CI でも必須化しています。

## Lint & Pre-commit / 静的解析とフック
- `ruff` による PEP8 / import 整形、`kivymd.uix.iconbutton` の import 禁止ルールを導入しています。
- `.pre-commit-config.yaml` を利用してローカルコミット前に自動チェックを実行できます。
- 禁止 import に違反すると pre-commit および CI で失敗します。

