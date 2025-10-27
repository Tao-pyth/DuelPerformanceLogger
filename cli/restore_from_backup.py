"""Command line interface for restoring DuelPerformanceLogger backups."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.function import DatabaseError, DatabaseManager


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Restore a DuelPerformanceLogger database from a backup archive.",
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to the backup ZIP archive exported by the application.",
    )
    parser.add_argument(
        "--mode",
        choices=("full", "upsert"),
        default="full",
        help="Restore mode. 'full' clears existing data, 'upsert' merges records.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the archive without committing changes.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    archive_path = Path(args.input)
    if not archive_path.exists():
        parser.error(f"Backup file '{archive_path}' does not exist")

    manager = DatabaseManager()
    manager.ensure_database()

    try:
        payload = archive_path.read_bytes()
    except OSError as exc:  # pragma: no cover - filesystem error
        parser.error(f"Failed to read backup file: {exc}")
        return 2

    try:
        report = manager.import_backup_archive(
            payload, mode=args.mode, dry_run=args.dry_run
        )
    except DatabaseError as exc:
        print(f"Restore failed: {exc}", file=sys.stderr)
        last_report = manager.last_restore_report
        if last_report and last_report.log_path:
            print(f"See log: {last_report.log_path}", file=sys.stderr)
        return 1

    print("Restore completed successfully." if not args.dry_run else "Dry-run completed.")
    for table in sorted(report.restored):
        print(f"  {table}: {report.restored[table]}")
    print(f"Failures recorded: {len(report.failures)}")
    if report.log_path:
        print(f"Log file: {report.log_path}")
    if args.dry_run:
        print("No changes were committed to the database.")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())
