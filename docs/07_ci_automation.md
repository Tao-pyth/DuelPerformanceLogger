# 07. CI / Automation Policy / CI・自動化方針

## 1. Branch Strategy
- `main`: 安定版。直接 push 禁止、PR マージのみ。
- `work`: 開発中デフォルトブランチ。Codex の作業はここへマージ。
- リリース準備時は `release/DPL.<MAJOR>.<MINOR>.<PATCH>` ブランチを作成し、CI で署名済みビルドを確認。

## 2. Required Checks
- `pytest` (ユニットテスト)
- `ruff check .`
- `mypy app/`
- `python -m compileall app/`
- Windows ビルドでの `pyinstaller` 成功確認

## 3. Automation Agents
- Codex は `AGENTS.md` の規約に従い、PR 作成時に変更点サマリとテスト結果を必ず記載。
- Renovate 等の依存更新ボットは `requirements.txt` のマイナーバージョン更新のみ許可。
- CI からの環境変数は `function/core/env.py` に集約し、直接 `os.environ` を参照しない。

## 4. Artifact Management
- 成果物は GitHub Releases のみ。Git LFS やリポジトリ直下へ EXE を置かない。
- CI ログは 30 日保持。必要に応じて `docs/07_ci_automation.md` にトラブルシューティングを追記。
- 依存キャッシュは `pip cache dir` を利用し、クリーンビルドは週 1 回実施。
