import random
import time

import pytest

from runtrail.toolkit.local_function_tool import LocalFunctionTool
from runtrail.toolkit.tool_mock import ToolMock


def test_call_returns_fake_response_by_default():
    tool = ToolMock("search", fake_response={"results": []})

    assert tool.call(q="anything") == {"results": []}


def test_call_raises_the_injected_exception():
    tool = ToolMock("search", raise_=ConnectionError("simulated network failure"))

    with pytest.raises(ConnectionError, match="simulated network failure"):
        tool.call()


def test_call_simulates_a_timeout():
    tool = ToolMock("search", timeout_after_sec=0.05)

    start = time.monotonic()
    with pytest.raises(TimeoutError, match="simulated a timeout"):
        tool.call()
    assert time.monotonic() - start >= 0.05


def test_call_garbles_a_string_response_deterministically():
    tool = ToolMock("search", fake_response="hello world", garble=True, rng=random.Random(1))

    result = tool.call()

    assert result != "hello world"
    assert len(result) == len("hello world")


def test_call_delegates_to_wrapped_tool_when_failure_rate_is_zero():
    real = LocalFunctionTool("search", lambda q: f"real result for {q}")
    tool = ToolMock("search", wrapped=real, fake_response="fake", failure_rate=0.0)

    assert tool.call(q="x") == "real result for x"


def test_call_always_injects_fault_when_failure_rate_is_one():
    real = LocalFunctionTool("search", lambda q: f"real result for {q}")
    tool = ToolMock("search", wrapped=real, fake_response="fake", failure_rate=1.0)

    assert tool.call(q="x") == "fake"


def test_failure_rate_probabilistically_mixes_real_and_fake_calls():
    real = LocalFunctionTool("search", lambda q: "real")
    tool = ToolMock("search", wrapped=real, fake_response="fake", failure_rate=0.5, rng=random.Random(42))

    results = [tool.call(q="x") for _ in range(50)]

    assert "real" in results
    assert "fake" in results
