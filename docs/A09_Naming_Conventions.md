# A09. Naming Conventions / 命名規約

Duel Performance Logger のコード／ドキュメント資産に共通の命名ルールを定め、
カテゴリごとの接頭語 (prefix) と連番付与の基準を明文化します。
新規ファイルの追加や大きな機能拡張を行う際は、本ガイドを参照して命名の一貫性を確保してください。

## Category Index / カテゴリ一覧
| Category / カテゴリ | Prefix / 接頭語 | Scope / 対象範囲 | 主な配置 | 補足 |
| --- | --- | --- | --- | --- |
| Application Core | `APP` | `app/function/` 配下のドメインロジックおよび共通モジュール | `app/function/` | データベース、UI ブリッジなどアプリケーションの中心機能。 |
| Command-line Interface | `CLI` | `cli/` 配下のエントリポイントとユーティリティ | `cli/` | 単体実行可能なスクリプトおよび CLI ヘルパー。 |
| Test Suite | `TST` | `tests/` 配下のユニットテスト、統合テスト | `tests/` | Pytest ベースの検証コード。 |
| Documentation | `DOC` | `docs/` 配下の設計書、運用手順書、テンプレート | `docs/` | 本書を含む、ナレッジベース全般。 |
| Infrastructure & Tooling | `OPS` | CI/CD、デプロイスクリプト、設定ファイル | `.github/`, `scripts/` など | リポジトリ外縁の運用資産。 |

## Numbering Rules / 番号採番ルール
1. 各カテゴリは 3 桁のゼロ埋め連番を用いる (`001` から開始)。
2. 命名フォーマットは `PREFIX-###`（例: `APP-001`, `CLI-002`）。
3. 既存番号との重複を避けるため、同一カテゴリ内で最新番号 + 1 を割り当てる。
4. ドキュメントの場合は、既存の `Axx/Bxx/Cxx` フォーマットと併用しつつ `DOC` 番号をメタデータとして記録する。
5. フォルダに複数モジュールがある場合、主要エントリポイント（`__init__.py`、`main()` 定義など）に番号を付与する。補助モジュールは必要に応じて同じ番号を共有できる。

> **Tip:** 新しいカテゴリを追加する場合は、上表に行を追加し、採番開始番号を `001` にリセットします。

## Reference Classification / 既存ファイルの分類
| File / ファイル | Category | Proposed ID | 根拠 |
| --- | --- | --- | --- |
| `cli/restore_from_backup.py` | Command-line Interface | `CLI-001` | バックアップ復元 CLI を提供し、`argparse` でエントリポイントを構築しているため。 |
| `app/function/cmn_database.py` | Application Core | `APP-001` | データベース管理を一元化するコアモジュールであり、マイグレーションや例外クラスを定義している。 |
| `tests/test_versioning.py` | Test Suite | `TST-001` | バージョン管理ロジックを検証する Pytest テストケース群を含む。 |

## Checklist for New Assets / 新規ファイル・機能追加チェックリスト
- [ ] 対象コードの責務に最も近いカテゴリを選定し、上表に存在しない場合はカテゴリを追加する。
- [ ] 選択したカテゴリの最新番号を確認し、`PREFIX-###` 形式で新しい識別子を割り当てる。
- [ ] モジュール内に docstring またはコメントで ID を記載し、コードレビューで参照できるようにする。
- [ ] 重要なファイル追加時は、本ドキュメントの「Reference Classification」表に追記して履歴を残す。
- [ ] 関連ドキュメント（README、運用手順、テスト仕様など）を更新し、命名規約との整合性を確認する。
- [ ] テストや CI 定義に影響がある場合、`docs/A07_CI_Automation.md` など関連ガイドを参照し手順を反映する。

**Last Updated:** 2025-01-16
