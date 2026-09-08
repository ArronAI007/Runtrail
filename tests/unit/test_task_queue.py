import threading
import time

import pytest

from runtrail.runtime.queue import TaskQueue


def test_map_respects_max_concurrency():
    max_concurrency = 2
    queue = TaskQueue(max_concurrency=max_concurrency)
    active: list[int] = []
    peak: list[int] = []
    lock = threading.Lock()

    def task(i):
        with lock:
            active.append(i)
            peak.append(len(active))
        time.sleep(0.05)
        with lock:
            active.remove(i)
        return i

    results = queue.map(task, range(6))
    queue.shutdown()

    assert sorted(results) == list(range(6))
    assert max(peak) <= max_concurrency


def test_submit_retries_until_it_succeeds():
    queue = TaskQueue(max_concurrency=1, max_retries=2, backoff_base_sec=0.01)
    attempts = {"count": 0}

    def flaky():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("transient")
        return "ok"

    future = queue.submit(flaky)

    assert future.result() == "ok"
    assert attempts["count"] == 3
    queue.shutdown()


def test_submit_raises_after_exhausting_retries():
    queue = TaskQueue(max_concurrency=1, max_retries=1, backoff_base_sec=0.01)

    def always_fails():
        raise RuntimeError("permanent")

    future = queue.submit(always_fails)

    with pytest.raises(RuntimeError, match="permanent"):
        future.result()
    queue.shutdown()


def test_rate_limit_spaces_out_submissions():
    queue = TaskQueue(max_concurrency=5, rate_limit_per_sec=10)  # min interval 0.1s
    start = time.monotonic()

    queue.map(lambda i: i, range(4))

    elapsed = time.monotonic() - start
    queue.shutdown()
    assert elapsed >= 0.3  # at least 3 gaps of ~0.1s between 4 submissions


def test_higher_priority_tasks_run_before_lower_priority_ones():
    queue = TaskQueue(max_concurrency=1)
    order: list[str] = []
    release = threading.Event()

    def gatekeeper():
        release.wait()  # holds the single worker so the batch below queues up first

    def record(name):
        order.append(name)

    gate_future = queue.submit(gatekeeper)
    low1 = queue.submit(record, "low1", priority=0)
    high1 = queue.submit(record, "high1", priority=10)
    low2 = queue.submit(record, "low2", priority=0)
    high2 = queue.submit(record, "high2", priority=10)

    release.set()
    for future in [gate_future, low1, high1, low2, high2]:
        future.result()
    queue.shutdown()

    assert order == ["high1", "high2", "low1", "low2"]


def test_map_accepts_a_priority_key_per_item():
    queue = TaskQueue(max_concurrency=1)
    order: list[str] = []
    release = threading.Event()

    def gatekeeper():
        release.wait()

    def record(item):
        order.append(item["name"])

    gate_future = queue.submit(gatekeeper)
    items = [{"name": "low"}, {"name": "high"}]

    def run_map():
        queue.map(record, items, priority_key=lambda item: 10 if item["name"] == "high" else 0)

    thread = threading.Thread(target=run_map)
    thread.start()
    time.sleep(0.05)  # let both items land on the heap behind the gatekeeper
    release.set()
    gate_future.result()
    thread.join()
    queue.shutdown()

    assert order == ["high", "low"]
