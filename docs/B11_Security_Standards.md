# B11. セキュリティ基準 (Security Standards)
依存パッケージのサプライチェーン対策からランタイム保護、インシデント対応までを日本語主体で整理し、必要な英語用語を括弧で補足します。

## 目次 / Table of Contents
- [サプライチェーン管理 (Supply Chain)](#supply-chain)
- [ランタイム保護 (Runtime Protections)](#runtime-protections)
- [インシデント対応 (Incident Handling)](#incident-handling)
- [チェックリスト (Checklist)](#security-checklist)

## <a id="supply-chain"></a>サプライチェーン管理 (Supply Chain)
- 依存パッケージは `requirements.txt` のバージョンを固定し、`pip install --require-hashes` をサポートできるようハッシュを管理します。
- アップデート用 ZIP は `SHA256` と `signature.json` (Ed25519) を検証し、検証失敗時は `UP-200` として処理します。
- 署名鍵は `scripts/signing/` に置かず、CI シークレットストアで保管します。アクセスログを四半期ごとに監査します。

## <a id="runtime-protections"></a>ランタイム保護 (Runtime Protections)
- `Updater.exe` は一時ディレクトリへコピーした後に実行し、置換対象ファイルと競合しないようにします。
- DB 暗号化は行いませんが、個人情報 (PII) を保持しない方針を維持します。設定値は匿名化した識別子のみ保存します。
- ログ出力に機密値が含まれる場合は `function.cmn_logger.sanitize` を通し、`A06_Logging_Strategy.md` の構造化フィールド規約に従います。

## <a id="incident-handling"></a>インシデント対応 (Incident Handling)
- セキュリティインシデント発生時は 24 時間以内に `SECURITY.md` を更新し、影響範囲と対処状況を明記します。
- 再発防止策は本ドキュメントおよび [`C28_Wiki_Overview.md`](C28_Wiki_Overview.md) のセキュリティ欄へ追記します。
- 重大脆弱性が判明した場合は PATCH バージョンのホットフィックスをリリースし、アプリ内通知を強制表示します。

## <a id="security-checklist"></a>チェックリスト (Checklist)
- [ ] `requirements.txt` のハッシュ値が更新されている。
- [ ] 更新 ZIP の署名検証結果がログに記録されている。
- [ ] 機密情報がログへ出力されていない。
- [ ] インシデント報告が 24 時間以内に公開されている。

**最終更新日 (Last Updated):** 2025-10-12
