import sys

import pytest

from runtrail.toolkit.code_exec_tool import CodeExecTool


def test_call_returns_stdout_for_successful_code():
    tool = CodeExecTool()

    result = tool.call(code="print(2 + 2)")

    assert result["stdout"].strip() == "4"
    assert result["returncode"] == 0


def test_call_captures_stderr_on_exception():
    tool = CodeExecTool()

    result = tool.call(code="raise ValueError('boom')")

    assert result["returncode"] != 0
    assert "boom" in result["stderr"]


def test_call_reports_timeout():
    tool = CodeExecTool(timeout_sec=0.2)

    result = tool.call(code="while True: pass")

    assert result["returncode"] == -1
    assert "timeout" in result["stderr"]


def test_call_with_sandbox_off_runs_in_process():
    tool = CodeExecTool(sandbox=False)

    result = tool.call(code="print(2 + 2)")

    assert result["stdout"].strip() == "4"
    assert result["returncode"] == 0


def test_call_with_sandbox_off_reports_exceptions_as_stderr():
    tool = CodeExecTool(sandbox=False)

    result = tool.call(code="raise ValueError('boom')")

    assert result["returncode"] != 0
    assert "boom" in result["stderr"]


def test_call_enforces_cpu_limit_when_sandboxed():
    tool = CodeExecTool(timeout_sec=10, cpu_limit=1)

    result = tool.call(code="i = 0\nwhile True:\n    i += 1")

    assert result["returncode"] != 0


@pytest.mark.skipif(
    sys.platform == "darwin",
    reason=(
        "RLIMIT_AS is unreliable on Darwin (setrlimit itself raises 'current limit exceeds "
        "maximum limit' even from an unlimited baseline) — verified working for real on Linux "
        "(python:3.12-slim in Docker), see test_sandbox.py"
    ),
)
def test_call_enforces_memory_limit_when_sandboxed():
    tool = CodeExecTool(memory_limit_mb=32)

    result = tool.call(code="x = bytearray(200 * 1024 * 1024); print('allocated')")

    assert result["returncode"] != 0
    assert "allocated" not in result["stdout"]
