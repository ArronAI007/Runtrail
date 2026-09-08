import sys

import pytest

from runtrail.evaluator import (
    CodeExecEvaluator,
    JSONSchemaEvaluator,
    NormalizedMatchEvaluator,
    ToolCallEvaluator,
)


def test_normalized_match_evaluator_ignores_case_and_whitespace():
    evaluator = NormalizedMatchEvaluator()

    assert evaluator.evaluate({"output": "  Paris  "}, "paris")["passed"] is True
    assert evaluator.evaluate({"output": "London"}, "paris")["passed"] is False


def test_json_schema_evaluator_passes_valid_output():
    schema = {"type": "object", "required": ["answer"], "properties": {"answer": {"type": "string"}}}
    evaluator = JSONSchemaEvaluator(schema)

    result = evaluator.evaluate({"output": {"answer": "4"}}, None)

    assert result["passed"] is True


def test_json_schema_evaluator_fails_invalid_output():
    schema = {"type": "object", "required": ["answer"]}
    evaluator = JSONSchemaEvaluator(schema)

    result = evaluator.evaluate({"output": {}}, None)

    assert result["passed"] is False
    assert "error" in result


def test_tool_call_evaluator_scores_partial_accuracy():
    evaluator = ToolCallEvaluator()
    expected = [{"tool": "search", "args": {"q": "x"}}, {"tool": "sum", "args": {}}]
    actual = {"tool_calls": [{"tool": "search", "args": {"q": "x"}}, {"tool": "sum", "args": {"wrong": 1}}]}

    result = evaluator.evaluate(actual, expected)

    assert result["passed"] is False
    assert result["tool_call_accuracy"] == 0.5


def test_tool_call_evaluator_passes_exact_match():
    evaluator = ToolCallEvaluator()
    expected = [{"tool": "search", "args": {"q": "x"}}]
    actual = {"tool_calls": [{"tool": "search", "args": {"q": "x"}}]}

    result = evaluator.evaluate(actual, expected)

    assert result["passed"] is True
    assert result["tool_call_accuracy"] == 1.0


def test_code_exec_evaluator_passes_when_stdout_matches_ground_truth():
    evaluator = CodeExecEvaluator()

    result = evaluator.evaluate({"output": "print(2 + 2)"}, "4")

    assert result["passed"] is True
    assert result["stdout"] == "4"


def test_code_exec_evaluator_reports_error_on_exception():
    evaluator = CodeExecEvaluator()

    result = evaluator.evaluate({"output": "raise ValueError('boom')"}, "irrelevant")

    assert result["passed"] is False
    assert "boom" in result["error"]


def test_code_exec_evaluator_times_out_on_infinite_loop():
    evaluator = CodeExecEvaluator(timeout_sec=0.2)

    result = evaluator.evaluate({"output": "while True: pass"}, "x")

    assert result["passed"] is False
    assert "timeout" in result["error"]


def test_code_exec_evaluator_with_sandbox_off_runs_in_process():
    evaluator = CodeExecEvaluator(sandbox=False)

    result = evaluator.evaluate({"output": "print(2 + 2)"}, "4")

    assert result["passed"] is True
    assert result["stdout"] == "4"


def test_code_exec_evaluator_with_sandbox_off_reports_exceptions_too():
    evaluator = CodeExecEvaluator(sandbox=False)

    result = evaluator.evaluate({"output": "raise ValueError('boom')"}, "irrelevant")

    assert result["passed"] is False
    assert "boom" in result["error"]


def test_code_exec_evaluator_enforces_cpu_limit_when_sandboxed():
    evaluator = CodeExecEvaluator(timeout_sec=10, cpu_limit=1)

    result = evaluator.evaluate({"output": "i = 0\nwhile True:\n    i += 1"}, "n/a")

    assert result["passed"] is False


@pytest.mark.skipif(
    sys.platform == "darwin",
    reason=(
        "RLIMIT_AS is unreliable on Darwin (setrlimit itself raises 'current limit exceeds "
        "maximum limit' even from an unlimited baseline) — verified working for real on Linux "
        "(python:3.12-slim in Docker), see test_sandbox.py"
    ),
)
def test_code_exec_evaluator_enforces_memory_limit_when_sandboxed():
    evaluator = CodeExecEvaluator(memory_limit_mb=32)

    result = evaluator.evaluate({"output": "x = bytearray(200 * 1024 * 1024); print('allocated')"}, "n/a")

    assert result["passed"] is False
    assert "allocated" not in result.get("stdout", "")
