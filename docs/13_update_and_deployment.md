# 05. Update & Deployment / アップデートとデプロイ

## 1. Distribution Principles
- `Main.exe` は自己更新しない。必ず `Updater.exe` を経由して入れ替える。
- 配布形態は onefolder。`Main.exe`, `Updater.exe`, `resources/`, `version.json` をまとめて ZIP 化。
- インストール先は `%ProgramFiles%/DuelPerformanceLogger/`。ユーザー書き込み不可を前提とする。

## 2. Update Flow
1. `Main.exe` が GitHub Releases から ZIP をダウンロードし、ハッシュを検証。
2. ZIP を `%LOCALAPPDATA%/DuelPerformanceLogger/update/staging/` に展開。
3. `Updater.exe --install "<INSTALL_DIR>" --staging "<STAGING_DIR>" --main-name "Main.exe" --args "--via-updater --updated-from=<old> --updated-to=<new>"` を起動。
4. Updater は `Main.exe` の終了を待ち、ファイルを入れ替えてからアプリを再起動。

## 3. Rollback Strategy
- 更新前にインストールディレクトリを `<version>.bak` としてバックアップ。
- 失敗時はバックアップをリストアし、`updater.log` にステータスを書き込む。
- ユーザーへはポップアップで「前バージョンへ戻しました」と通知。

## 4. CI Integration
- GitHub Actions: `on: push: tags: - "DPL.*"` でトリガー。
- ステップ: (1) 依存インストール, (2) `pytest`, (3) `pyinstaller -y scripts/pyinstaller/duel_logger.spec`, (4) ZIP 圧縮, (5) リリースアップロード。
- 成果物には SHA256 ハッシュ (`sha256sums.txt`) を同梱し、利用者が検証できるようにする。
