# B13. アップデート配備 (Update Deployment)
Main.exe が自己更新せず Updater.exe を介して入れ替わるという原則を守るための手順とロールバック方針を整理します。

## 目次 / Table of Contents
- [配布原則 (Distribution Principles)](#distribution-principles)
- [アップデートフロー (Update Flow)](#update-flow)
- [ロールバック戦略 (Rollback Strategy)](#rollback-strategy)
- [CI 連携 (CI Integration)](#ci-integration)
- [チェックリスト (Checklist)](#deployment-checklist)

## <a id="distribution-principles"></a>配布原則 (Distribution Principles)
- `Main.exe` は自己更新せず、常に `Updater.exe` を経由して入れ替えます。
- 配布形態は PyInstaller one-folder。`Main.exe`、`Updater.exe`、`resource/`、`version.json` をまとめて ZIP 化します。
- インストール先は `%ProgramFiles%/DuelPerformanceLogger/` を前提とし、一般ユーザーは書き込み不可とします。

## <a id="update-flow"></a>アップデートフロー (Update Flow)
1. `Main.exe` が GitHub Releases から ZIP をダウンロードし、SHA256 を検証します。
2. ZIP を `%LOCALAPPDATA%/DuelPerformanceLogger/update/staging/` に展開します。
3. `Updater.exe --install "<INSTALL_DIR>" --staging "<STAGING_DIR>" --main-name "Main.exe" --args "--via-updater --updated-from=<old> --updated-to=<new>"` を起動します。
4. Updater は `Main.exe` の終了を待ち、ファイルを入れ替えて再起動します。

## <a id="rollback-strategy"></a>ロールバック戦略 (Rollback Strategy)
- 更新前にインストールディレクトリを `<version>.bak` としてバックアップします。
- 失敗時はバックアップをリストアし、`updater.log` にステータスを書き込みます。
- ユーザーにはポップアップで「前バージョンへ戻しました」と通知します。

## <a id="ci-integration"></a>CI 連携 (CI Integration)
- GitHub Actions のトリガーは `on: push: tags: - "DPL.*"` を使用します。
- 実行ステップ: (1) 依存インストール, (2) `pytest`, (3) `pyinstaller -y scripts/pyinstaller/duel_logger.spec`, (4) ZIP 圧縮, (5) リリースアップロード。
- 成果物には `sha256sums.txt` を同梱し、利用者が検証できるようにします。

## <a id="deployment-checklist"></a>チェックリスト (Checklist)
- [ ] アップデート ZIP の SHA256 を公開した。
- [ ] ステージングディレクトリのクリーンアップを実施した。
- [ ] ロールバックバックアップが保存されている。
- [ ] CI からリリース資産が正常にアップロードされた。

**最終更新日 (Last Updated):** 2025-10-12
