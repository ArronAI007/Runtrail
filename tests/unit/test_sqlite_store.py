import threading

from runtrail.storage.sqlite_store import SQLiteStore


def test_sqlite_store_round_trips_a_saved_result(tmp_path):
    store = SQLiteStore(tmp_path / "test.db")
    store.save_result(
        run_id="run-1",
        case={"input": "x"},
        output={"output": "x"},
        evaluation={"passed": True, "score": 1.0},
    )

    results = store.load_run("run-1")

    assert len(results) == 1
    assert results[0]["case"] == {"input": "x"}
    assert results[0]["evaluation"]["passed"] is True


def test_sqlite_store_is_usable_from_a_different_thread(tmp_path):
    store = SQLiteStore(tmp_path / "test.db")
    errors = []

    def write_from_another_thread():
        try:
            store.save_result("run-1", {"input": "x"}, {"output": "x"}, {"passed": True})
        except Exception as exc:  # noqa: BLE001 — capturing to assert on in the main thread
            errors.append(exc)

    thread = threading.Thread(target=write_from_another_thread)
    thread.start()
    thread.join()

    assert not errors
    assert len(store.load_run("run-1")) == 1


def test_save_result_stores_trace_id_steps_and_duration(tmp_path):
    store = SQLiteStore(tmp_path / "test.db")
    store.save_result(
        "run-1",
        {"input": "x"},
        {"output": "x"},
        {"passed": True},
        trace_id="trace-abc",
        steps=[{"type": "thought", "content": "thinking"}],
        duration_ms=42.5,
    )

    results = store.load_run("run-1")

    assert results[0]["trace_id"] == "trace-abc"
    assert results[0]["steps"] == [{"type": "thought", "content": "thinking"}]
    assert results[0]["duration_ms"] == 42.5


def test_load_trace_looks_up_a_single_case_by_trace_id(tmp_path):
    store = SQLiteStore(tmp_path / "test.db")
    store.save_result("run-1", {"input": "x"}, {"output": "x"}, {"passed": True}, trace_id="trace-abc")

    trace = store.load_trace("trace-abc")

    assert trace["run_id"] == "run-1"
    assert trace["case"] == {"input": "x"}


def test_load_trace_returns_none_for_unknown_id(tmp_path):
    store = SQLiteStore(tmp_path / "test.db")

    assert store.load_trace("does-not-exist") is None


def test_list_runs_aggregates_pass_rate_per_run(tmp_path):
    store = SQLiteStore(tmp_path / "test.db")
    store.save_result("run-1", {"input": "a"}, {}, {"passed": True})
    store.save_result("run-1", {"input": "b"}, {}, {"passed": False})
    store.save_result("run-2", {"input": "c"}, {}, {"passed": True})

    runs = {r["run_id"]: r for r in store.list_runs()}

    assert runs["run-1"] == {"run_id": "run-1", "total": 2, "passed": 1, "pass_rate": 0.5}
    assert runs["run-2"] == {"run_id": "run-2", "total": 1, "passed": 1, "pass_rate": 1.0}


def test_overall_stats_aggregates_across_all_runs(tmp_path):
    store = SQLiteStore(tmp_path / "test.db")
    store.save_result(
        "run-1", {"input": "a"}, {}, {"passed": True}, steps=[{"type": "thought"}], duration_ms=10.0
    )
    store.save_result(
        "run-1",
        {"input": "b"},
        {},
        {"passed": False, "failure_category": "infinite_loop"},
        duration_ms=30.0,
    )

    stats = store.overall_stats()

    assert stats["total"] == 2
    assert stats["passed"] == 1
    assert stats["pass_rate"] == 0.5
    assert stats["avg_duration_ms"] == 20.0
    assert stats["avg_steps"] == 0.5
    assert stats["failure_category_counts"] == {"infinite_loop": 1}
