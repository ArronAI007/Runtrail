import json
import sqlite3
import threading
import uuid
from pathlib import Path

from runtrail.storage.base import BaseStore

_SCHEMA = """
CREATE TABLE IF NOT EXISTS results (
    trace_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    case_json TEXT NOT NULL,
    output_json TEXT NOT NULL,
    evaluation_json TEXT NOT NULL,
    steps_json TEXT NOT NULL,
    duration_ms REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS hitl_reviews (
    review_id TEXT PRIMARY KEY,
    case_json TEXT NOT NULL,
    output_json TEXT NOT NULL,
    evaluation_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hitl_annotations (
    review_id TEXT PRIMARY KEY,
    annotation_json TEXT NOT NULL
);
"""


class SQLiteStore(BaseStore):
    """Zero-config local store; the default backend for development.

    Safe to share across threads (e.g. TaskQueue-driven concurrent runs, or
    the Web UI's thread-pooled request handlers): the connection is opened
    with check_same_thread=False and all access goes through a single lock.
    """

    def __init__(self, path: str | Path = "runtrail.db"):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

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
        with self._lock:
            self._conn.execute(
                "INSERT INTO results "
                "(trace_id, run_id, case_json, output_json, evaluation_json, steps_json, duration_ms) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    trace_id or str(uuid.uuid4()),
                    run_id,
                    json.dumps(case),
                    json.dumps(output),
                    json.dumps(evaluation),
                    json.dumps(steps or []),
                    duration_ms or 0.0,
                ),
            )
            self._conn.commit()

    def load_run(self, run_id: str) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT trace_id, case_json, output_json, evaluation_json, steps_json, duration_ms "
                "FROM results WHERE run_id = ?",
                (run_id,),
            ).fetchall()
        return [_row_to_trace_dict(run_id, row) for row in rows]

    def load_trace(self, trace_id: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT run_id, case_json, output_json, evaluation_json, steps_json, duration_ms "
                "FROM results WHERE trace_id = ?",
                (trace_id,),
            ).fetchone()
        if row is None:
            return None
        run_id, *rest = row
        return _row_to_trace_dict(run_id, (trace_id, *rest))

    def list_runs(self) -> list[dict]:
        with self._lock:
            rows = self._conn.execute("SELECT run_id, evaluation_json FROM results").fetchall()
        return _aggregate_by_run(rows)

    def overall_stats(self) -> dict:
        with self._lock:
            rows = self._conn.execute(
                "SELECT evaluation_json, steps_json, duration_ms FROM results"
            ).fetchall()
        return _aggregate_stats(rows)

    def enqueue_review(self, case: dict, output: dict, evaluation: dict) -> str:
        review_id = str(uuid.uuid4())
        with self._lock:
            self._conn.execute(
                "INSERT INTO hitl_reviews (review_id, case_json, output_json, evaluation_json) "
                "VALUES (?, ?, ?, ?)",
                (review_id, json.dumps(case), json.dumps(output), json.dumps(evaluation)),
            )
            self._conn.commit()
        return review_id

    def list_pending_reviews(self) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT r.review_id, r.case_json, r.output_json, r.evaluation_json "
                "FROM hitl_reviews r "
                "LEFT JOIN hitl_annotations a ON a.review_id = r.review_id "
                "WHERE a.review_id IS NULL"
            ).fetchall()
        return [
            {
                "review_id": review_id,
                "case": json.loads(c),
                "output": json.loads(o),
                "evaluation": json.loads(e),
            }
            for review_id, c, o, e in rows
        ]

    def record_annotation(self, review_id: str, annotation: dict) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO hitl_annotations (review_id, annotation_json) VALUES (?, ?)",
                (review_id, json.dumps(annotation)),
            )
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()


def _row_to_trace_dict(run_id: str, row: tuple) -> dict:
    trace_id, c, o, e, s, duration_ms = row
    return {
        "trace_id": trace_id,
        "run_id": run_id,
        "case": json.loads(c),
        "output": json.loads(o),
        "evaluation": json.loads(e),
        "steps": json.loads(s),
        "duration_ms": duration_ms,
    }


def _aggregate_by_run(rows: list[tuple]) -> list[dict]:
    stats: dict[str, dict] = {}
    for run_id, eval_json in rows:
        entry = stats.setdefault(run_id, {"total": 0, "passed": 0})
        entry["total"] += 1
        if json.loads(eval_json).get("passed"):
            entry["passed"] += 1
    return [
        {
            "run_id": run_id,
            "total": s["total"],
            "passed": s["passed"],
            "pass_rate": s["passed"] / s["total"] if s["total"] else 0.0,
        }
        for run_id, s in stats.items()
    ]


def _aggregate_stats(rows: list[tuple]) -> dict:
    total = len(rows)
    passed = 0
    total_duration = 0.0
    total_steps = 0
    failure_category_counts: dict[str, int] = {}
    for eval_json, steps_json, duration_ms in rows:
        evaluation = json.loads(eval_json)
        if evaluation.get("passed"):
            passed += 1
        category = evaluation.get("failure_category")
        if category is not None:
            failure_category_counts[category] = failure_category_counts.get(category, 0) + 1
        total_duration += duration_ms or 0.0
        total_steps += len(json.loads(steps_json) or [])
    return {
        "total": total,
        "passed": passed,
        "pass_rate": passed / total if total else 0.0,
        "avg_duration_ms": total_duration / total if total else 0.0,
        "avg_steps": total_steps / total if total else 0.0,
        "failure_category_counts": failure_category_counts,
    }
