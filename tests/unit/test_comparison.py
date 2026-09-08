from runtrail import Harness, SimpleEvaluator
from runtrail.dataset import InMemoryDataset


def test_compare_runs_every_candidate_against_the_same_dataset():
    dataset = InMemoryDataset(
        [
            {"input": "2+2", "ground_truth": "4"},
            {"input": "capital of France", "ground_truth": "Paris"},
        ]
    )

    def good_agent(task_input: str) -> dict:
        answers = {"2+2": "4", "capital of France": "Paris"}
        return {"output": answers[task_input]}

    def bad_agent(task_input: str) -> dict:
        return {"output": "I don't know"}

    comparison = Harness().compare(
        {"good": good_agent, "bad": bad_agent}, dataset, SimpleEvaluator()
    )

    assert comparison.reports["good"].passed == 2
    assert comparison.reports["bad"].passed == 0
    assert comparison.best() == "good"


def test_comparison_summary_table_lists_all_candidates():
    dataset = InMemoryDataset([{"input": "x", "ground_truth": "x"}])
    comparison = Harness().compare(
        {"a": lambda x: {"output": x}, "b": lambda x: {"output": "wrong"}},
        dataset,
        SimpleEvaluator(),
    )

    table = comparison.summary_table()

    assert "a" in table
    assert "b" in table
    assert "pass_rate" in table


def test_comparison_to_json_writes_per_candidate_stats(tmp_path):
    dataset = InMemoryDataset([{"input": "x", "ground_truth": "x"}])
    comparison = Harness().compare({"a": lambda x: {"output": x}}, dataset, SimpleEvaluator())

    path = tmp_path / "comparison.json"
    comparison.to_json(path)

    import json

    data = json.loads(path.read_text())
    assert data["a"]["pass_rate"] == 1.0
