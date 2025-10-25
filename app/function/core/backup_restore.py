"""Robust CSV restoration utilities for DuelPerformanceLogger."""

from __future__ import annotations

import csv
import io
import json
import sqlite3
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterable, Sequence

from . import paths
from .csv_schema_map import (
    ColumnSpec,
    ColumnType,
    TableSchema,
    CSV_DELETE_ORDER,
    CSV_TABLE_ORDER,
    SCHEMA_BY_TABLE,
)

__all__ = [
    "RestoreFailure",
    "RestoreReport",
    "RestoreError",
    "restore_from_directory",
    "restore_from_zip",
    "restore_from_zip_bytes",
]


@dataclass(slots=True)
class RestoreFailure:
    """Details about a single failed record during restoration."""

    table: str
    row_number: int
    column: str | None
    value: str | None
    reason: str


@dataclass(slots=True)
class RestoreReport:
    """Outcome of a restore operation."""

    mode: str
    dry_run: bool
    restored: dict[str, int] = field(default_factory=dict)
    failures: list[RestoreFailure] = field(default_factory=list)
    error: str | None = None
    log_path: Path | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    integrity_ok: bool = False

    @property
    def ok(self) -> bool:
        return self.error is None and not self.failures and self.integrity_ok


class RestoreError(RuntimeError):
    """Raised when a critical error occurs during restoration."""

    def __init__(self, message: str, failures: Iterable[RestoreFailure] | None = None):
        super().__init__(message)
        self.failures = list(failures or [])


_TRUTHY = {"1", "true", "yes", "on"}
_FALSEY = {"0", "false", "no", "off"}


def restore_from_directory(
    database_path: Path | str,
    source_directory: Path | str,
    *,
    mode: str = "full",
    dry_run: bool = False,
) -> RestoreReport:
    """Restore database content from a directory containing CSV backups."""

    database_path = Path(database_path)
    source_directory = Path(source_directory)

    if mode not in {"full", "upsert"}:
        raise ValueError("mode must be 'full' or 'upsert'")
    if not source_directory.exists():
        raise FileNotFoundError(source_directory)

    report = RestoreReport(mode=mode, dry_run=dry_run)

    connection = sqlite3.connect(database_path)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute("BEGIN IMMEDIATE")

        if mode == "full":
            _clear_tables(connection)

        for table in CSV_TABLE_ORDER:
            schema = SCHEMA_BY_TABLE.get(table)
            csv_path = source_directory / f"{table}.csv"
            if not schema or not csv_path.exists():
                report.restored[table] = 0
                continue

            try:
                inserted = _restore_table(connection, schema, csv_path, mode)
            except RestoreError:
                report.restored.setdefault(table, 0)
                raise
            report.restored[table] = inserted

        report.integrity_ok = _run_integrity_check(connection)
        if not report.integrity_ok:
            raise RestoreError("PRAGMA integrity_check failed", [])

        if dry_run:
            connection.execute("ROLLBACK")
        else:
            connection.execute("COMMIT")
    except RestoreError as exc:
        connection.execute("ROLLBACK")
        report.failures.extend(exc.failures)
        report.error = str(exc)
    except Exception as exc:  # pragma: no cover - defensive
        connection.execute("ROLLBACK")
        report.error = str(exc)
    finally:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.close()

    report.finished_at = datetime.now(timezone.utc)
    report.log_path = _write_report(report)
    return report


def restore_from_zip(
    database_path: Path | str,
    zip_path: Path | str,
    *,
    mode: str = "full",
    dry_run: bool = False,
) -> RestoreReport:
    """Restore database content from a backup ZIP archive."""

    zip_path = Path(zip_path)
    if not zip_path.exists():
        raise FileNotFoundError(zip_path)

    with TemporaryDirectory() as temp_dir:
        try:
            with zipfile.ZipFile(zip_path) as archive:
                _extract_required_members(archive, Path(temp_dir))
        except RestoreError as exc:
            report = RestoreReport(mode=mode, dry_run=dry_run)
            report.failures.extend(exc.failures)
            report.error = str(exc)
            report.finished_at = datetime.now(timezone.utc)
            report.log_path = _write_report(report)
            return report
        return restore_from_directory(database_path, temp_dir, mode=mode, dry_run=dry_run)


def restore_from_zip_bytes(
    database_path: Path | str,
    payload: bytes,
    *,
    mode: str = "full",
    dry_run: bool = False,
) -> RestoreReport:
    """Restore database content from ZIP bytes."""

    if not payload:
        raise ValueError("payload must not be empty")

    with TemporaryDirectory() as temp_dir:
        try:
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                _extract_required_members(archive, Path(temp_dir))
        except RestoreError as exc:
            report = RestoreReport(mode=mode, dry_run=dry_run)
            report.failures.extend(exc.failures)
            report.error = str(exc)
            report.finished_at = datetime.now(timezone.utc)
            report.log_path = _write_report(report)
            return report
        return restore_from_directory(database_path, temp_dir, mode=mode, dry_run=dry_run)


def _extract_required_members(archive: zipfile.ZipFile, destination: Path) -> None:
    expected = {f"{table}.csv" for table in CSV_TABLE_ORDER}
    required = {"decks.csv", "seasons.csv", "matches.csv"}
    members = [info for info in archive.infolist() if not info.is_dir()]
    found = {Path(info.filename).name for info in members if info.filename}
    missing = required - found
    if missing:
        raise RestoreError(
            "Backup archive is missing required files",
            [
                RestoreFailure(
                    table="archive",
                    row_number=0,
                    column=None,
                    value=", ".join(sorted(missing)),
                    reason="missing_csv",
                )
            ],
        )

    for info in members:
        name = Path(info.filename).name
        if name not in expected:
            continue
        target = destination / name
        with archive.open(info) as src, target.open("wb") as dst:
            dst.write(src.read())


def _clear_tables(connection: sqlite3.Connection) -> None:
    for table in CSV_DELETE_ORDER:
        connection.execute(f"DELETE FROM {table}")
        try:
            connection.execute("DELETE FROM sqlite_sequence WHERE name = ?", (table,))
        except sqlite3.DatabaseError:
            continue


def _restore_table(
    connection: sqlite3.Connection,
    table_schema: TableSchema,
    csv_path: Path,
    mode: str,
) -> int:
    columns = table_schema.columns

    with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise RestoreError(
                f"CSV file '{csv_path.name}' is missing a header",
                [
                    RestoreFailure(
                        table=table_schema.name,
                        row_number=1,
                        column=None,
                        value=None,
                        reason="missing_header",
                    )
                ],
            )

        available_columns = [name for name in reader.fieldnames if name in columns]
        if not available_columns:
            raise RestoreError(
                f"CSV file '{csv_path.name}' contains no known columns",
                [
                    RestoreFailure(
                        table=table_schema.name,
                        row_number=1,
                        column=None,
                        value=", ".join(reader.fieldnames),
                        reason="unknown_columns",
                    )
                ],
            )

        _ensure_required_columns(table_schema.name, columns, available_columns)

        statement = _build_insert_statement(table_schema.name, available_columns, mode)
        inserted = 0

        for row_number, raw_row in enumerate(reader, start=2):
            if not raw_row or all((value or "").strip() == "" for value in raw_row.values()):
                continue

            converted: list[object] = []
            for column in available_columns:
                spec = columns[column]
                try:
                    converted.append(_convert_value(raw_row.get(column), spec))
                except ValueError as exc:
                    raise RestoreError(
                        f"Invalid value for column '{column}'",
                        [
                            RestoreFailure(
                                table=table_schema.name,
                                row_number=row_number,
                                column=column,
                                value=(raw_row.get(column) or ""),
                                reason=str(exc),
                            )
                        ],
                    ) from exc

            try:
                connection.execute(statement, converted)
            except sqlite3.DatabaseError as exc:
                raise RestoreError(
                    f"SQLite rejected row {row_number} during restore",
                    [
                        RestoreFailure(
                            table=table_schema.name,
                            row_number=row_number,
                            column=None,
                            value=json.dumps(raw_row, ensure_ascii=False),
                            reason=str(exc),
                        )
                    ],
                ) from exc

            inserted += 1

    return inserted


def _ensure_required_columns(
    table: str,
    columns: dict[str, ColumnSpec],
    available: Sequence[str],
) -> None:
    missing = [
        name
        for name, spec in columns.items()
        if not spec.nullable and name not in available and spec.default is None
    ]
    if missing:
        raise RestoreError(
            f"CSV file for '{table}' is missing required columns",
            [
                RestoreFailure(
                    table=table,
                    row_number=1,
                    column=None,
                    value=", ".join(sorted(missing)),
                    reason="missing_columns",
                )
            ],
        )


def _build_insert_statement(table: str, columns: Sequence[str], mode: str) -> str:
    placeholders = ", ".join(["?"] * len(columns))
    column_list = ", ".join(columns)
    verb = "INSERT OR REPLACE" if mode == "upsert" else "INSERT"
    return f"{verb} INTO {table} ({column_list}) VALUES ({placeholders})"


def _convert_value(raw_value: str | None, spec: ColumnSpec) -> object:
    text_value = "" if raw_value is None else str(raw_value)
    normalized = text_value.strip()

    if not normalized:
        if spec.default is not None:
            return spec.default
        if spec.nullable:
            return None

    if spec.type == ColumnType.TEXT:
        return text_value

    if spec.type == ColumnType.JSON:
        candidate = text_value if normalized else (spec.default or "[]")
        try:
            parsed = json.loads(candidate) if candidate else []
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON: {exc.msg}") from exc
        return json.dumps(parsed, ensure_ascii=False, separators=(",", ":"))

    if spec.type == ColumnType.INTEGER:
        if not normalized:
            raise ValueError("integer value required")
        try:
            return int(float(normalized))
        except ValueError as exc:
            raise ValueError(f"invalid integer: {normalized}") from exc

    if spec.type == ColumnType.BOOLEAN:
        if not normalized:
            return int(spec.default or 0)
        lowered = normalized.lower()
        if lowered in _TRUTHY:
            return 1
        if lowered in _FALSEY:
            return 0
        raise ValueError(f"invalid boolean: {text_value}")

    if spec.type == ColumnType.EPOCH:
        if not normalized:
            raise ValueError("epoch timestamp required")
        try:
            return int(float(normalized))
        except ValueError as exc:
            raise ValueError(f"invalid epoch: {normalized}") from exc

    if spec.type == ColumnType.TURN:
        return _convert_turn(normalized or text_value)

    if spec.type == ColumnType.RESULT:
        return _convert_result(normalized or text_value)

    raise ValueError(f"Unsupported column type: {spec.type}")


def _convert_turn(value: str) -> int:
    lowered = value.strip().lower()
    if lowered in {"1", "true", "first", "先攻"}:
        return 1
    if lowered in {"0", "false", "second", "後攻"}:
        return 0
    raise ValueError(f"invalid turn value: {value}")


def _convert_result(value: str) -> int:
    lowered = value.strip().lower()
    mapping = {
        "1": 1,
        "win": 1,
        "victory": 1,
        "勝ち": 1,
        "-1": -1,
        "lose": -1,
        "loss": -1,
        "敗北": -1,
        "0": 0,
        "draw": 0,
        "引き分け": 0,
    }
    if lowered in mapping:
        return mapping[lowered]
    raise ValueError(f"invalid result value: {value}")


def _run_integrity_check(connection: sqlite3.Connection) -> bool:
    try:
        row = connection.execute("PRAGMA integrity_check").fetchone()
    except sqlite3.DatabaseError:
        return False
    return bool(row and row[0] == "ok")


def _write_report(report: RestoreReport) -> Path:
    timestamp = report.finished_at or datetime.now(timezone.utc)
    log_path = paths.log_dir() / f"restore-{timestamp.strftime('%Y%m%d-%H%M%S')}.log"

    lines = [
        f"mode: {report.mode}",
        f"dry_run: {report.dry_run}",
        f"integrity_ok: {report.integrity_ok}",
        f"error: {report.error or ''}",
        "counts:",
    ]
    for table in CSV_TABLE_ORDER:
        lines.append(f"  {table}: {report.restored.get(table, 0)}")

    if report.failures:
        lines.append("failures:")
        for failure in report.failures:
            lines.append(
                f"  - table={failure.table} row={failure.row_number} "
                f"column={failure.column or ''} reason={failure.reason}"
            )
            if failure.value:
                lines.append(f"    value={failure.value}")

    log_path.write_text("\n".join(lines), encoding="utf-8")
    return log_path
