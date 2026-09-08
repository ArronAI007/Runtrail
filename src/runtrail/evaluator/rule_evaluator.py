from typing import Any

from runtrail.evaluator.base import BaseEvaluator
from runtrail.evaluator.ground_truth import exact_match, normalized_match


class RuleEvaluator(BaseEvaluator):
    """Compares the agent's 'output' field against ground_truth using a rule function."""

    def __init__(self, rule=exact_match):
        self._rule = rule

    def evaluate(self, output: dict, ground_truth: Any) -> dict:
        passed = bool(self._rule(output.get("output"), ground_truth))
        return {"passed": passed, "score": 1.0 if passed else 0.0}


class SimpleEvaluator(RuleEvaluator):
    """Exact-match evaluator; the default for the quickstart example."""


class NormalizedMatchEvaluator(RuleEvaluator):
    """Case-insensitive, whitespace-trimmed match evaluator."""

    def __init__(self):
        super().__init__(rule=normalized_match)
