# 06. Security & Integrity / セキュリティ指針

## 1. Supply Chain
- 依存パッケージは `requirements.txt` のバージョンを固定し、`pip install --require-hashes` をサポートする。
- ダウンロードするアップデート ZIP は `SHA256` と `signature.json` (Ed25519) を検証する。
- アップデート署名鍵は `scripts/signing/` に保存せず、CI のシークレットとして管理。

## 2. Runtime Protections
- `Updater.exe` は一時ディレクトリへコピーしてから実行し、置換対象と競合しないようにする。
- DB の暗号化は行わないが、ユーザー名やメール等の個人情報は保存しない方針。
- ログ出力からアクセストークンなどの機密値をフィルタするため `function.cmn_logger.sanitize` を必ず通す。

## 3. Incident Handling
- セキュリティインシデント発生時は 24 時間以内に `SECURITY.md` を更新。
- `docs/06_security.md` に再発防止策を追記し、Slack #security チャンネルで周知。
- 重大脆弱性にはホットフィックス (PATCH バージョン) をリリースし、更新通知をアプリ内で強制表示。
