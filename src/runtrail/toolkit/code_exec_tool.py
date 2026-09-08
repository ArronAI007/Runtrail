import subprocess
import sys
from typing import Any

from runtrail.security.sandbox import exec_in_process, resource_limit_preexec_fn
from runtrail.toolkit.base_tool import BaseTool


class CodeExecTool(BaseTool):
    """Executes Python code and returns stdout/stderr — the tool-layer
    counterpart to CodeExecEvaluator, for Agents that need to run code as
    part of *solving* a task, not just for scoring the final answer.

    `sandbox=True` (default) runs it in a subprocess, optionally
    resource-limited via cpu_limit/memory_limit_mb, and always
    timeout-bounded. `sandbox=False` runs in-process instead: faster, but no
    isolation/limits/timeout — dev-only, never for untrusted Agent output.
    See the README's security note.
    """

    name = "code_exec"

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

    def call(self, **kwargs: Any) -> dict:
        code = kwargs["code"]
        if not self.sandbox:
            stdout, error = exec_in_process(code)
            return {"stdout": stdout, "stderr": error or "", "returncode": 0 if error is None else 1}

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
            return {"stdout": "", "stderr": f"timeout after {self.timeout_sec}s", "returncode": -1}
        return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
