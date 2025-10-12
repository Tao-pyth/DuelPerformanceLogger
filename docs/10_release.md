# 08. リリース管理ガイド (Release Management)

PyInstaller one-folder 構成と Updater.exe を前提にした Duel Performance Logger のリリース手順を定義します。

## バージョンポリシー

- 形式: `DPL.<MAJOR>.<MINOR>.<PATCH>`。
- MAJOR: 破壊的変更 (DB schema 不整合、Updater CLI 互換性切り捨て)。
- MINOR: 後方互換な新機能追加 (DSL キー追加、UI 機能強化)。
- PATCH: バグ修正および内部改善のみ。
- バージョン定義は `app/function/core/version.py::__version__`。

## リリース分岐

1. `main` ブランチから release ブランチ `release/DPL.x.y.z` を作成。
2. 変更を凍結し、テスト完了後にタグ付け。
3. リリース後は `main` にマージバックし、バージョンを次開発版に進める。

## パッケージング手順

1. `python scripts/tools/build.py --mode onefolder --version DPL.x.y.z`。
2. 生成物: `dist/DuelPerformanceLogger/` (Main.exe, Updater.exe, assets)。
3. `scripts/tools/sign.ps1 dist/DuelPerformanceLogger/*.exe` で署名。
4. `scripts/tools/package.ps1 dist/DuelPerformanceLogger DuelPerformanceLogger-DPL.x.y.z-win64.zip` でアーカイブ。

## アップデート配信

- ZIP を GitHub Release にアップロード。
- `checksums.txt` に SHA256 を追記。
- 更新サーバーの manifest (`updates/manifest.json`) にバージョンを登録。
- Manifest 例:

```json
{
  "channel": "stable",
  "latest": "DPL.1.4.0",
  "packages": {
    "DPL.1.4.0": {
      "url": "https://downloads.example.com/DPL.1.4.0.zip",
      "sha256": "..."
    }
  }
}
```

## ドキュメント更新

- `docs/` 配下の該当ガイドを更新。
- `CHANGELOG.md` に差分を追記。
- バージョンタグと同名の Release Notes を作成し、以下を記載:
  - ハイライト
  - 既知の問題 (`docs/known_issues.md` 参照)
  - SHA256
  - アップデート手順

## CI パイプライン

- タグプッシュで `windows-build.yml` が実行。
- ステップ: lint → pytest → build → sign → upload。
- 失敗時は Slack `#dpl-release` に通知。

## Checklist

- [ ] `__version__` を更新。
- [ ] マイグレーションテストが成功。
- [ ] PyInstaller one-folder ビルドを検証。
- [ ] Updater manifest を更新。
- [ ] Release Notes と `known_issues` を公開。

**Last Updated:** 2025-10-12
