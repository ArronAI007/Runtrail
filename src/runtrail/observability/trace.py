import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class Trace:
    """One case's full execution record, identified by a unique trace_id and
    queryable on its own (Store.load_trace).

    `steps` carries whatever step-level detail an Agent chooses to report via
    output['steps'] — a list of dicts, e.g.:
      {"type": "thought", "content": "..."}
      {"type": "tool_call", "tool": "search", "args": {...}, "result": ..., "duration_ms": ...}
      {"type": "llm_call", "input": ..., "output": ..., "tokens": {"prompt_tokens":.., "completion_tokens":.., "total_tokens":..}}
    An Agent that just returns {"output": ...} still gets a full Trace — steps
    default to [] rather than being required.
    """

    case: dict
    output: dict
    evaluation: dict
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    steps: list[dict[str, Any]] = field(default_factory=list)
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
