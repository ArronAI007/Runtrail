from runtrail import Harness, SimpleEvaluator
from runtrail.dataset import InMemoryDataset


def test_harness_runs_a_plain_callable_agent_and_reports_pass_rate():
    def agent(task_input: str) -> dict:
        return {"output": task_input}

    dataset = InMemoryDataset(
        [
            {"input": "4", "ground_truth": "4"},
            {"input": "wrong", "ground_truth": "right"},
        ]
    )

    report = Harness().run(agent=agent, dataset=dataset, evaluator=SimpleEvaluator())

    assert report.total == 2
    assert report.passed == 1
    assert report.summary() == "1/2 passed (50.0%)"


def test_harness_continues_after_an_agent_crashes_on_one_case():
    def agent(task_input: str) -> dict:
        if task_input == "boom":
            raise RuntimeError("simulated subprocess crash")
        return {"output": task_input}

    dataset = InMemoryDataset(
        [
            {"input": "boom", "ground_truth": "n/a"},
            {"input": "4", "ground_truth": "4"},
        ]
    )

    report = Harness().run(agent=agent, dataset=dataset, evaluator=SimpleEvaluator())

    assert report.total == 2
    assert report.passed == 1
    assert report.traces[0].evaluation["passed"] is False
    assert "RuntimeError" in report.traces[0].evaluation["error"]


def test_report_to_json_writes_a_readable_file(tmp_path):
    def agent(task_input: str) -> dict:
        return {"output": task_input}

    dataset = InMemoryDataset([{"input": "4", "ground_truth": "4"}])
    report = Harness().run(agent=agent, dataset=dataset, evaluator=SimpleEvaluator())

    out_path = tmp_path / "report.json"
    report.to_json(out_path)

    assert out_path.exists()
