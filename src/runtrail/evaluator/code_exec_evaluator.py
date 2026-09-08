import subprocess
import sys
from typing import Any

from runtrail.evaluator.base import BaseEvaluator
from runtrail.security.sandbox import exec_in_process, resource_limit_preexec_fn


class CodeExecEvaluator(BaseEvaluator):
    """Executes the agent's 'output' field as Python code and compares its
    stdout against ground_truth.

    `sandbox=True` (default) runs it in a subprocess — OS-level isolation
    (same idea as SubprocessAgent), optionally resource-limited via
    cpu_limit/memory_limit_mb, and always timeout-bounded. `sandbox=False`
    runs it in-process instead: no isolation, no resource limits, no timeout
    — faster for trusted code during dev iteration, never for untrusted
    Agent output. See the README's security note.
    """

    def __init__(
        self,
        timeout_sec: float = 10.0,
        *,
        sandbox: bool = True,
        cpu_limit: float | None = None,
        memory_limit_mb: int | None = None,
    ):
        self.timeout_sec = timeout_sec
        self.sandbox = sandbox
        self.cpu_limit = cpu_limit
        self.memory_limit_mb = memory_limit_mb

    def evaluate(self, output: dict, ground_truth: Any) -> dict:
        code = output.get("output", "")

        if self.sandbox:
            actual, error = self._run_sandboxed(code)
        else:
            actual, error = exec_in_process(code)

        if error is not None:
            return {"passed": False, "score": 0.0, "error": error}

        actual = actual.strip()
        passed = actual == str(ground_truth).strip()
        return {"passed": passed, "score": 1.0 if passed else 0.0, "stdout": actual}

    def _run_sandboxed(self, code: str) -> tuple[str, str | None]:
        preexec_fn = resource_limit_preexec_fn(self.cpu_limit, self.memory_limit_mb)
        try:
            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
                preexec_fn=preexec_fn,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return "", f"code execution exceeded timeout_sec={self.timeout_sec}"

        if result.returncode != 0:
            return "", result.stderr.strip()
        return result.stdout, None
