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

