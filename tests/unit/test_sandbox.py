import subprocess
import sys

import pytest

from runtrail.security.sandbox import exec_in_process, resource_limit_preexec_fn


def test_resource_limit_preexec_fn_returns_none_when_no_limits_requested():
    assert resource_limit_preexec_fn(None, None) is None


def test_resource_limit_preexec_fn_returns_a_callable_when_limits_requested():
    preexec_fn = resource_limit_preexec_fn(cpu_limit=5, memory_limit_mb=256)

    assert callable(preexec_fn)


def test_resource_limit_preexec_fn_actually_enforces_cpu_limit_in_a_real_subprocess():
    preexec_fn = resource_limit_preexec_fn(cpu_limit=1, memory_limit_mb=None)

    result = subprocess.run(
        [sys.executable, "-c", "i = 0\nwhile True:\n    i += 1"],
        capture_output=True,
        text=True,
        timeout=10,
        preexec_fn=preexec_fn,
        check=False,
    )

    # Killed by SIGXCPU (negative returncode) once it exceeds 1 CPU-second.
    assert result.returncode != 0


@pytest.mark.skipif(
    sys.platform == "darwin",
    reason=(
        "RLIMIT_AS is unreliable on Darwin — setrlimit(RLIMIT_AS, ...) itself raises "
        "'ValueError: current limit exceeds maximum limit' even from an unlimited starting "
        "point, a documented macOS kernel quirk, not a bug in resource_limit_preexec_fn. "
        "Verified working for real on Linux (python:3.12-slim in Docker): the same code "
        "correctly kills the child with MemoryError before it can allocate past the cap."
    ),
)
def test_resource_limit_preexec_fn_actually_enforces_memory_limit_on_linux():
    preexec_fn = resource_limit_preexec_fn(cpu_limit=None, memory_limit_mb=32)

    code = "x = bytearray(200 * 1024 * 1024); print('allocated')"
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=10,
        preexec_fn=preexec_fn,
        check=False,
    )

    assert result.returncode != 0
    assert "allocated" not in result.stdout


def test_exec_in_process_returns_stdout_with_no_error():
    stdout, error = exec_in_process("print('hello')")

    assert stdout.strip() == "hello"
    assert error is None


def test_exec_in_process_surfaces_an_exception_as_the_error():
    _stdout, error = exec_in_process("raise ValueError('boom')")

    assert error is not None
    assert "boom" in error


def test_resource_limit_preexec_fn_raises_on_non_posix(monkeypatch):
    monkeypatch.setattr("runtrail.security.sandbox._HAS_RESOURCE_MODULE", False)

    with pytest.raises(RuntimeError, match="POSIX"):
        resource_limit_preexec_fn(cpu_limit=1, memory_limit_mb=None)
