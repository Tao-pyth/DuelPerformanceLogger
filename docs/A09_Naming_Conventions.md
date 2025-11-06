# A09. Naming Conventions

This guide defines shared naming rules for Duel Performance Logger code and documentation assets, including category prefixes and numbering schemes.
このガイドは、カテゴリごとの接頭語や採番方式を含め、Duel Performance Logger のコードおよびドキュメント資産に共通する命名規則を定義します。

## Category Index / カテゴリ一覧

The table lists standard prefixes, scopes, and primary locations for each category.
標準的な接頭語、適用範囲、主な配置場所を以下の表に示します。

| Category | Prefix | Scope | Primary Location | Notes |
|----------|--------|-------|------------------|-------|
| Application Core | `APP` | Domain logic and shared modules under `app/function/` | `app/function/` | Covers database access and UI bridges. |
| Command-line Interface | `CLI` | Entry points and utilities under `cli/` | `cli/` | Applies to standalone scripts and helpers. |
| Test Suite | `TST` | Unit and integration tests under `tests/` | `tests/` | Uses Pytest-based verification. |
| Documentation | `DOC` | Design docs, operations guides, templates | `docs/` | Includes this manual and other knowledge bases. |
| Infrastructure & Tooling | `OPS` | CI/CD scripts and configuration | `.github/`, `scripts/` | Captures operational assets at the repository edge. |

## Numbering Rules / 番号採番ルール

Follow these steps to assign consistent identifiers.
一貫した識別子を割り当てるため、以下の手順に従います。

1. Each category uses zero-padded three-digit numbers starting at `001`.
   1. 各カテゴリでゼロ埋め三桁（`001` から開始）の番号を使用します。
2. Format names as `PREFIX-###` (for example, `APP-001`, `CLI-002`).
   2. 命名フォーマットは `PREFIX-###`（例: `APP-001`、`CLI-002`）とします。
3. Within a category, assign the next available number to avoid duplication.
   3. 同一カテゴリ内では未使用の連番を割り当て、番号の重複を避けます。
4. Documentation assets may keep existing `Axx/Bxx/Cxx` labels while storing `DOC` identifiers as metadata.
   4. ドキュメント資産は既存の `Axx/Bxx/Cxx` ラベルを維持しつつ、`DOC` 識別子をメタデータとして保持します。
5. When multiple modules share a folder, apply the identifier to the main entry point (`__init__.py`, `main()`), and allow helper modules to reuse the same ID.
   5. 複数モジュールを含むフォルダーでは主要エントリポイント（`__init__.py` や `main()`）に番号を付け、補助モジュールは同じ ID を共有できます。

**Tip:** Add a new row to the category table and restart numbering at `001` when introducing a new category.
**Tip:** 新しいカテゴリを追加する際は表に行を追加し、採番を `001` から開始してください。

## Reference Classification / 既存ファイルの分類

Use the table below as examples for mapping files to categories and identifiers.
以下の表を例として、ファイルをカテゴリや識別子に対応付けてください。

| File | Category | Proposed ID | Rationale |
|------|----------|-------------|-----------|
| `cli/restore_from_backup.py` | Command-line Interface | `CLI-001` | Provides the backup-restore CLI via `argparse`. |
| `app/function/cmn_database.py` | Application Core | `APP-001` | Centralizes database management, migrations, and exceptions. |
| `tests/test_versioning.py` | Test Suite | `TST-001` | Contains Pytest cases validating versioning logic. |

## Checklist for New Assets / 新規ファイル・機能追加チェックリスト

Review these items whenever you add new files or major features.
新しいファイルや大きな機能を追加する際は次の項目を確認してください。

- [ ] Choose the category closest to the asset’s responsibility and add it to the table if missing.
  - [ ] 対象資産の責務に最も近いカテゴリを選び、表に存在しない場合はカテゴリを追加している。
- [ ] Assign a new `PREFIX-###` identifier after checking the latest number in that category.
  - [ ] カテゴリ内の最新番号を確認し、`PREFIX-###` 形式の新しい識別子を割り当てている。
- [ ] Record the identifier in docstrings or comments so reviewers can reference it.
  - [ ] レビュアーが参照できるように、識別子を docstring またはコメントに記載している。
- [ ] Update the Reference Classification table for significant additions.
  - [ ] 重要な追加の場合は既存分類表を更新して履歴を残している。
- [ ] Synchronize related documentation and verify consistency with naming rules.
  - [ ] 関連ドキュメントを更新し、命名規約との整合性を確認している。
- [ ] Reflect any CI or test impacts by consulting guides such as `docs/A07_CI_Automation.md`.
  - [ ] CI やテストへの影響がある場合は `docs/A07_CI_Automation.md` などのガイドを参照して手順を反映している。

**Last Updated:** 2025-01-16
**最終更新日:** 2025-01-16
