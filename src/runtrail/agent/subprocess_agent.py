import json
import subprocess
from typing import Any

from runtrail.agent.base import BaseAgent
from runtrail.security.sandbox import resource_limit_preexec_fn


class SubprocessAgent(BaseAgent):
    """Runs the agent in an isolated subprocess sandbox, so a crashing or looping
    Agent can't take down the harness. The command is invoked once per task: it
    receives {"input": task_input} as JSON on stdin and must print a JSON object
    to stdout. cpu_limit/memory_limit_mb enforce OS-level resource limits (POSIX only).
    """

    def __init__(
        self,
        command: list[str],
        *,
        timeout_sec: float = 60.0,
        cpu_limit: float | None = None,
        memory_limit_mb: int | None = None,
    ):
        self.command = command
        self.timeout_sec = timeout_sec
        self.cpu_limit = cpu_limit
        self.memory_limit_mb = memory_limit_mb

    def run(self, task_input: Any) -> dict:
        preexec_fn = resource_limit_preexec_fn(self.cpu_limit, self.memory_limit_mb)

        try:
            result = subprocess.run(
                self.command,
                input=json.dumps({"input": task_input}),
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
                preexec_fn=preexec_fn,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(
                f"SubprocessAgent exceeded timeout_sec={self.timeout_sec}"
            ) from exc

        if result.returncode != 0:
            raise RuntimeError(
                f"SubprocessAgent command failed (exit {result.returncode}): {result.stderr.strip()}"
            )

        return json.loads(result.stdout)
