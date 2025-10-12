# A01. Coding Guidelines
### コーディング規約の概要
Python/Eel ハイブリッドな Duel Performance Logger のコードベースに一貫性を持たせるための指針です。英語で規則名を示し、具体的な実践ポイントを日本語で補足します。

## Table of Contents / 目次
- [General Style / 全体スタイル](#general-style)
- [Naming Rules / 命名規則](#naming-rules)
- [Error Handling / 例外処理](#error-handling)
- [Testing Discipline / テスト運用](#testing-discipline)
- [Documentation / ドキュメント連携](#documentation)
- [Checklist / チェックリスト](#checklist)

## <a id="general-style"></a>General Style / 全体スタイル
DPL のモジュール構成や import 慣行を統一して、CI の静的解析を安定させます。

- Maintain **domain-first** segmentation under `function/` and reserve `cmn_*.py` for shared helpers。役割を明文化して循環依存を防ぎます。
- Disallow `try/except` around imports; resolve missing dependencies via environment setup。例外で握りつぶさず、`requirements.txt` の整備で解決します。
- Build file paths via `function.core.paths` factories rather than manual concatenation。テスト環境でも同一の解決結果を得られます。
- Centralise `eel.expose` calls in `app/main.py` while keeping bridge implementations in `app/function/web/`。UI 側からの呼び出し点を可視化します。

## <a id="naming-rules"></a>Naming Rules / 命名規則
モジュールや DSL の識別子を揃え、コードレビューの負担を軽減します。

- Host web views inside `resource/web/` and load templates relative to `index.html`。UI 資産の探索コストを下げます。
- Structure DB accessors as `fetch_*`, `insert_*`, `update_*`, `delete_*`。操作意図が名称から分かるようにします。
- Prefer `snake_case` keys for DSL (YAML) and `Sentence case` labels for UI display。翻訳差分を管理しやすい形に保ちます。

## <a id="error-handling"></a>Error Handling / 例外処理
ユーザーへの通知とロギングを両立させるためのルールです。

- Wrap UI-layer exceptions with custom classes defined in `function.cmn_error`。サポートチームが原因分類をしやすくします。
- Route severe failures through `function.cmn_logger.log_error` to `%LOCALAPPDATA%/DuelPerformanceLogger/logs/app.log`。監査証跡を一元化します。
- Before returning `sys.exit(1)` for CLI/batch flows, ensure errors are logged。バッチ運用時のサイレント失敗を回避します。

## <a id="testing-discipline"></a>Testing Discipline / テスト運用
回帰リスクを抑えるための最低限のテスト追加ルールです。

- When adding features, extend `tests/` with at least one happy path and one negative scenario。自動化された再現確認を保証します。
- For UI changes, run `npx eslint --ext .js resource/web/static/js/` followed by `npx prettier`。JavaScript の整形と lint を両立させます。
- During migrations, add snapshot DBs under `tests/migration` and execute `pytest -k migration`。スキーマ変更の後方互換を検証します。

## <a id="documentation"></a>Documentation / ドキュメント連携
コード変更とドキュメントを同期させるための運用です。

- Update [`C28_Wiki_Overview.md`](C28_Wiki_Overview.md) in each PR and attach screenshots for UI changes。社内共有 wiki を常に最新化します。
- Record revisions to this guideline and persist the latest hash in `docs/VERSION`。規約改定履歴を機械的に追跡します。
- When introducing translations, co-locate English and Japanese in the same paragraph so reviewers can cross-check quickly。訳語差異を減らします。

## <a id="checklist"></a>Checklist / チェックリスト
レビュー前に次の項目を確認してください。

- [ ] 新規モジュールが `function/` 内のドメイン構成に従っている。
- [ ] ログ出力が統一フォーマットで追加されている。
- [ ] テストとドキュメントの更新が同一 PR で行われている。

**Last Updated:** 2025-10-12
