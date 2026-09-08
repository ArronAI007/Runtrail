from fastapi.testclient import TestClient

from runtrail.storage.sqlite_store import SQLiteStore
from runtrail.ui.main import create_app


def test_list_reviews_returns_the_pending_queue(tmp_path):
    store = SQLiteStore(tmp_path / "ui.db")
    store.enqueue_review({"input": "x"}, {"output": "y"}, {"passed": False})

    client = TestClient(create_app(store=store))
    response = client.get("/api/reviews")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_annotate_review_removes_it_from_pending(tmp_path):
    store = SQLiteStore(tmp_path / "ui.db")
    review_id = store.enqueue_review({"input": "x"}, {"output": "y"}, {"passed": False})

    client = TestClient(create_app(store=store))
    response = client.post(
        f"/api/reviews/{review_id}/annotate",
        json={"reviewer": "alice", "passed": True, "score": 1.0, "notes": "fine"},
    )

    assert response.status_code == 200
    assert client.get("/api/reviews").json() == []


def test_index_page_renders_pending_reviews_and_escapes_html(tmp_path):
    store = SQLiteStore(tmp_path / "ui.db")
    store.enqueue_review({"input": "<script>alert(1)</script>"}, {"output": "y"}, {"passed": False})

    client = TestClient(create_app(store=store))
    response = client.get("/")

    assert response.status_code == 200
    assert "<script>alert(1)</script>" not in response.text
    assert "&lt;script&gt;" in response.text


def test_get_run_returns_saved_results(tmp_path):
    store = SQLiteStore(tmp_path / "ui.db")
    store.save_result("run-1", {"input": "x"}, {"output": "y"}, {"passed": True}, trace_id="t-1")

    client = TestClient(create_app(store=store))
    response = client.get("/api/runs/run-1")

    results = response.json()
    assert len(results) == 1
    assert results[0]["trace_id"] == "t-1"
    assert results[0]["case"] == {"input": "x"}
    assert results[0]["output"] == {"output": "y"}
    assert results[0]["evaluation"] == {"passed": True}


def test_get_run_failed_only_filters_out_passing_cases(tmp_path):
    store = SQLiteStore(tmp_path / "ui.db")
    store.save_result("run-1", {"input": "a"}, {}, {"passed": True})
    store.save_result("run-1", {"input": "b"}, {}, {"passed": False})

    client = TestClient(create_app(store=store))
    response = client.get("/api/runs/run-1", params={"failed_only": "true"})

    results = response.json()
    assert len(results) == 1
    assert results[0]["case"] == {"input": "b"}


def test_list_runs_returns_run_summaries(tmp_path):
    store = SQLiteStore(tmp_path / "ui.db")
    store.save_result("run-1", {"input": "a"}, {}, {"passed": True})
    store.save_result("run-1", {"input": "b"}, {}, {"passed": False})

    client = TestClient(create_app(store=store))
    response = client.get("/api/runs")

    assert response.json() == [{"run_id": "run-1", "total": 2, "passed": 1, "pass_rate": 0.5}]


def test_get_trace_returns_full_detail_or_404(tmp_path):
    store = SQLiteStore(tmp_path / "ui.db")
    store.save_result(
        "run-1", {"input": "x"}, {"output": "y"}, {"passed": True}, trace_id="t-1", steps=[{"type": "thought"}]
    )

    client = TestClient(create_app(store=store))

    found = client.get("/api/traces/t-1")
    assert found.status_code == 200
    assert found.json()["steps"] == [{"type": "thought"}]

    missing = client.get("/api/traces/does-not-exist")
    assert missing.status_code == 404


def test_get_stats_returns_aggregate_metrics(tmp_path):
    store = SQLiteStore(tmp_path / "ui.db")
    store.save_result("run-1", {"input": "a"}, {}, {"passed": True}, duration_ms=10.0)
    store.save_result(
        "run-1", {"input": "b"}, {}, {"passed": False, "failure_category": "infinite_loop"}, duration_ms=30.0
    )

    client = TestClient(create_app(store=store))
    stats = client.get("/api/stats").json()

    assert stats["total"] == 2
    assert stats["passed"] == 1
    assert stats["avg_duration_ms"] == 20.0
    assert stats["failure_category_counts"] == {"infinite_loop": 1}


def test_run_detail_page_lists_traces_and_supports_failed_only_toggle(tmp_path):
    store = SQLiteStore(tmp_path / "ui.db")
    store.save_result("run-1", {"input": "a"}, {}, {"passed": True}, trace_id="t-pass")
    store.save_result("run-1", {"input": "b"}, {}, {"passed": False}, trace_id="t-fail")

    client = TestClient(create_app(store=store))

    all_page = client.get("/runs/run-1")
    assert "t-pass" in all_page.text
    assert "t-fail" in all_page.text

    failed_page = client.get("/runs/run-1", params={"failed_only": "true"})
    assert "t-fail" in failed_page.text
    assert "t-pass" not in failed_page.text


def test_trace_detail_page_renders_steps(tmp_path):
    store = SQLiteStore(tmp_path / "ui.db")
    store.save_result(
        "run-1",
        {"input": "x"},
        {"output": "y"},
        {"passed": True},
        trace_id="t-1",
        steps=[{"type": "tool_call", "tool": "search"}],
    )

    client = TestClient(create_app(store=store))
    response = client.get("/traces/t-1")

    assert response.status_code == 200
    assert "search" in response.text

    assert client.get("/traces/missing").status_code == 404


def test_index_page_shows_stats_and_run_list(tmp_path):
    store = SQLiteStore(tmp_path / "ui.db")
    store.save_result("run-1", {"input": "a"}, {}, {"passed": True})

    client = TestClient(create_app(store=store))
    response = client.get("/")

    assert "run-1" in response.text
    assert "pass rate" in response.text
