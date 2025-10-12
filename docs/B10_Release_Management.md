# B10. リリース管理 (Release Management)
Duel Performance Logger の PyInstaller one-folder 配布と Updater.exe 運用を安全に進めるための手順書です。主要な手順名は英語を添えますが、説明は日本語を中心にまとめています。

## 目次 / Table of Contents
- [バージョンポリシー (Version Policy)](#version-policy)
- [リリース分岐 (Release Branching)](#release-branching)
- [パッケージング手順 (Packaging Procedure)](#packaging)
- [アップデート配信 (Update Distribution)](#distribution)
- [ドキュメント更新 (Documentation Updates)](#documentation-updates)
- [CI パイプライン (CI Pipeline)](#ci-pipeline)
- [チェックリスト (Checklist)](#release-checklist)

## <a id="version-policy"></a>バージョンポリシー (Version Policy)
- バージョン形式は `DPL.<MAJOR>.<MINOR>.<PATCH>` を採用します。
- MAJOR は破壊的変更時 (DB スキーマ不整合や Updater CLI 非互換) に更新します。
- MINOR は後方互換な新機能追加時 (DSL キー追加や UI 強化) に上げます。
- PATCH はバグ修正や内部改善のみを含みます。
- 定義元は `app/function/core/version.py::__version__` であり、更新時にコミットメッセージへ明記します。

## <a id="release-branching"></a>リリース分岐 (Release Branching)
1. `main` ブランチから `release/DPL.x.y.z` を作成し、以降は緊急修正のみを取り込みます。
2. リリースブランチでテスト完了後にタグ `DPL.x.y.z` を付与します。
3. 本番公開後は `main` にマージバックし、`work` 側で次の開発バージョンへバンプします。

## <a id="packaging"></a>パッケージング手順 (Packaging Procedure)
1. `python scripts/tools/build.py --mode onefolder --version DPL.x.y.z` を実行します。
2. 出力物 `dist/DuelPerformanceLogger/` に `Main.exe` と `Updater.exe`、資産ファイルが揃っていることを確認します。
3. `scripts/tools/sign.ps1 dist/DuelPerformanceLogger/*.exe` でコード署名を行います。
4. `scripts/tools/package.ps1 dist/DuelPerformanceLogger DuelPerformanceLogger-DPL.x.y.z-win64.zip` で ZIP 化します。

## <a id="distribution"></a>アップデート配信 (Update Distribution)
- 作成した ZIP を GitHub Releases へアップロードします。
- `checksums.txt` に SHA256 を追記し、リリースノートに同値を記載します。
- 更新サーバーの manifest (`updates/manifest.json`) に新バージョンを登録します。
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

## <a id="documentation-updates"></a>ドキュメント更新 (Documentation Updates)
- `/docs` 配下の該当ガイドを新しいファイル名 (例: [`A06_Logging_Strategy.md`](A06_Logging_Strategy.md)) に合わせて更新します。
- `CHANGELOG.md` に差分を追記し、主要ハイライトを日本語でまとめます。
- リリースノートには以下を含めます:
  - ハイライト
  - 既知の問題 (参照: [`C22_Known_Issues.md`](C22_Known_Issues.md))
  - SHA256 値
  - 更新手順とロールバック案内

## <a id="ci-pipeline"></a>CI パイプライン (CI Pipeline)
- タグ作成で `windows-build.yml` が起動し、lint → pytest → build → sign → upload の順で実行します。
- 失敗時は Slack `#dpl-release` に通知し、対応内容を [`C28_Wiki_Overview.md`](C28_Wiki_Overview.md) のインシデント欄へ追記します。

## <a id="release-checklist"></a>チェックリスト (Checklist)
- [ ] `__version__` を新バージョンへ更新した。
- [ ] マイグレーションテストが成功している。
- [ ] PyInstaller one-folder ビルドを検証した。
- [ ] Updater manifest を更新した。
- [ ] リリースノートと既知の問題を公開した。

**最終更新日 (Last Updated):** 2025-10-12
