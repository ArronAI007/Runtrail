import sys

import pytest

from runtrail.agent.subprocess_agent import SubprocessAgent

_ECHO_SCRIPT = (
    "import sys, json; "
    "data = json.loads(sys.stdin.read()); "
    "print(json.dumps({'output': data['input']}))"
)
_SLEEP_SCRIPT = "import time; time.sleep(5)"
_FAIL_SCRIPT = "import sys; sys.stderr.write('boom'); sys.exit(1)"


def test_run_returns_parsed_stdout_json():
    agent = SubprocessAgent([sys.executable, "-c", _ECHO_SCRIPT])

    result = agent.run("hello")

    assert result == {"output": "hello"}


def test_run_raises_timeout_error_when_command_hangs():
    agent = SubprocessAgent([sys.executable, "-c", _SLEEP_SCRIPT], timeout_sec=0.2)

    with pytest.raises(TimeoutError):
        agent.run("hello")


def test_run_raises_runtime_error_on_nonzero_exit():
    agent = SubprocessAgent([sys.executable, "-c", _FAIL_SCRIPT])

    with pytest.raises(RuntimeError, match="boom"):
        agent.run("hello")
