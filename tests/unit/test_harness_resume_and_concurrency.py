import threading
import time

from runtrail import Harness, SimpleEvaluator
from runtrail.dataset import InMemoryDataset
from runtrail.runtime.checkpoint import Checkpoint
from runtrail.runtime.queue import TaskQueue


def test_harness_with_queue_runs_all_cases_concurrently():
    dataset = InMemoryDataset([{"input": str(i), "ground_truth": str(i)} for i in range(5)])

    def agent(task_input: str) -> dict:
        return {"output": task_input}

    queue = TaskQueue(max_concurrency=3)
    report = Harness().run(agent=agent, dataset=dataset, evaluator=SimpleEvaluator(), queue=queue)
    queue.shutdown()

    assert report.total == 5
    assert report.passed == 5


def test_harness_runs_higher_priority_cases_first_under_a_bounded_queue():
    dataset = InMemoryDataset(
        [
            {"input": "low1", "ground_truth": "low1", "priority": 0},
            {"input": "high1", "ground_truth": "high1", "priority": 10},
            {"input": "low2", "ground_truth": "low2", "priority": 0},
            {"input": "high2", "ground_truth": "high2", "priority": 10},
        ]
    )
    order: list[str] = []

    def agent(task_input: str) -> dict:
        order.append(task_input)
        return {"output": task_input}

    queue = TaskQueue(max_concurrency=1)
    release = threading.Event()
    # A gatekeeper unrelated to the dataset holds the single worker, so all 4
    # cases are guaranteed to be queued (and heap-sorted by priority) before
    # any of them run — otherwise which case races onto the worker first could
    # itself masquerade as "priority order" by coincidence.
    gate_future = queue.submit(release.wait)

    thread = threading.Thread(
        target=lambda: Harness().run(agent=agent, dataset=dataset, evaluator=SimpleEvaluator(), queue=queue)
    )
    thread.start()
    time.sleep(0.1)  # let all 4 cases land on the heap behind the gatekeeper
    release.set()
    gate_future.result()
    thread.join()
    queue.shutdown()

    assert order == ["high1", "high2", "low1", "low2"]


def test_harness_checkpoint_does_not_rerun_completed_cases(tmp_path):
    calls = []

    def agent(task_input: str) -> dict:
        calls.append(task_input)
        return {"output": task_input}

    dataset = InMemoryDataset(
        [
            {"input": "a", "ground_truth": "a"},
            {"input": "b", "ground_truth": "b"},
        ]
    )
    checkpoint = Checkpoint("run-1", checkpoint_dir=tmp_path)

    report1 = Harness().run(agent=agent, dataset=dataset, evaluator=SimpleEvaluator(), checkpoint=checkpoint)
    assert calls == ["a", "b"]
    assert report1.passed == 2

    def failing_agent(task_input: str) -> dict:
        raise AssertionError("should not rerun a completed case")

    resumed_checkpoint = Checkpoint("run-1", checkpoint_dir=tmp_path)
    report2 = Harness().run(
        agent=failing_agent, dataset=dataset, evaluator=SimpleEvaluator(), checkpoint=resumed_checkpoint
    )

    assert report2.total == 2
    assert report2.passed == 2


def test_harness_resumes_from_a_partially_completed_checkpoint(tmp_path):
    dataset = InMemoryDataset(
        [
            {"input": "a", "ground_truth": "a"},
            {"input": "b", "ground_truth": "b"},
            {"input": "c", "ground_truth": "c"},
        ]
    )
    checkpoint = Checkpoint("run-2", checkpoint_dir=tmp_path)
    for case_id, letter in [("0", "a"), ("1", "b")]:
        checkpoint.save_case(
            case_id,
            {
                "case": {"input": letter, "ground_truth": letter},
                "output": {"output": letter},
                "evaluation": {"passed": True, "score": 1.0},
                "timestamp": "2024-01-01T00:00:00+00:00",
            },
        )

    calls = []

    def agent(task_input: str) -> dict:
        calls.append(task_input)
        return {"output": task_input}

    report = Harness().run(agent=agent, dataset=dataset, evaluator=SimpleEvaluator(), checkpoint=checkpoint)

    assert calls == ["c"]
    assert report.total == 3
    assert report.passed == 3
