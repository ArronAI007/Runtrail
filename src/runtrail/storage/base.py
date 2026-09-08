from abc import ABC, abstractmethod
from typing import Self


class BaseStore(ABC):
    """Interface every Store (SQLite / Postgres) implements for persisting run
    results, per-trace lookup, run/aggregate stats, and the HITL review queue.
    """

    @abstractmethod
    def save_result(
        self,
        run_id: str,
        case: dict,
        output: dict,
        evaluation: dict,
        *,
        trace_id: str | None = None,
        steps: list[dict] | None = None,
        duration_ms: float | None = None,
    ) -> None:
        ...

    @abstractmethod
    def load_run(self, run_id: str) -> list[dict]:
        ...

    @abstractmethod
    def load_trace(self, trace_id: str) -> dict | None:
        """Look up one case's full execution record by its trace_id."""

    @abstractmethod
    def list_runs(self) -> list[dict]:
        """List every run_id seen, with its case/pass counts — the Web UI's task list."""

    @abstractmethod
    def overall_stats(self) -> dict:
        """Aggregate pass rate, avg duration/steps, and failure_category counts
        across every stored result — the Web UI dashboard's data source.
        """

    @abstractmethod
    def enqueue_review(self, case: dict, output: dict, evaluation: dict) -> str:
        """Queue one case for human review and return its review_id."""

    @abstractmethod
    def list_pending_reviews(self) -> list[dict]:
        """List reviews that have not yet been annotated."""

    @abstractmethod
    def record_annotation(self, review_id: str, annotation: dict) -> None:
        """Attach a human annotation to a queued review, marking it reviewed."""

    @abstractmethod
    def close(self) -> None:
        """Release the underlying connection. Also usable as a context manager."""

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
