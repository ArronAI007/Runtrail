from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """Interface every Agent adapter (local / subprocess / remote) implements."""

    @abstractmethod
    def run(self, task_input: Any) -> dict:
        """Execute one task and return the agent's output as a dict."""
