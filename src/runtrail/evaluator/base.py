from abc import ABC, abstractmethod
from typing import Any


class BaseEvaluator(ABC):
    """Interface every Evaluator (rule / LLM-judge / code-exec) implements."""

    @abstractmethod
    def evaluate(self, output: dict, ground_truth: Any) -> dict:
        """Score one Agent output. Must return a dict with at least 'passed' and 'score'."""
