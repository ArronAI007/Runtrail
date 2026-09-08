import json
import uuid

from runtrail.storage.base import BaseStore

_SCHEMA = """
CREATE TABLE IF NOT EXISTS results (
    trace_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    case_json JSONB NOT NULL,
    output_json JSONB NOT NULL,
    evaluation_json JSONB NOT NULL,
    steps_json JSONB NOT NULL,
    duration_ms DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS hitl_reviews (
    review_id TEXT PRIMARY KEY,
    case_json JSONB NOT NULL,
    output_json JSONB NOT NULL,
    evaluation_json JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS hitl_annotations (
    review_id TEXT PRIMARY KEY,
    annotation_json JSONB NOT NULL
);
"""


class PostgresStore(BaseStore):
    """Production store backed by PostgreSQL. Requires the 'postgres' extra:
    pip install 'runtrail[postgres]'.
    """

    def __init__(self, dsn: str):
        self.dsn = dsn
        self._conn = self._connect()
        with self._conn.cursor() as cur:
            cur.execute(_SCHEMA)
        self._conn.commit()

    def _connect(self):
        try:
            import psycopg
        except ImportError as exc:
            raise ImportError(
                "PostgresStore requires the 'postgres' extra: pip install 'runtrail[postgres]'"
            ) from exc
        return psycopg.connect(self.dsn, autocommit=False)

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
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO results "
                "(trace_id, run_id, case_json, output_json, evaluation_json, steps_json, duration_ms) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
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
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT trace_id, case_json, output_json, evaluation_json, steps_json, duration_ms "
                "FROM results WHERE run_id = %s",
                (run_id,),
            )
            rows = cur.fetchall()
        return [
            {
                "trace_id": trace_id,
                "run_id": run_id,
                "case": c,
                "output": o,
                "evaluation": e,
                "steps": s,
                "duration_ms": duration_ms,
            }
            for trace_id, c, o, e, s, duration_ms in rows
        ]

    def load_trace(self, trace_id: str) -> dict | None:
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT run_id, case_json, output_json, evaluation_json, steps_json, duration_ms "
                "FROM results WHERE trace_id = %s",
                (trace_id,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        run_id, c, o, e, s, duration_ms = row
        return {
            "trace_id": trace_id,
            "run_id": run_id,
            "case": c,
            "output": o,
            "evaluation": e,
            "steps": s,
            "duration_ms": duration_ms,
        }

    def list_runs(self) -> list[dict]:
        with self._conn.cursor() as cur:
            cur.execute("SELECT run_id, evaluation_json FROM results")
            rows = cur.fetchall()
        stats: dict[str, dict] = {}
        for run_id, evaluation in rows:
            entry = stats.setdefault(run_id, {"total": 0, "passed": 0})
            entry["total"] += 1
            if evaluation.get("passed"):
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

    def overall_stats(self) -> dict:
        with self._conn.cursor() as cur:
            cur.execute("SELECT evaluation_json, steps_json, duration_ms FROM results")
            rows = cur.fetchall()

        total = len(rows)
        passed = 0
        total_duration = 0.0
        total_steps = 0
        failure_category_counts: dict[str, int] = {}
        for evaluation, steps, duration_ms in rows:
            if evaluation.get("passed"):
                passed += 1
            category = evaluation.get("failure_category")
            if category is not None:
                failure_category_counts[category] = failure_category_counts.get(category, 0) + 1
            total_duration += duration_ms or 0.0
            total_steps += len(steps or [])

        return {
            "total": total,
            "passed": passed,
            "pass_rate": passed / total if total else 0.0,
            "avg_duration_ms": total_duration / total if total else 0.0,
            "avg_steps": total_steps / total if total else 0.0,
            "failure_category_counts": failure_category_counts,
        }

    def enqueue_review(self, case: dict, output: dict, evaluation: dict) -> str:
        review_id = str(uuid.uuid4())
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO hitl_reviews (review_id, case_json, output_json, evaluation_json) "
                "VALUES (%s, %s, %s, %s)",
                (review_id, json.dumps(case), json.dumps(output), json.dumps(evaluation)),
            )
        self._conn.commit()
        return review_id

    def list_pending_reviews(self) -> list[dict]:
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT r.review_id, r.case_json, r.output_json, r.evaluation_json "
                "FROM hitl_reviews r "
                "LEFT JOIN hitl_annotations a ON a.review_id = r.review_id "
                "WHERE a.review_id IS NULL"
            )
            rows = cur.fetchall()
        return [
            {"review_id": review_id, "case": c, "output": o, "evaluation": e}
            for review_id, c, o, e in rows
        ]

    def record_annotation(self, review_id: str, annotation: dict) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO hitl_annotations (review_id, annotation_json) VALUES (%s, %s) "
                "ON CONFLICT (review_id) DO UPDATE SET annotation_json = EXCLUDED.annotation_json",
                (review_id, json.dumps(annotation)),
            )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
