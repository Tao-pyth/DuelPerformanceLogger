#!/usr/bin/env python3
"""ドキュメント整合性チェックおよびインデックス生成スクリプト。

記載内容
    - Markdown 構成ファイルの有無やリンク妥当性を検証する関数群。
    - docs_index.json の生成ロジック。

想定参照元
    - リリース前チェックや CI でのドキュメント検証。
    - ドキュメント担当者が手動で整合性を確認する際の CLI。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

DOC_ROOT = Path(__file__).resolve().parent
INDEX_PATH = DOC_ROOT / "docs_index.json"
EXPECTED_ORDER = [
    "A00_Baseline_Environment.md",
    "A01_Coding_Guidelines.md",
    "A02_Database_Policy.md",
    "A03_Interface_Control_Core.md",
    "A04_Async_Policy.md",
    "A05_Error_Taxonomy.md",
    "A06_Logging_Strategy.md",
    "A07_CI_Automation.md",
    "A08_Project_Structure.md",
    "B10_Release_Management.md",
    "B11_Security_Standards.md",
    "B12_Test_Plan.md",
    "B13_Update_Deployment.md",
    "C20_Agent_Policies.md",
    "C21_Improvement_Proposals.md",
    "C22_Known_Issues.md",
    "C23_Rebuild_Policies_Script.py",
    "C24_Codex_Core_Template.md",
    "C25_Codex_Doc_Template.md",
    "C26_Codex_UI_Template.md",
    "C27_UI_Spec_MenuScreen.md",
    "C28_Wiki_Overview.md",
]

LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
ANCHOR_PATTERN = re.compile(r"<a[^>]+id=\"([^\"]+)\"")
HEADING_PATTERN = re.compile(r"^#+\s+(.+)$", re.MULTILINE)


@dataclass
class LinkIssue:
    """リンク検証で検出した問題点を表すデータ構造。

    属性
        source: :class:`Path`
            問題を含む Markdown ファイルのパス。
        target: ``str``
            問題となったリンク文字列。
        reason: ``str``
            検出理由（ファイル欠如、アンカー未検出など）。
    """

    source: Path
    target: str
    reason: str


def normalise_anchor(text: str) -> str:
    """アンカー文字列を前後の空白除去だけで正規化します。

    入力
        text: ``str``
            アンカー候補文字列。
    出力
        ``str``
            トリム済み文字列。
    処理概要
        1. ``strip`` を呼び出し前後の空白を削除します。
    """

    return text.strip()


def collect_markdown_files() -> List[Path]:
    """ドキュメントルート直下の Markdown ファイル一覧を取得します。

    入力
        引数はありません。
    出力
        ``List[Path]``
            ファイル名でソートした Markdown パスのリスト。
    処理概要
        1. ``DOC_ROOT`` 直下の ``*.md`` を収集しソートします。
    """

    files = sorted(DOC_ROOT.glob("*.md"))
    return files


def collect_anchors(path: Path) -> Set[str]:
    """指定 Markdown 内のアンカー ID を収集します。

    入力
        path: :class:`Path`
            解析対象の Markdown ファイル。
    出力
        ``Set[str]``
            明示的な ``id`` 属性および見出しスラッグから生成したアンカー集合。
    処理概要
        1. HTML アンカー ``id`` を正規表現で抽出。
        2. 見出しテキストを GitHub 互換スラッグに変換し集合へ追加します。
    """

    text = path.read_text(encoding="utf-8")
    anchors: Set[str] = set()
    for match in ANCHOR_PATTERN.finditer(text):
        anchors.add(match.group(1))
    # Fall back to GitHub-style slug generation for headings without explicit anchors
    for heading in HEADING_PATTERN.findall(text):
        slug = (
            heading.lower()
            .strip()
            .replace("/", " ")
            .replace("(", "")
            .replace(")", "")
        )
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)
        slug = re.sub(r"\s+", "-", slug).strip("-")
        if slug:
            anchors.add(slug)
    return anchors


def split_link(raw_link: str) -> Tuple[str, str]:
    """Markdown リンク文字列をパスとアンカーに分割します。

    入力
        raw_link: ``str``
            ``[text](target#anchor)`` の ``target#anchor`` 部分。
    出力
        ``Tuple[str, str]``
            (パス, アンカー)。URL やメールリンクはアンカーを空文字で返します。
    処理概要
        1. http/mailto/self アンカーなどの特殊ケースを判定。
        2. ``#`` で分割し、アンカー部は :func:`normalise_anchor` を適用します。
    """

    if raw_link.startswith("http://") or raw_link.startswith("https://"):
        return raw_link, ""
    if raw_link.startswith("mailto:"):
        return raw_link, ""
    if raw_link.startswith("#"):
        return "", normalise_anchor(raw_link[1:])
    if "#" in raw_link:
        path, anchor = raw_link.split("#", 1)
        return path, normalise_anchor(anchor)
    return raw_link, ""


def check_links(files: Iterable[Path]) -> List[LinkIssue]:
    """Markdown リンクの整合性を検査します。

    入力
        files: ``Iterable[Path]``
            検査対象の Markdown ファイル群。
    出力
        ``List[LinkIssue]``
            問題が見つかったリンク情報のリスト。
    処理概要
        1. 事前に各ファイルのアンカー集合を構築。
        2. 各リンクを解析し、対象ファイルの存在とアンカーの有無を確認します。
    """

    anchors: Dict[Path, Set[str]] = {
        path: collect_anchors(path) for path in files
    }
    issues: List[LinkIssue] = []

    for source in files:
        text = source.read_text(encoding="utf-8")
        for match in LINK_PATTERN.finditer(text):
            raw_link = match.group(1).strip()
            if not raw_link or raw_link.startswith("http") or raw_link.startswith("mailto:"):
                continue
            target_path_str, anchor = split_link(raw_link)
            if target_path_str.startswith("http") or target_path_str.startswith("mailto:"):
                continue

            if target_path_str:
                target_path = (source.parent / target_path_str).resolve()
            else:
                target_path = source.resolve()

            if target_path.suffix == "":
                # Non-file anchor within same document
                target_path = source.resolve()

            if target_path.suffix and target_path.suffix != ".md":
                continue

            if not target_path.exists():
                issues.append(LinkIssue(source, raw_link, "target file missing"))
                continue

            if anchor:
                target_anchors = anchors.get(target_path, set())
                if anchor not in target_anchors:
                    issues.append(LinkIssue(source, raw_link, "anchor not found"))
    return issues


def generate_index(files: Iterable[Path]) -> Dict[str, List[str]]:
    """カテゴリ別に Markdown ファイルを整列したインデックスを生成します。

    入力
        files: ``Iterable[Path]``
            インデックス対象のファイル群。
    出力
        ``Dict[str, List[str]]``
            キー ``"A"`` ``"B"`` ``"C"`` ごとにファイル名リストを格納した辞書。
    処理概要
        1. ``EXPECTED_ORDER`` に従い存在するファイルを抽出。
        2. ファイル名の接頭辞でカテゴリを判定し辞書へ格納します。
    """

    ordered = [name for name in EXPECTED_ORDER if (DOC_ROOT / name).exists()]
    groups: Dict[str, List[str]] = {"A": [], "B": [], "C": []}
    for name in ordered:
        if name.startswith("A"):
            groups["A"].append(name)
        elif name.startswith("B"):
            groups["B"].append(name)
        elif name.startswith("C"):
            groups["C"].append(name)
    return groups


def write_index(groups: Dict[str, List[str]]) -> None:
    """インデックス情報を ``docs_index.json`` に書き出します。

    入力
        groups: ``Dict[str, List[str]]``
            :func:`generate_index` が返すカテゴリ別ファイル名辞書。
    出力
        ``None``
            ファイルへ書き込むのみです。
    処理概要
        1. ``json.dumps`` で整形し ``INDEX_PATH`` へ保存します。
    """

    INDEX_PATH.write_text(json.dumps(groups, indent=2) + "\n", encoding="utf-8")


def check_expected_files(markdown_files: Iterable[Path]) -> List[str]:
    """期待する Markdown ファイルの有無を検証します。

    入力
        markdown_files: ``Iterable[Path]``
            実際に存在する Markdown ファイル群。
    出力
        ``List[str]``
            欠落ファイルや余剰ファイルを説明するメッセージリスト。
    処理概要
        1. 実在ファイルの集合を作成。
        2. ``EXPECTED_ORDER`` と比較し不足・過剰をメッセージ化します。
    """

    actual_names = {path.name for path in markdown_files}
    missing = [name for name in EXPECTED_ORDER if name not in actual_names]
    orphaned = sorted(name for name in actual_names if name not in EXPECTED_ORDER)
    issues: List[str] = []
    if missing:
        issues.append("Missing files: " + ", ".join(missing))
    if orphaned:
        issues.append("Orphan files: " + ", ".join(orphaned))
    return issues


def ensure_logging_section() -> bool:
    """ロギング戦略ドキュメントに特定セクションがあるか確認します。

    入力
        引数はありません。
    出力
        ``bool``
            ``True``: セクションが存在。``False``: 欠如またはファイルなし。
    処理概要
        1. ``A06_Logging_Strategy.md`` を読み込み ``Monitoring & Telemetry`` を検索します。
    """

    path = DOC_ROOT / "A06_Logging_Strategy.md"
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    return "Monitoring & Telemetry" in text


def run_consistency_check(update_index: bool) -> int:
    """ドキュメント整合性チェックを実行し終了コードを返します。

    入力
        update_index: ``bool``
            ``True`` の場合は docs_index.json を更新します。
    出力
        ``int``
            正常終了は ``0``、何らかの問題を検出した場合は ``1``。
    処理概要
        1. Markdown 構造、リンク、必須セクションの順に検証。
        2. 問題があればレポートを表示し 1、なければ 0 を返します。
    """

    markdown_files = collect_markdown_files()
    doc_files: List[Path] = list(markdown_files)
    script_path = DOC_ROOT / "C23_Rebuild_Policies_Script.py"
    if script_path.exists():
        doc_files.append(script_path)
    report_lines: List[str] = []

    structure_issues = check_expected_files(doc_files)
    if structure_issues:
        report_lines.extend(structure_issues)

    link_issues = check_links(markdown_files)
    if link_issues:
        for issue in link_issues:
            rel_source = issue.source.relative_to(DOC_ROOT)
            report_lines.append(f"Broken link in {rel_source}: {issue.target} ({issue.reason})")

    if not ensure_logging_section():
        report_lines.append("A06_Logging_Strategy.md is missing the Monitoring & Telemetry section.")

    if update_index:
        groups = generate_index(doc_files)
        write_index(groups)

    if report_lines:
        print("Consistency check failed:")
        for line in report_lines:
            print(f"- {line}")
        return 1

    print("All documentation checks passed.")
    return 0


def parse_args() -> argparse.Namespace:
    """コマンドライン引数を解析します。

    入力
        引数はありません。
    出力
        :class:`argparse.Namespace`
            利用可能なフラグ ``check_consistency`` と ``write_index`` を含む解析結果。
    処理概要
        1. ``argparse.ArgumentParser`` を構築し、想定されるオプションを登録します。
    """

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check-consistency",
        action="store_true",
        help="Validate links, expected files, and logging merge status.",
    )
    parser.add_argument(
        "--write-index",
        action="store_true",
        help="Regenerate docs_index.json while performing checks.",
    )
    return parser.parse_args()


def main() -> None:
    """CLI エントリーポイント。整合性チェックを実行します。

    入力
        引数はありません。
    出力
        ``None``
            プロセス終了コードとして ``sys.exit`` を使用します。
    処理概要
        1. 引数を解析し ``--check-consistency`` が指定されているか確認します。
        2. 必要に応じて :func:`run_consistency_check` を実行し終了コードで終了します。
    """

    args = parse_args()
    if not args.check_consistency:
        print("No action specified. Use --check-consistency.")
        sys.exit(1)
    exit_code = run_consistency_check(update_index=args.write_index)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
