import os

import pytest

psycopg = pytest.importorskip("psycopg")

from runtrail.storage.postgres_store import PostgresStore

DSN = os.environ.get("RUNTRAIL_TEST_POSTGRES_DSN")

pytestmark = pytest.mark.skipif(not DSN, reason="RUNTRAIL_TEST_POSTGRES_DSN not set")


@pytest.fixture
def store():
    s = PostgresStore(DSN)
    yield s
    with s._conn.cursor() as cur:
        cur.execute("TRUNCATE results, hitl_reviews, hitl_annotations")
    s._conn.commit()


def test_save_and_load_run_round_trips_through_real_postgres(store):
    store.save_result(
        "run-1",
        {"input": "x"},
        {"output": "y"},
        {"passed": True, "score": 1.0},
        trace_id="trace-abc",
        steps=[{"type": "thought", "content": "thinking"}],
        duration_ms=12.5,
    )

    results = store.load_run("run-1")

    assert len(results) == 1
    assert results[0]["trace_id"] == "trace-abc"
    assert results[0]["case"] == {"input": "x"}
    assert results[0]["evaluation"]["passed"] is True
    assert results[0]["steps"] == [{"type": "thought", "content": "thinking"}]
    assert results[0]["duration_ms"] == 12.5


def test_load_trace_looks_up_a_single_case_by_trace_id(store):
    store.save_result("run-1", {"input": "x"}, {"output": "y"}, {"passed": True}, trace_id="trace-xyz")

    trace = store.load_trace("trace-xyz")

    assert trace["run_id"] == "run-1"
    assert trace["case"] == {"input": "x"}
    assert store.load_trace("missing") is None


def test_list_runs_and_overall_stats_through_real_postgres(store):
    store.save_result("run-1", {"input": "a"}, {}, {"passed": True}, duration_ms=10.0)
    store.save_result(
        "run-1",
        {"input": "b"},
        {},
        {"passed": False, "failure_category": "infinite_loop"},
        duration_ms=30.0,
    )

    runs = {r["run_id"]: r for r in store.list_runs()}
    assert runs["run-1"] == {"run_id": "run-1", "total": 2, "passed": 1, "pass_rate": 0.5}

    stats = store.overall_stats()
    assert stats["total"] == 2
    assert stats["passed"] == 1
    assert stats["avg_duration_ms"] == 20.0
    assert stats["failure_category_counts"] == {"infinite_loop": 1}


def test_hitl_queue_round_trips_through_real_postgres(store):
    review_id = store.enqueue_review({"input": "x"}, {"output": "y"}, {"passed": False})

    pending = store.list_pending_reviews()
    assert len(pending) == 1
    assert pending[0]["review_id"] == review_id

    store.record_annotation(review_id, {"reviewer": "alice", "passed": True, "score": 1.0, "notes": ""})

    assert store.list_pending_reviews() == []
