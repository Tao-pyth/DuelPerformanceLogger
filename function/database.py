"""High-level helper around the SQLite database used by the app.

The application stores user generated data – such as registered decks,
season notes and detailed match logs – inside a single SQLite file located
under :mod:`resource/db`.  This module concentrates all access to that file
so that the rest of the UI can stay focused on presentation logic.

The manager intentionally exposes simple dictionary based structures instead
of raw SQLite rows.  That keeps the calling code free from persistence
details while still allowing the UI to display the stored information.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Optional


class DatabaseError(RuntimeError):
    """Base error that signals an unexpected database failure."""


class DuplicateEntryError(DatabaseError):
    """Raised when a unique constraint prevents inserting a record."""


class DatabaseManager:
    """Utility wrapper around an on-disk SQLite database file.

    Parameters
    ----------
    db_path:
        Optional custom path to the SQLite database file.  When omitted the
        database is placed inside ``resource/db`` with the default file name
        ``duel_performance.sqlite3``.
    """

    def __init__(self, db_path: Optional[Path | str] = None) -> None:
        base_dir = Path(__file__).resolve().parent.parent / "resource" / "db"
        if db_path is None:
            db_path = base_dir / "duel_performance.sqlite3"
        else:
            db_path = Path(db_path)
            if db_path.is_dir():
                # Allow callers to pass only the directory and rely on the
                # default file name.
                db_path = db_path / "duel_performance.sqlite3"

        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Low level helpers
    # ------------------------------------------------------------------
    def _connect(self) -> sqlite3.Connection:
        """Return a SQLite connection with sensible defaults.

        Each connection enables foreign key constraints and configures the
        row factory so results can be accessed as dictionaries.
        """

        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON;")
        return connection

    # ------------------------------------------------------------------
    # Database lifecycle helpers
    # ------------------------------------------------------------------
    @property
    def db_path(self) -> Path:
        """Expose the current database file path for informational purposes."""

        return self._db_path

    def ensure_database(self) -> None:
        """Create the database file with all tables when it does not exist."""

        if not self._db_path.exists():
            self.initialize_database()

    def initialize_database(self) -> None:
        """Re-create the database file from scratch.

        Existing files are removed before the new empty schema is created.  The
        method is idempotent and can safely be called multiple times.
        """

        if self._db_path.exists():
            self._db_path.unlink()

        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self._db_path) as connection:
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys = ON;")
            cursor.executescript(
                """
                CREATE TABLE decks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT DEFAULT ''
                );

                CREATE TABLE seasons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT DEFAULT ''
                );

                CREATE TABLE matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_no INTEGER NOT NULL,
                    deck_name TEXT NOT NULL,
                    turn TEXT NOT NULL CHECK (turn IN ('first', 'second')),
                    opponent_deck TEXT,
                    keywords TEXT,
                    result TEXT NOT NULL CHECK (result IN ('win', 'lose', 'draw')),
                    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
                );

                CREATE INDEX idx_matches_deck_created_at
                    ON matches(deck_name, created_at DESC);

                CREATE INDEX idx_matches_match_no
                    ON matches(match_no);
                """
            )

    # ------------------------------------------------------------------
    # Data retrieval helpers
    # ------------------------------------------------------------------
    def fetch_decks(self) -> list[dict[str, str]]:
        """Return all registered decks sorted by name."""

        with self._connect() as connection:
            cursor = connection.execute(
                "SELECT name, description FROM decks ORDER BY name COLLATE NOCASE"
            )
            return [dict(row) for row in cursor.fetchall()]

    def fetch_seasons(self) -> list[dict[str, str]]:
        """Return the stored season definitions sorted by name."""

        with self._connect() as connection:
            cursor = connection.execute(
                "SELECT name, description FROM seasons ORDER BY name COLLATE NOCASE"
            )
            return [dict(row) for row in cursor.fetchall()]

    def fetch_matches(self, deck_name: Optional[str] = None) -> list[dict[str, object]]:
        """Return stored match logs.

        Parameters
        ----------
        deck_name:
            When provided, only matches for the specified deck are returned.
        """

        query = (
            "SELECT match_no, deck_name, turn, opponent_deck, keywords, result, created_at"
            " FROM matches"
        )
        params: Iterable[object] = ()
        if deck_name:
            query += " WHERE deck_name = ?"
            params = (deck_name,)

        query += " ORDER BY created_at ASC, id ASC"

        with self._connect() as connection:
            cursor = connection.execute(query, tuple(params))
            records: list[dict[str, object]] = []
            for row in cursor.fetchall():
                # Keywords are stored as JSON for simplicity.
                keywords_raw = row["keywords"]
                keywords = json.loads(keywords_raw) if keywords_raw else []
                created_at_raw = row["created_at"]
                created_at = self._format_timestamp(created_at_raw)
                record = {
                    "match_no": row["match_no"],
                    "deck_name": row["deck_name"],
                    "turn": row["turn"],
                    "opponent_deck": row["opponent_deck"] or "",
                    "keywords": keywords,
                    "result": row["result"],
                    "created_at": created_at,
                }
                records.append(record)
            return records

    def fetch_last_match(self, deck_name: Optional[str] = None) -> Optional[dict[str, object]]:
        """Return the most recently recorded match.

        When *deck_name* is supplied the search is scoped to that deck.
        """

        query = (
            "SELECT match_no, deck_name, turn, opponent_deck, keywords, result, created_at"
            " FROM matches"
        )
        params: Iterable[object] = ()
        if deck_name:
            query += " WHERE deck_name = ?"
            params = (deck_name,)

        query += " ORDER BY created_at DESC, id DESC LIMIT 1"

        with self._connect() as connection:
            cursor = connection.execute(query, tuple(params))
            row = cursor.fetchone()
            if row is None:
                return None

            keywords_raw = row["keywords"]
            keywords = json.loads(keywords_raw) if keywords_raw else []
            created_at_raw = row["created_at"]
            created_at = self._format_timestamp(created_at_raw)
            return {
                "match_no": row["match_no"],
                "deck_name": row["deck_name"],
                "turn": row["turn"],
                "opponent_deck": row["opponent_deck"] or "",
                "keywords": keywords,
                "result": row["result"],
                "created_at": created_at,
            }

    def get_next_match_number(self, deck_name: Optional[str] = None) -> int:
        """Return the next match number for the given deck.

        The helper inspects the latest match entry and adds one to its
        ``match_no``.  When the database is empty the value ``1`` is returned.
        """

        last_match = self.fetch_last_match(deck_name)
        if last_match is None:
            return 1
        last_no = last_match.get("match_no")
        try:
            return int(last_no) + 1
        except (TypeError, ValueError):
            # When the value was stored as text and is not numeric we fall
            # back to a safe default.
            return 1

    # ------------------------------------------------------------------
    # Data mutation helpers
    # ------------------------------------------------------------------
    def add_deck(self, name: str, description: str = "") -> None:
        """Insert a new deck definition."""

        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO decks (name, description) VALUES (?, ?)",
                    (name, description),
                )
        except sqlite3.IntegrityError as exc:  # pragma: no cover - defensive
            raise DuplicateEntryError(f"Deck '{name}' already exists") from exc
        except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive
            raise DatabaseError("Failed to insert deck") from exc

    def add_season(self, name: str, description: str = "") -> None:
        """Insert a season definition."""

        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO seasons (name, description) VALUES (?, ?)",
                    (name, description),
                )
        except sqlite3.IntegrityError as exc:  # pragma: no cover - defensive
            raise DuplicateEntryError(f"Season '{name}' already exists") from exc
        except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive
            raise DatabaseError("Failed to insert season") from exc

    def record_match(self, record: dict[str, object]) -> None:
        """Persist a match record.

        ``record`` must at least contain the keys ``match_no``, ``deck_name``,
        ``turn`` and ``result``.  Optional keys such as ``opponent_deck`` and
        ``keywords`` are stored when present.
        """

        keywords = record.get("keywords") or []
        keywords_json = json.dumps(list(keywords), ensure_ascii=False)

        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO matches (
                        match_no, deck_name, turn, opponent_deck, keywords, result
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.get("match_no", 0),
                        record["deck_name"],
                        record["turn"],
                        record.get("opponent_deck", ""),
                        keywords_json,
                        record["result"],
                    ),
                )
        except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive
            raise DatabaseError("Failed to record match") from exc

    # ------------------------------------------------------------------
    # Advanced helpers
    # ------------------------------------------------------------------
    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Provide a managed database transaction.

        This utility ensures that the wrapped block runs within a single
        transaction.  Any error causes the transaction to roll back while
        successful execution commits automatically.
        """

        connection = self._connect()
        try:
            yield connection
            connection.commit()
        except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive
            connection.rollback()
            raise DatabaseError("Database transaction failed") from exc
        finally:
            connection.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _format_timestamp(value: object) -> str:
        """Convert a SQLite timestamp value into an ISO formatted string."""

        try:
            timestamp = int(value)
        except (TypeError, ValueError):
            return ""

        return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
