import contextlib
import io
import sys
from collections.abc import Callable

_HAS_RESOURCE_MODULE = sys.platform != "win32"
if _HAS_RESOURCE_MODULE:
    import resource


def resource_limit_preexec_fn(
    cpu_limit: float | None,
    memory_limit_mb: int | None,
) -> Callable[[], None] | None:
    """Build a `subprocess.run(preexec_fn=...)` that applies POSIX rlimits, or
    None if no limits were requested. Shared by every subprocess-based sandbox
    (SubprocessAgent, CodeExecEvaluator, CodeExecTool) so the CPU/memory-limit
    semantics stay identical across all of them.
    """
    if cpu_limit is None and memory_limit_mb is None:
        return None
    if not _HAS_RESOURCE_MODULE:
        raise RuntimeError("cpu_limit/memory_limit_mb require a POSIX platform")

    def _apply() -> None:
        if cpu_limit is not None:
            cpu_seconds = int(cpu_limit)
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        if memory_limit_mb is not None:
            limit_bytes = memory_limit_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))

    return _apply


def exec_in_process(code: str) -> tuple[str, str | None]:
    """Run Python code with no process isolation and no resource limits — the
    'sandbox off' path for trusted, fast dev-time iteration (see the toggle on
    CodeExecEvaluator/CodeExecTool). No timeout protection either: bypassing
    the sandbox means bypassing the guarantees a subprocess boundary buys you.
    Returns (stdout, error_message_or_None).
    """
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            exec(code, {"__name__": "__main__"})  # noqa: S102 — this *is* the "sandbox off" path
    except Exception as exc:  # noqa: BLE001 — surface any failure as the tool/evaluator's error field
        return buffer.getvalue(), f"{type(exc).__name__}: {exc}"
    return buffer.getvalue(), None
