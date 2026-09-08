import pytest

from runtrail import Harness
from runtrail.dataset import InMemoryDataset
from runtrail.evaluator import FailureCategory, FailureClassifier, SimpleEvaluator


def test_classify_raises_if_evaluation_passed():
    with pytest.raises(ValueError, match="failed evaluation"):
        FailureClassifier().classify({}, {"passed": True})


def test_classify_maps_timeout_error_to_infinite_loop():
    category = FailureClassifier().classify({}, {"passed": False, "error": "TimeoutError: exceeded 5s"})
    assert category == FailureCategory.INFINITE_LOOP


def test_classify_maps_tool_call_accuracy_to_tool_call_error():
    category = FailureClassifier().classify({}, {"passed": False, "tool_call_accuracy": 0.5})
    assert category == FailureCategory.TOOL_CALL_ERROR


def test_classify_falls_back_to_unknown():
    category = FailureClassifier().classify({}, {"passed": False})
    assert category == FailureCategory.UNKNOWN


def test_harness_tags_a_crashed_case_with_failure_category():
    def agent(task_input: str) -> dict:
        raise TimeoutError("agent looped forever")

    dataset = InMemoryDataset([{"input": "x", "ground_truth": "y"}])
    report = Harness().run(agent=agent, dataset=dataset, evaluator=SimpleEvaluator())

    assert report.traces[0].evaluation["failure_category"] == FailureCategory.INFINITE_LOOP
