#!/usr/bin/env python3
"""Utility script to reconstruct the development policy documentation.

The project lost the curated guideline documents that used to live under
``docs/``.  This helper reproduces the last agreed upon baseline so that
we can re-run it whenever we need to recover the markdown files.  The
script writes a fixed set of documents whose contents mirror the previous
revision that the team reviewed during the 2025-10 working session.

Usage
-----
$ python docs/rebuild_dev_policies.py            # write into docs/
$ python docs/rebuild_dev_policies.py --check    # verify without writing
$ python docs/rebuild_dev_policies.py --dest tmp # output elsewhere

The command is idempotent: if a file already exists with the same
content it will be left untouched.  A diff-style summary is printed to
STDOUT for quick verification.
"""

from __future__ import annotations

import argparse
import hashlib
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import Dict, Iterable


ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Document:
    """Represents a single policy document to be materialised."""

    relative_path: Path
    body: str

    def target(self, destination: Path) -> Path:
        return destination / self.relative_path

    def serialised(self) -> bytes:
        return self.body.encode("utf-8")

    def digest(self) -> str:
        return hashlib.sha256(self.serialised()).hexdigest()


def iter_documents() -> Iterable[Document]:
    """Yield the authoritative document set."""

    yield Document(
        Path("00_baseline.md"),
        dedent(
            """
            # 00. Environment Baseline / 環境ベースライン

            | Item | Baseline | Notes |
            | ---- | -------- | ----- |
            | Python | 3.10.x | Windows 10/11 (64bit) を想定した Kivy/KivyMD ランタイム。 |
            | Pip | pip >= 23 | `requirements.txt` を `--constraint` なしでインストール。 |
            | Build Tooling | PyInstaller 6.x onefolder | `scripts/pyinstaller/duel_logger.spec` を使用。 |
            | UI Toolkit | Kivy 2.3.x, KivyMD 1.1.x | SDL2 / ANGLE バイナリ依存を事前に取得。 |
            | Packaging Host | GitHub Actions `windows-latest` | ビルド成果物は Release Assets のみに配置。 |

            ## 1. Python Setup
            - 仮想環境を推奨。`python -m venv .venv && .venv\\Scripts\\activate`。
            - `pip install -r requirements.txt` 実行後に `kivy` が GPU 対応のバイナリを参照しているか確認。
            - Windows では `set KIVY_NO_CONSOLELOG=1` を `.env` に設定し、ログノイズを抑止。

            ## 2. OS Dependencies
            - Visual C++ 再頒布パッケージ 2019 以降をインストール。
            - Windows Defender / SmartScreen でブロックされないよう、未署名バイナリは手動で許可。
            - 開発時は `%APPDATA%/DuelPerformanceLogger/` 配下の DB/DSL を versioned backup する。

            ## 3. Tooling Matrix
            - テキストエディタは UTF-8 (BOM 無し) 固定。
            - `black` 23.x, `ruff` 0.6.x, `mypy` 1.10.x を静的検査ツールとして採用。
            - UI レイアウト確認用に `kivy_inspector` を利用可。実機動作は常にウィンドウサイズ 1280x720 以上で確認する。

            ## 4. Verification Checklist
            1. `python -m compileall app/` でバイトコード生成が警告なく通るか。
            2. `pytest` によるユニットテストが完了するか。
            3. `function/cmn_resources.py` が mgenplus フォントを正常に登録できるか。
            4. `DatabaseManager.ensure_database()` 呼び出しで schema version の差分が無いことを確認。
            """
        ).strip()
        + "\n",
    )

    yield Document(
        Path("01_coding_guidelines.md"),
        dedent(
            """
            # 01. Coding Guidelines / コーディング規約

            ## 1. General Style
            - `function/` 配下は **domain-first** でモジュールを分割する。`cmn_*.py` は共通ヘルパーのみに限定。
            - Import 文では `try/except` を禁止。依存欠如はインストール手順側で解決する。
            - `Path` を直接連結せず、`function.core.paths` に定義したファクトリを経由する。
            - Kivy プロパティは `StringProperty` 等の型を明示し、`ObjectProperty(None)` の濫用を避ける。

            ## 2. Naming Rules
            - 画面クラスは `<Feature>NameScreen` (例: `MatchEntryScreen`) とし、対応する KV は `resource/theme/gui/screens/<Feature>NameScreen.kv`。
            - DB アクセサは `fetch_*`, `insert_*`, `update_*`, `delete_*` の 4 系列に揃える。
            - DSL (YAML) のキーは `snake_case`、UI に表示する識別子は `Sentence case` を採用。

            ## 3. Error Handling
            - UI 層で捕捉する例外は `function.cmn_error` に定義したカスタム例外へラップ。
            - 重大な失敗は `function.cmn_logger.log_error` を経由して `%LOCALAPPDATA%/DuelPerformanceLogger/logs/app.log` に出力。
            - CLI/バッチ実行時は `sys.exit(1)` を返す前に必ずエラーログへ書き込む。

            ## 4. Testing Discipline
            - 機能追加時は `tests/` に回帰テストを追加し、**少なくとも 1 つ**のハッピーパスと 1 つの異常系をカバーする。
            - UI 変更時は `resource/theme/gui/screens/` 配下の KV を `kivy_parser` で lint し、無効なプロパティを検出する。
            - マイグレーション実装時は `tests/migration` にスナップショット DB を追加し、`pytest -k migration` を実行する。

            ## 5. Documentation
            - PR には `docs/wiki/Overview.md` を更新し、変更点のスクリーンショットを添付。
            - 規約変更は本ドキュメントを更新し、最新版のハッシュを `docs/VERSION` に記録する。
            - 翻訳追加時は英語と日本語を同じ段落に併記し、読み手が選択できるようにする。
            """
        ).strip()
        + "\n",
    )

    yield Document(
        Path("02_database_policy.md"),
        dedent(
            """
            # 02. Database Policy / データベース運用方針

            ## 1. Schema Governance
            - スキーマバージョンは `db_metadata` テーブルの `schema_version` カラムで管理し、SemVer 互換の整数 3 桁 (例: 10203)。
            - 変更時は `app/function/core/version.py` の `__version__` を更新し、マイグレーションチェーンに追記する。
            - マイグレーションは冪等性を重視し、`IF NOT EXISTS` / `ALTER TABLE ADD COLUMN` のみを利用する。

            ## 2. Backup Strategy
            - `%APPDATA%/DuelPerformanceLogger/backups/` に ZIP バックアップを保存。ファイル名は `DPL_{app_version}_{timestamp}.zip`。
            - 自動バックアップ前に SQLite の `VACUUM` を実施し、ファイル断片化を防止。
            - 復元時は一時ディレクトリへ展開後、整合性チェック (`PRAGMA integrity_check`) を実行してから本番 DB と置換。

            ## 3. Access Layer Rules
            - `DatabaseManager` のコネクションは `contextlib.contextmanager` で扱い、`commit` / `rollback` を確実に発火。
            - クエリ文字列は `?` プレースホルダでパラメータバインディングを徹底し、フォーマット文字列は使用しない。
            - 長時間実行クエリはスレッドプールへ委譲し、UI スレッドでブロックしない。

            ## 4. Test Fixtures
            - `tests/fixtures/db/seed.sql` に初期化スクリプトを配置し、差分が出た際は `docs/02_database_policy.md` の履歴を更新。
            - マイグレーションテストは `pytest --maxfail=1 -k db_migration` を最低 1 日 1 回 CI で実行。
            - スキーマ図は `docs/resource/schema.drawio` に保存し、更新時は PNG もエクスポートする。
            """
        ).strip()
        + "\n",
    )

    yield Document(
        Path("03_logging_monitoring.md"),
        dedent(
            """
            # 03. Logging & Monitoring / ログと監視

            ## 1. Logging Channels
            - アプリログ: `%LOCALAPPDATA%/DuelPerformanceLogger/logs/app.log` (1 日 1 ファイル, UTF-8)。
            - デバッグログ: `%LOCALAPPDATA%/DuelPerformanceLogger/logs/debug.log`。`DEBUG` レベル以上を記録。
            - 更新ログ: `%LOCALAPPDATA%/DuelPerformanceLogger/logs/updater.log`。Updater.exe の実行記録専用。

            ## 2. Format & Retention
            - ログ形式は `[YYYY-MM-DD HH:MM:SS][LEVEL][module] message`。
            - 30 日より古いログは起動時に自動削除。閾値は `config["logging"]["retention_days"]` で変更可。
            - 重大障害 (`CRITICAL`) 発生時は Windows イベントログにも転送する (pywin32 `win32evtlogutil.ReportEvent`)。

            ## 3. Monitoring Hooks
            - `function.cmn_logger` は `logging.LoggerAdapter` を返し、`extra={"request_id": str(uuid4())}` を付与。
            - UI のトースト通知と同期させるため、`log_info` `log_warning` `log_error` ヘルパーを利用する。
            - Updater.exe からの進行状況は `%LOCALAPPDATA%/DuelPerformanceLogger/status/update.json` に JSON で出力。

            ## 4. Incident Response
            1. ログを収集し、`tools/support/package_logs.ps1` で ZIP 化。
            2. 発生バージョン・OS ビルド・再現手順を `docs/wiki/Overview.md#Incident-Report` に追記。
            3. `docs/03_logging_monitoring.md` に対応状況を履歴として更新。
            """
        ).strip()
        + "\n",
    )

    yield Document(
        Path("04_async_policy.md"),
        dedent(
            """
            # 04. Async & Progress Policy / 非同期処理・進捗表示方針

            ## 1. Threading Rules
            - UI スレッド (Kivy メインループ) で重い処理は実行しない。`function.cmn_async.run_in_executor` を利用。
            - 同期 I/O は `ThreadPoolExecutor(max_workers=4)` に委譲し、戻り値は `Clock.schedule_once` で UI へ反映。
            - Python の `asyncio` は採用しない。Kivy の event loop と整合しないため。

            ## 2. Progress Feedback
            - 長時間処理 (> 500ms) は必ずプログレス表示 (ダイアログ or snackbar) を出す。
            - 進捗率が不明な処理はインジケータをインデターミネイト表示に設定し、タイムアウト時はリトライ導線を用意。
            - CSV エクスポートなど、完了時にはトースト通知で保存先パスを表示。

            ## 3. Cancellation & Retry
            - Updater.exe 実行時はキャンセル不可。代わりに `--dry-run` オプションを提供し、検証モードで動作確認。
            - DB マイグレーションは途中失敗時に自動ロールバックし、再実行は安全であることを保証。
            - 非同期タスクは `function.cmn_async.AsyncJobRegistry` で追跡し、重複実行を防止。

            ## 4. Testing Guidance
            - `tests/async/test_job_registry.py` を追加し、重複タスク抑止ロジックを単体テスト。
            - UI からの操作は `pytest --kivy` プラグインを利用して自動化し、プログレスダイアログの表示/非表示を検証する。
            """
        ).strip()
        + "\n",
    )

    yield Document(
        Path("05_update_and_deployment.md"),
        dedent(
            """
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
            """
        ).strip()
        + "\n",
    )

    yield Document(
        Path("06_security.md"),
        dedent(
            """
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
            """
        ).strip()
        + "\n",
    )

    yield Document(
        Path("07_ci_automation.md"),
        dedent(
            """
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
            """
        ).strip()
        + "\n",
    )

    yield Document(
        Path("08_release.md"),
        dedent(
            """
            # 08. Release Management / リリース管理

            ## 1. Versioning
            - バージョンスキームは `DPL.<MAJOR>.<MINOR>.<PATCH>`。
            - 破壊的変更: MAJOR++ / MINOR, PATCH を 0 にリセット。
            - 後方互換追加: MINOR++ / PATCH を 0 にリセット。
            - バグ修正: PATCH++。

            ## 2. Release Checklist
            1. `app/function/core/version.py` の `__version__` を更新。
            2. `docs/wiki/Overview.md` の「Project Snapshot」を最新化。
            3. マイグレーションを実行し、`logs/app.log` に結果を記録。
            4. `pytest`, `ruff`, `mypy` を実行。
            5. `pyinstaller -y scripts/pyinstaller/duel_logger.spec`。
            6. `tools/release/verify_update.py` で Updater の replace-and-relaunch を検証。
            7. GitHub Release を作成し、ZIP と SHA256 を添付。

            ## 3. Communication
            - Release Notes は日本語/英語併記で記述。テンプレートは `docs/resource/release_note_template.md`。
            - 既知の問題 (Known Issues) は release note の末尾に掲載し、回避策を記載。
            - 重大バグ発生時はホットフィックス版を 24 時間以内に配布。

            ## 4. Post Release Tasks
            - Issue Tracker へ「リリース済み」ラベルを追加し、フィードバックを収集。
            - 収集したログやクラッシュダンプは 14 日で破棄。
            - 次期開発用の `work` ブランチを `main` から再作成し、マージキューをクリア。
            """
        ).strip()
        + "\n",
    )


DOCS: Dict[Path, Document] = {doc.relative_path: doc for doc in iter_documents()}


def compute_diff(target: Path, document: Document) -> str:
    """Return a short diff-like status string for display."""

    if not target.exists():
        return "(new)"

    existing_digest = hashlib.sha256(target.read_bytes()).hexdigest()
    if existing_digest == document.digest():
        return "(up-to-date)"
    return "(will update)"


def write_documents(destination: Path, check_only: bool) -> int:
    """Write the documents into *destination* and return number of changes."""

    destination.mkdir(parents=True, exist_ok=True)

    changed = 0
    for doc in DOCS.values():
        target = doc.target(destination)
        status = compute_diff(target, doc)
        print(f"- {target.relative_to(destination)} {status}")

        if check_only:
            continue

        if status == "(up-to-date)":
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(doc.serialised())
        changed += 1

    return changed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dest",
        type=Path,
        default=ROOT,
        help="Destination directory (defaults to docs/).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only report what would change without writing files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    destination = args.dest
    if not destination.is_absolute():
        destination = (ROOT / args.dest).resolve()

    changed = write_documents(destination, check_only=args.check)

    if args.check:
        print("No files were modified (check mode).")
    else:
        print(f"Completed. {changed} file(s) written.")


if __name__ == "__main__":
    main()
