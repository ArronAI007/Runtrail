from collections.abc import Callable
from typing import Any

from runtrail.agent.base import BaseAgent


class LocalAgent(BaseAgent):
    """Wraps a plain in-process callable as a BaseAgent."""

    def __init__(self, fn: Callable[[Any], dict]):
        self._fn = fn

    def run(self, task_input: Any) -> dict:
        return self._fn(task_input)
