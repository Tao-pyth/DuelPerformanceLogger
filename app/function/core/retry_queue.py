"""Simple retry queue utilities for orchestrating retriable jobs.

本モジュールでは、アプリ内で発生するリトライ可能な処理を
共通化して扱うための :class:`RetryQueue` を提供します。設定値
``retry.max_attempts`` と ``retry.backoff_sec`` を参照しながら同一
ジョブの実行回数やバックオフ間隔を一貫させることができます。
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import time
from typing import Any, Callable, Mapping, MutableMapping

__all__ = ["RetryJobState", "RetryQueue"]

logger = logging.getLogger(__name__)


Status = str


@dataclass(slots=True)
class RetryJobState:
    """State container representing a queued retry job."""

    job_id: str
    description: str
    max_attempts: int
    backoff_seconds: float
    status: Status = "idle"
    attempts: int = 0
    last_error: str | None = None
    metadata: MutableMapping[str, Any] = field(default_factory=dict)

    def snapshot(self) -> dict[str, Any]:
        """Export the current state as a serialisable dictionary."""

        return {
            "job_id": self.job_id,
            "description": self.description,
            "status": self.status,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "last_error": self.last_error,
            "metadata": dict(self.metadata),
        }


class RetryQueue:
    """Coordinate retry attempts for jobs that may fail transiently."""

    def __init__(
        self,
        *,
        max_attempts: int = 3,
        backoff_seconds: float = 15.0,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        self._max_attempts = max(1, int(max_attempts or 1))
        self._backoff_seconds = float(backoff_seconds) if backoff_seconds is not None else 0.0
        if self._backoff_seconds < 0:
            self._backoff_seconds = 0.0
        self._sleep = sleep or time.sleep
        self._jobs: dict[str, RetryJobState] = {}

    @property
    def max_attempts(self) -> int:
        return self._max_attempts

    @property
    def backoff_seconds(self) -> float:
        return self._backoff_seconds

    def configure(self, *, max_attempts: int | None = None, backoff_seconds: float | None = None) -> None:
        """Update queue defaults."""

        if max_attempts is not None:
            self._max_attempts = max(1, int(max_attempts or 1))
        if backoff_seconds is not None:
            value = float(backoff_seconds)
            self._backoff_seconds = value if value >= 0 else 0.0

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any] | None) -> "RetryQueue":
        """Instantiate queue from configuration mapping."""

        mapping = mapping or {}
        try:
            max_attempts_raw = mapping.get("retry.max_attempts")
            backoff_raw = mapping.get("retry.backoff_sec")
        except AttributeError:
            max_attempts_raw = None
            backoff_raw = None

        def _coerce_int(value: Any, default: int) -> int:
            try:
                return int(value)
            except (TypeError, ValueError):
                return default

        def _coerce_float(value: Any, default: float) -> float:
            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        queue = cls(
            max_attempts=_coerce_int(max_attempts_raw, 3),
            backoff_seconds=_coerce_float(backoff_raw, 15.0),
        )
        return queue

    def state(self, job_id: str) -> RetryJobState | None:
        """Return the recorded state for *job_id* if present."""

        return self._jobs.get(job_id)

    def snapshot(self) -> dict[str, Any]:
        """Return snapshot of all known jobs."""

        return {job_id: state.snapshot() for job_id, state in self._jobs.items()}

    def reset(self, job_id: str) -> None:
        """Remove an existing job state."""

        self._jobs.pop(job_id, None)

    def run(
        self,
        job_id: str,
        func: Callable[[], Any],
        *,
        description: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        on_retry: Callable[[Exception, RetryJobState], None] | None = None,
        on_failure: Callable[[Exception, RetryJobState], None] | None = None,
        on_success: Callable[[Any, RetryJobState], None] | None = None,
        raise_on_failure: bool = True,
        max_attempts: int | None = None,
        backoff_seconds: float | None = None,
    ) -> Any:
        """Execute *func* with retries according to queue policy."""

        state = self._jobs.get(job_id)
        attempts_limit = max_attempts if max_attempts is not None else self._max_attempts
        attempts_limit = max(1, int(attempts_limit))
        backoff = backoff_seconds
        if backoff is None:
            backoff = self._backoff_seconds
        else:
            backoff = max(float(backoff), 0.0)
        if state is None:
            state = RetryJobState(
                job_id=job_id,
                description=description or job_id,
                max_attempts=attempts_limit,
                backoff_seconds=backoff,
            )
            self._jobs[job_id] = state
        else:
            state.description = description or state.description or job_id
            state.max_attempts = attempts_limit
            state.backoff_seconds = backoff

        state.metadata.update(dict(metadata or {}))
        state.status = "waiting"
        state.attempts = 0
        state.last_error = None

        result: Any = None

        for attempt in range(1, attempts_limit + 1):
            state.status = "running"
            state.attempts = attempt
            try:
                result = func()
            except Exception as exc:  # pragma: no cover - behaviour validated via unit tests
                state.last_error = str(exc)
                if attempt >= attempts_limit:
                    state.status = "failed"
                    if on_failure is not None:
                        try:
                            on_failure(exc, state)
                        except Exception:  # pragma: no cover - defensive
                            logger.exception("Retry failure callback raised", exc_info=True)
                    if raise_on_failure:
                        raise
                    return None
                state.status = "waiting"
                if on_retry is not None:
                    try:
                        on_retry(exc, state)
                    except Exception:  # pragma: no cover - defensive
                        logger.exception("Retry callback raised", exc_info=True)
                if backoff > 0:
                    self._sleep(backoff)
            else:
                state.status = "succeeded"
                state.last_error = None
                if on_success is not None:
                    try:
                        on_success(result, state)
                    except Exception:  # pragma: no cover - defensive
                        logger.exception("Retry success callback raised", exc_info=True)
                return result

        return result

