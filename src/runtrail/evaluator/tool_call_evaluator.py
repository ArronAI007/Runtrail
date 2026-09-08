from typing import Any

from runtrail.evaluator.base import BaseEvaluator


class ToolCallEvaluator(BaseEvaluator):
    """Checks the Agent's tool calls against the expected sequence.

    Reads output['tool_calls'] (a list of {"tool": str, "args": dict}, in call
    order) and compares it against ground_truth, which must be the same shape.
    Reports 'tool_call_accuracy' as the fraction of expected calls matched
    position-by-position, so it also feeds FailureClassifier's TOOL_CALL_ERROR path.
    """

    def evaluate(self, output: dict, ground_truth: Any) -> dict:
        actual = output.get("tool_calls", [])
        expected = ground_truth or []

        if not expected:
            accuracy = 1.0 if not actual else 0.0
        else:
            matched = sum(1 for a, e in zip(actual, expected) if a == e)
            accuracy = matched / len(expected)

        passed = accuracy == 1.0 and len(actual) == len(expected)
        return {"passed": passed, "score": accuracy, "tool_call_accuracy": accuracy}
