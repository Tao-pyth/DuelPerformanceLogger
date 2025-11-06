# A01. Coding Guidelines

These guidelines keep the Python/Eel hybrid codebase of Duel Performance Logger consistent by pairing rule names with actionable practices.
これらのガイドラインは、Duel Performance Logger の Python/Eel ハイブリッドなコードベースに一貫性を持たせるために、規則名と実践的な運用ポイントを整理したものです。

## Table of Contents / 目次

The following topics cover style conventions, naming, error handling, testing, documentation, and review preparation.
以下のトピックでは、スタイル規約・命名・例外処理・テスト・ドキュメント・レビュー準備について説明します。

- General Style
  - 全体スタイル
- Naming Rules
  - 命名規則
- Error Handling
  - 例外処理
- Testing Discipline
  - テスト運用
- Documentation
  - ドキュメント連携
- Checklist
  - チェックリスト

## <a id="general-style"></a>General Style / 全体スタイル

Align module boundaries and import habits to stabilize static analysis in CI.
モジュール境界や import の習慣を揃えて、CI における静的解析を安定させます。

- Maintain **domain-first** segmentation under `function/`, reserving `cmn_*.py` for shared helpers to document responsibilities and avoid circular dependencies.
  - `function/` 配下では **ドメイン優先** の区分を維持し、共通ヘルパーは `cmn_*.py` に集約して責務を明確化し、循環依存を防ぎます。
- Disallow `try/except` blocks around imports and resolve missing packages by fixing `requirements.txt` or environment setup instead of suppressing errors.
  - import 文を囲む `try/except` を禁止し、エラーを握りつぶさずに `requirements.txt` や環境設定を是正して不足パッケージを解決します。
- Build file paths through factories in `function.core.paths` to obtain identical results in local and test environments.
  - ローカルとテスト環境で同一のパス解決を得るために、`function.core.paths` のファクトリー経由でファイルパスを組み立てます。
- Centralize `eel.expose` declarations inside `app/main.py` while keeping bridge implementations within `app/function/web/` for traceable UI entry points.
  - UI からの呼び出し点を可視化するために、`eel.expose` の宣言は `app/main.py` に集約し、ブリッジ実装は `app/function/web/` に配置します。

## <a id="naming-rules"></a>Naming Rules / 命名規則

Keep module and DSL identifiers consistent to reduce review friction and improve discoverability.
モジュールや DSL の識別子を統一し、レビュー負担を軽減するとともに探索性を高めます。

- Host web views inside `resource/web/` and load templates relative to `index.html` to simplify UI asset discovery.
  - UI 資産の探索を容易にするため、Web ビューは `resource/web/` に配置し、テンプレートは `index.html` を起点に読み込みます。
- Name database accessors using `fetch_*`, `insert_*`, `update_*`, and `delete_*` so the intended operation is clear from the identifier.
  - 目的を名称から判別できるように、データベースアクセス関数には `fetch_*`・`insert_*`・`update_*`・`delete_*` の命名を用います。
- Use `snake_case` keys for DSL (YAML) files and `Sentence case` labels for UI display strings to keep translation diffs manageable.
  - 翻訳差分を管理しやすくするため、DSL (YAML) のキーは `snake_case`、UI 表示のラベルは `Sentence case` を採用します。

## <a id="error-handling"></a>Error Handling / 例外処理

Balance user-facing notifications with logging so that support teams can investigate failures efficiently.
ユーザー通知とロギングを両立させ、サポートチームが障害を効率的に調査できるようにします。

- Wrap UI-layer exceptions with custom classes from `function.cmn_error` so support staff can categorize issues quickly.
  - サポート担当者が原因を分類しやすいように、UI 層の例外は `function.cmn_error` のカスタムクラスでラップします。
- Route severe failures through `function.cmn_logger.log_error`, which writes to `%LOCALAPPDATA%/DuelPerformanceLogger/logs/app.log` for a unified audit trail.
  - 重大な障害は `%LOCALAPPDATA%/DuelPerformanceLogger/logs/app.log` に書き込む `function.cmn_logger.log_error` を経由させ、監査証跡を一元化します。
- Before returning `sys.exit(1)` in CLI or batch flows, ensure the error has been logged to prevent silent failures.
  - CLI やバッチフローで `sys.exit(1)` を返す前に必ずエラーを記録し、サイレントな失敗を防ぎます。

## <a id="testing-discipline"></a>Testing Discipline / テスト運用

Apply a minimum testing standard to control regression risk whenever the codebase changes.
コードベースの変更時に回帰リスクを抑制するための最低限のテスト基準を適用します。

- When adding features, extend `tests/` with at least one happy path and one negative scenario to guarantee automated verification.
  - 機能追加時には、少なくともハッピーパスとネガティブシナリオを 1 件ずつ `tests/` に追加し、自動化された検証を確保します。
- For UI modifications, run `npx eslint --ext .js resource/web/static/js/` followed by `npx prettier` to maintain linting and formatting.
  - UI を変更した場合は `npx eslint --ext .js resource/web/static/js/` を実行し、続けて `npx prettier` を実行して lint と整形を維持します。
- During migrations, place snapshot databases under `tests/migration` and execute `pytest -k migration` to confirm backward compatibility.
  - マイグレーション時には `tests/migration` にスナップショット DB を配置し、`pytest -k migration` を実行して後方互換性を検証します。

## <a id="documentation"></a>Documentation / ドキュメント連携

Synchronize code changes with documentation so reviewers and stakeholders receive consistent information.
レビュー担当者やステークホルダーが一貫した情報を得られるよう、コード変更とドキュメントを同期させます。

- Update [`C28_Wiki_Overview.md`](C28_Wiki_Overview.md) in each PR and attach screenshots for UI changes to keep the internal wiki current.
  - 各 PR で [`C28_Wiki_Overview.md`](C28_Wiki_Overview.md) を更新し、UI 変更時はスクリーンショットを添付して社内 Wiki を最新に保ちます。
- Record revisions to this guideline and store the latest hash in `docs/VERSION` so policy history can be tracked mechanically.
  - 本ガイドラインの改定履歴を記録し、最新ハッシュを `docs/VERSION` に保存して運用履歴を機械的に追跡できるようにします。
- When introducing translations, keep English and Japanese sentences adjacent so reviewers can cross-check wording quickly.
  - 翻訳を追加する場合は英語と日本語の文を隣接させ、レビュー担当者が表現差異をすぐ確認できるようにします。

## <a id="checklist"></a>Checklist / チェックリスト

Confirm the following items before submitting changes for review.
レビューに提出する前に次の項目を確認してください。

- [ ] New modules follow the domain-driven structure under `function/`.
  - [ ] 新規モジュールが `function/` 内のドメイン構成に従っている。
- [ ] Logging entries use the standardized format.
  - [ ] ログ出力が統一フォーマットで追加されている。
- [ ] Tests and documentation updates are included in the same PR.
  - [ ] テストとドキュメントの更新が同一 PR で行われている。

**Last Updated:** 2025-10-12
**最終更新日:** 2025-10-12
