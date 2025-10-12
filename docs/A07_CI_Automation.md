# A07. CI Automation
### CI・自動化方針の概要
DPL の継続的インテグレーションと自動化エージェント運用を統一するための指針です。ブランチ戦略や必須チェックを英語名で示しつつ、日本語で運用ノートを補足します。

## Table of Contents / 目次
- [Branch Strategy / ブランチ戦略](#branch-strategy)
- [Required Checks / 必須チェック](#required-checks)
- [Automation Agents / 自動化エージェント](#automation-agents)
- [Artifact Management / 成果物管理](#artifact-management)
- [Checklist / チェックリスト](#ci-checklist)

## <a id="branch-strategy"></a>Branch Strategy / ブランチ戦略
安定性とリリースサイクルを両立させるためのブランチ運用です。

- `main`: stable branch; direct pushes prohibited, merge via PR only。運用チームが参照します。
- `work`: default development branch where Codex contributions land。日常開発の基準です。
- Create `release/DPL.<MAJOR>.<MINOR>.<PATCH>` branches for release preparation and validate signed builds via CI。リリース候補の検証を徹底します。

## <a id="required-checks"></a>Required Checks / 必須チェック
PR マージ前に必ず通過すべき自動チェックです。

- `pytest` (unit tests)。全テストが成功すること。
- `ruff check .`。Python スタイルの一貫性を確認します。
- `mypy app/`。型検証で静的な欠陥を検出します。
- `python -m compileall app/`。バイトコード生成で構文エラーを早期検知します。
- Windows build success with `pyinstaller` in one-folder mode。配布物の生成を保証します。

## <a id="automation-agents"></a>Automation Agents / 自動化エージェント
自動 bot や Codex エージェントのガバナンスルールです。

- Codex agents must follow [`C20_Agent_Policies.md`](C20_Agent_Policies.md) and include change summaries plus test results in PRs。レビュー容易性を確保します。
- Dependency bots like Renovate may bump `requirements.txt` minor versions only。破壊的変更を防ぎます。
- Surface CI-provided environment variables via `function/core/env.py` rather than accessing `os.environ` directly。設定を一元管理します。

## <a id="artifact-management"></a>Artifact Management / 成果物管理
ビルド成果物とログの取り扱い方針です。

- Publish artefacts exclusively through GitHub Releases; avoid storing EXE binaries directly in the repository or Git LFS。配布経路を一本化します。
- Retain CI logs for 30 days and extend troubleshooting guidance within this document when recurring issues appear。知見の蓄積を促進します。
- Use `pip cache dir` for dependency caching and schedule a clean build at least weekly。キャッシュ汚染を防ぎます。

## <a id="ci-checklist"></a>Checklist / チェックリスト
CI 設定を更新した際に確認してください。

- [ ] 必須チェックがワークフローに設定されている。
- [ ] 自動化エージェントの権限とルールが最新ドキュメントに反映されている。
- [ ] 成果物の保存先が GitHub Releases に限定されている。

**Last Updated:** 2025-10-12
