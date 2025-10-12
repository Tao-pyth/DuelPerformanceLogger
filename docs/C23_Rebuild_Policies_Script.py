#!/usr/bin/env python3
"""Documentation consistency utilities for Duel Performance Logger."""
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
    source: Path
    target: str
    reason: str


def normalise_anchor(text: str) -> str:
    return text.strip()


def collect_markdown_files() -> List[Path]:
    files = sorted(DOC_ROOT.glob("*.md"))
    return files


def collect_anchors(path: Path) -> Set[str]:
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
    INDEX_PATH.write_text(json.dumps(groups, indent=2) + "\n", encoding="utf-8")


def check_expected_files(markdown_files: Iterable[Path]) -> List[str]:
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
    path = DOC_ROOT / "A06_Logging_Strategy.md"
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    return "Monitoring & Telemetry" in text


def run_consistency_check(update_index: bool) -> int:
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
    args = parse_args()
    if not args.check_consistency:
        print("No action specified. Use --check-consistency.")
        sys.exit(1)
    exit_code = run_consistency_check(update_index=args.write_index)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
