import html
from contextlib import asynccontextmanager
from typing import Any

from runtrail.hitl.annotation import Annotation
from runtrail.hitl.hitl_service import HITLService
from runtrail.storage.base import BaseStore

_PAGE_HEAD = "<html><head><title>Runtrail</title></head><body>"
_PAGE_TAIL = "</body></html>"
_NAV = '<p><a href="/">Dashboard</a></p>'


def create_app(store: BaseStore | None = None) -> Any:
    """Build the optional lightweight Web UI: task list, per-run Trace
    viewer, aggregate stats, and the HITL review queue — all backed by
    `store` (defaults to a local SQLiteStore). Requires the 'ui' extra:
    pip install 'runtrail[ui]'.
    """
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.responses import HTMLResponse
        from pydantic import BaseModel
    except ImportError as exc:
        raise ImportError(
            "The Runtrail Web UI requires the 'ui' extra: pip install 'runtrail[ui]'"
        ) from exc

    if store is None:
        from runtrail.storage.sqlite_store import SQLiteStore

        store = SQLiteStore()

    hitl = HITLService(store)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield
        store.close()

    app = FastAPI(title="Runtrail", lifespan=lifespan)

    class AnnotationRequest(BaseModel):
        reviewer: str
        passed: bool
        score: float
        notes: str = ""

    @app.get("/api/reviews")
    def list_reviews() -> list[dict]:
        return hitl.pending_reviews()

    @app.post("/api/reviews/{review_id}/annotate")
    def annotate_review(review_id: str, body: AnnotationRequest) -> dict:
        hitl.submit_annotation(
            Annotation(
                review_id=review_id,
                reviewer=body.reviewer,
                passed=body.passed,
                score=body.score,
                notes=body.notes,
            )
        )
        return {"status": "ok"}

    @app.get("/api/runs")
    def list_runs() -> list[dict]:
        return store.list_runs()

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str, failed_only: bool = False) -> list[dict]:
        traces = store.load_run(run_id)
        if failed_only:
            traces = [t for t in traces if not t["evaluation"].get("passed", True)]
        return traces

    @app.get("/api/traces/{trace_id}")
    def get_trace(trace_id: str) -> dict:
        trace = store.load_trace(trace_id)
        if trace is None:
            raise HTTPException(status_code=404, detail="trace not found")
        return trace

    @app.get("/api/stats")
    def get_stats() -> dict:
        return store.overall_stats()

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        stats = store.overall_stats()
        runs = store.list_runs()
        reviews = hitl.pending_reviews()
        return (
            _PAGE_HEAD
            + f"<h1>Runtrail Dashboard</h1>{_render_stats(stats)}"
            + f"<h2>Runs ({len(runs)})</h2>{_render_run_list(runs)}"
            + f"<h2>Pending Reviews ({len(reviews)})</h2>{_render_review_table(reviews)}"
            + _PAGE_TAIL
        )

    @app.get("/runs/{run_id}", response_class=HTMLResponse)
    def run_detail(run_id: str, failed_only: bool = False) -> str:
        traces = store.load_run(run_id)
        if failed_only:
            traces = [t for t in traces if not t["evaluation"].get("passed", True)]
        toggle_href = f"/runs/{run_id}" if failed_only else f"/runs/{run_id}?failed_only=true"
        toggle_label = "Show all cases" if failed_only else "Show failed cases only"
        return (
            _PAGE_HEAD
            + _NAV
            + f"<h1>Run {html.escape(run_id)}</h1>"
            + f'<p><a href="{toggle_href}">{toggle_label}</a></p>'
            + _render_trace_table(traces)
            + _PAGE_TAIL
        )

    @app.get("/traces/{trace_id}", response_class=HTMLResponse)
    def trace_detail(trace_id: str) -> str:
        trace = store.load_trace(trace_id)
        if trace is None:
            raise HTTPException(status_code=404, detail="trace not found")
        return _PAGE_HEAD + _NAV + _render_trace_detail(trace) + _PAGE_TAIL

    return app


def _esc(value: Any) -> str:
    return html.escape(str(value))


def _render_stats(stats: dict) -> str:
    pass_pct = round(stats["pass_rate"] * 100)
    failure_rows = "".join(
        f"<tr><td>{_esc(category)}</td><td>{count}</td></tr>"
        for category, count in stats["failure_category_counts"].items()
    )
    return (
        f"<p>Total cases: {stats['total']} — Passed: {stats['passed']} "
        f"— Avg duration: {stats['avg_duration_ms']:.1f}ms — Avg steps: {stats['avg_steps']:.1f}</p>"
        '<div style="background:#eee;width:300px;height:20px;border:1px solid #999">'
        f'<div style="background:#4a4;width:{pass_pct}%;height:100%"></div></div>'
        f"<p>{pass_pct}% pass rate</p>"
        + (
            f'<table border="1" cellpadding="6"><tr><th>Failure category</th><th>Count</th></tr>'
            f"{failure_rows}</table>"
            if failure_rows
            else ""
        )
    )


def _render_run_list(runs: list[dict]) -> str:
    if not runs:
        return "<p>No runs yet.</p>"
    rows = "".join(
        f'<tr><td><a href="/runs/{_esc(r["run_id"])}">{_esc(r["run_id"])}</a></td>'
        f'<td>{r["passed"]}/{r["total"]}</td><td>{r["pass_rate"] * 100:.1f}%</td></tr>'
        for r in runs
    )
    return f'<table border="1" cellpadding="6"><tr><th>Run ID</th><th>Passed</th><th>Pass rate</th></tr>{rows}</table>'


def _render_review_table(reviews: list[dict]) -> str:
    rows = "".join(
        f"<tr><td>{_esc(r['review_id'])}</td><td><pre>{_esc(r['case'])}</pre></td>"
        f"<td><pre>{_esc(r['output'])}</pre></td><td><pre>{_esc(r['evaluation'])}</pre></td></tr>"
        for r in reviews
    )
    return (
        '<table border="1" cellpadding="6">'
        "<tr><th>Review ID</th><th>Case</th><th>Output</th><th>Evaluation</th></tr>"
        f"{rows}</table>"
    )


def _render_trace_table(traces: list[dict]) -> str:
    if not traces:
        return "<p>No cases.</p>"
    rows = "".join(
        f'<tr><td><a href="/traces/{_esc(t["trace_id"])}">{_esc(t["trace_id"])}</a></td>'
        f"<td>{_esc(t['case'].get('input'))}</td>"
        f"<td>{'PASS' if t['evaluation'].get('passed') else 'FAIL'}</td>"
        f"<td>{_esc(t['evaluation'].get('failure_category', ''))}</td>"
        f"<td>{t['duration_ms']:.1f}ms</td><td>{len(t['steps'])}</td></tr>"
        for t in traces
    )
    return (
        '<table border="1" cellpadding="6">'
        "<tr><th>Trace ID</th><th>Input</th><th>Result</th><th>Failure category</th>"
        "<th>Duration</th><th>Steps</th></tr>"
        f"{rows}</table>"
    )


def _render_trace_detail(trace: dict) -> str:
    steps_html = "".join(f"<li><pre>{_esc(step)}</pre></li>" for step in trace["steps"]) or "<li>none</li>"
    return (
        f"<h1>Trace {_esc(trace['trace_id'])}</h1>"
        f"<p>Run: {_esc(trace['run_id'])} — Duration: {trace['duration_ms']:.1f}ms</p>"
        f"<h2>Case</h2><pre>{_esc(trace['case'])}</pre>"
        f"<h2>Output</h2><pre>{_esc(trace['output'])}</pre>"
        f"<h2>Evaluation</h2><pre>{_esc(trace['evaluation'])}</pre>"
        f"<h2>Steps</h2><ul>{steps_html}</ul>"
    )
