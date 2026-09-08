import random
import time
from typing import Any

from runtrail.toolkit.base_tool import BaseTool


class ToolMock(BaseTool):
    """Injects failures/latency/corruption for robustness testing, without
    depending on a real external service. Can stand alone (always returns
    `fake_response`) or wrap a real BaseTool and only inject faults some of
    the time (`wrapped=`, `failure_rate=`) — useful for chaos-testing a real
    integration.
    """

    def __init__(
        self,
        name: str,
        *,
        wrapped: BaseTool | None = None,
        fake_response: Any = None,
        raise_: Exception | None = None,
        delay_sec: float = 0.0,
        timeout_after_sec: float | None = None,
        garble: bool = False,
        failure_rate: float = 1.0,
        rng: random.Random | None = None,
    ):
        self.name = name
        self.wrapped = wrapped
        self._fake_response = fake_response
        self._raise = raise_
        self.delay_sec = delay_sec
        self.timeout_after_sec = timeout_after_sec
        self.garble = garble
        self.failure_rate = failure_rate
        self._rng = rng or random.Random()

    def call(self, **kwargs: Any) -> Any:
        if self.wrapped is not None and self._rng.random() >= self.failure_rate:
            return self.wrapped.call(**kwargs)

        if self.timeout_after_sec is not None:
            time.sleep(self.timeout_after_sec)
            raise TimeoutError(f"ToolMock '{self.name}' simulated a timeout after {self.timeout_after_sec}s")

        if self.delay_sec:
            time.sleep(self.delay_sec)

        if self._raise is not None:
            raise self._raise

        response = self._fake_response
        if self.garble and isinstance(response, str):
            response = _garble(response, rng=self._rng)
        return response


def _garble(text: str, *, rng: random.Random) -> str:
    """Deterministic (given a seeded rng) mojibake-style corruption, for
    testing how an Agent handles a tool returning garbled/unparseable text.
    """
    corruption_chars = ["�", "\x00", "?"]
    return "".join(rng.choice(corruption_chars) if rng.random() < 0.3 else ch for ch in text)
