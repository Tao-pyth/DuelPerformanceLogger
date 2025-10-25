"""CSV schema definitions used during backup restoration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Sequence

__all__ = [
    "ColumnType",
    "ColumnSpec",
    "TableSchema",
    "CSV_TABLE_ORDER",
    "CSV_DELETE_ORDER",
    "SCHEMA_BY_TABLE",
]


class ColumnType(str, Enum):
    """Column type identifiers supported by the restore pipeline."""

    TEXT = "text"
    INTEGER = "int"
    BOOLEAN = "bool"
    JSON = "json"
    EPOCH = "epoch"
    TURN = "turn"
    RESULT = "result"


@dataclass(frozen=True)
class ColumnSpec:
    """Schema metadata for a single CSV column."""

    name: str
    type: ColumnType
    nullable: bool = True
    default: object | None = None


@dataclass(frozen=True)
class TableSchema:
    """Schema definition for a single table."""

    name: str
    columns: Mapping[str, ColumnSpec]
    primary_key: str | None = None

    def optional_columns(self) -> Sequence[str]:
        return tuple(name for name, spec in self.columns.items() if spec.nullable)


CSV_TABLE_ORDER: tuple[str, ...] = ("decks", "opponent_decks", "seasons", "matches")
"""Order in which CSV files should be imported to satisfy dependencies."""

CSV_DELETE_ORDER: tuple[str, ...] = tuple(reversed(CSV_TABLE_ORDER))
"""Order in which tables should be cleared when performing a full restore."""


SCHEMA_BY_TABLE: Mapping[str, TableSchema] = {
    "decks": TableSchema(
        name="decks",
        primary_key="id",
        columns={
            "id": ColumnSpec("id", ColumnType.INTEGER),
            "name": ColumnSpec("name", ColumnType.TEXT, nullable=False),
            "description": ColumnSpec("description", ColumnType.TEXT),
            "usage_count": ColumnSpec(
                "usage_count", ColumnType.INTEGER, nullable=False, default=0
            ),
        },
    ),
    "opponent_decks": TableSchema(
        name="opponent_decks",
        primary_key="id",
        columns={
            "id": ColumnSpec("id", ColumnType.INTEGER),
            "name": ColumnSpec("name", ColumnType.TEXT, nullable=False),
            "usage_count": ColumnSpec(
                "usage_count", ColumnType.INTEGER, nullable=False, default=0
            ),
        },
    ),
    "seasons": TableSchema(
        name="seasons",
        primary_key="id",
        columns={
            "id": ColumnSpec("id", ColumnType.INTEGER),
            "name": ColumnSpec("name", ColumnType.TEXT, nullable=False),
            "description": ColumnSpec("description", ColumnType.TEXT),
            "start_date": ColumnSpec("start_date", ColumnType.TEXT),
            "start_time": ColumnSpec("start_time", ColumnType.TEXT),
            "end_date": ColumnSpec("end_date", ColumnType.TEXT),
            "end_time": ColumnSpec("end_time", ColumnType.TEXT),
            "rank_statistics_target": ColumnSpec(
                "rank_statistics_target", ColumnType.BOOLEAN, nullable=False, default=0
            ),
        },
    ),
    "matches": TableSchema(
        name="matches",
        primary_key="id",
        columns={
            "id": ColumnSpec("id", ColumnType.INTEGER),
            "match_no": ColumnSpec("match_no", ColumnType.INTEGER, nullable=False),
            "deck_id": ColumnSpec("deck_id", ColumnType.INTEGER, nullable=False),
            "season_id": ColumnSpec("season_id", ColumnType.INTEGER),
            "turn": ColumnSpec("turn", ColumnType.TURN, nullable=False),
            "opponent_deck": ColumnSpec("opponent_deck", ColumnType.TEXT),
            "keywords": ColumnSpec(
                "keywords", ColumnType.JSON, default="[]"
            ),
            "memo": ColumnSpec("memo", ColumnType.TEXT, nullable=False, default=""),
            "result": ColumnSpec("result", ColumnType.RESULT, nullable=False),
            "youtube_url": ColumnSpec("youtube_url", ColumnType.TEXT),
            "favorite": ColumnSpec(
                "favorite", ColumnType.BOOLEAN, nullable=False, default=0
            ),
            "created_at": ColumnSpec("created_at", ColumnType.EPOCH, nullable=False),
        },
    ),
}
