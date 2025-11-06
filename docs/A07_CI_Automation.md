# A07. CI Automation

This guidance standardizes continuous integration and automation agent operations for Duel Performance Logger.
このガイダンスは、Duel Performance Logger の継続的インテグレーションと自動化エージェント運用を標準化します。

## Table of Contents / 目次

The sections outline branch strategy, required checks, automation agents, artifact handling, and review checks.
以下のセクションでは、ブランチ戦略・必須チェック・自動化エージェント・成果物管理・確認事項について説明します。

- Branch Strategy
  - ブランチ戦略
- Required Checks
  - 必須チェック
- Automation Agents
  - 自動化エージェント
- Artifact Management
  - 成果物管理
- Checklist
  - チェックリスト

## <a id="branch-strategy"></a>Branch Strategy / ブランチ戦略

Balance stability and release cadence by assigning clear roles to each branch.
安定性とリリース速度を両立させるため、各ブランチに明確な役割を割り当てます。

- `main` is the stable branch; disable direct pushes and merge only through pull requests reviewed by maintainers.
  - `main` は安定ブランチであり、直接プッシュを禁止し、メンテナーがレビューしたプルリクエスト経由でのみマージします。
- `work` serves as the default development branch where Codex contributions land before promotion.
  - `work` は Codex の変更を受け入れる開発ブランチであり、昇格前の作業場所として利用します。
- Create `release/DPL.<MAJOR>.<MINOR>.<PATCH>` branches for release preparation and validate signed builds via CI.
  - リリース準備では `release/DPL.<MAJOR>.<MINOR>.<PATCH>` ブランチを作成し、CI で署名済みビルドを検証します。

## <a id="required-checks"></a>Required Checks / 必須チェック

Enforce the following checks before merging pull requests.
プルリクエストをマージする前に次のチェックを必ず通過させます。

- Run `pytest` to confirm unit tests pass.
  - `pytest` を実行して単体テストが成功することを確認します。
- Execute `ruff check .` and `mypy app/` to ensure style and type consistency.
  - `ruff check .` と `mypy app/` を実行し、スタイルと型の一貫性を確保します。
- Compile Python sources with `python -m compileall app/` and build the Windows one-folder package via `pyinstaller`.
  - `python -m compileall app/` でソースをバイトコード化し、`pyinstaller` を用いて Windows 向けワンフォルダー成果物を生成します。

## <a id="automation-agents"></a>Automation Agents / 自動化エージェント

Define governance for automation bots and agent workflows.
自動化ボットやエージェントの運用ルールを定義します。

- Codex agents must follow [`C20_Agent_Policies.md`](C20_Agent_Policies.md) and include change summaries plus test results in every PR.
  - Codex エージェントは [`C20_Agent_Policies.md`](C20_Agent_Policies.md) に従い、各 PR に変更概要とテスト結果を記載します。
- Allow dependency bots such as Renovate to bump `requirements.txt` only for minor or patch versions to avoid breaking changes.
  - Renovate などの依存関係ボットは、破壊的変更を避けるため `requirements.txt` のマイナー・パッチ更新のみに限定します。
- Surface CI-provided environment variables via `function/core/env.py` instead of accessing `os.environ` directly.
  - CI から渡される環境変数は `os.environ` を直接参照せず、`function/core/env.py` を経由して扱います。

## <a id="artifact-management"></a>Artifact Management / 成果物管理

Keep build outputs and logs controlled and discoverable.
ビルド成果物とログを整理し、追跡しやすい状態を保ちます。

- Publish release artifacts exclusively through GitHub Releases; avoid storing executables in the repository or Git LFS.
  - リリース成果物は GitHub Releases のみに公開し、リポジトリや Git LFS へ実行ファイルを保存しません。
- Retain CI logs for 30 days and document recurring issues in this file when patterns emerge.
  - CI ログは 30 日保持し、繰り返し発生する問題が見つかった場合は本ファイルに記録します。
- Use `pip cache dir` for dependency caching and schedule at least one clean build per week to prevent cache corruption.
  - 依存キャッシュには `pip cache dir` を利用し、キャッシュ汚染を防ぐため週 1 回以上のクリーンビルドを実施します。

## <a id="ci-checklist"></a>Checklist / チェックリスト

Confirm these items whenever CI settings change.
CI 設定を更新した際は次の項目を確認してください。

- [ ] Required checks are configured in the workflow.
  - [ ] 必須チェックがワークフローに設定されている。
- [ ] Automation agent permissions and rules reflect the latest documentation.
  - [ ] 自動化エージェントの権限とルールが最新ドキュメントに反映されている。
- [ ] Release artifacts are stored only in GitHub Releases.
  - [ ] リリース成果物の保存先が GitHub Releases に限定されている。

**Last Updated:** 2025-10-12
**最終更新日:** 2025-10-12
