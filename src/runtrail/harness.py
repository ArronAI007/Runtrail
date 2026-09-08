import uuid
from collections.abc import Callable
from datetime import datetime, timezone

from runtrail.agent.base import BaseAgent
from runtrail.agent.local_agent import LocalAgent
from runtrail.dataset.base import BaseDataset
from runtrail.evaluator.base import BaseEvaluator
from runtrail.observability.comparison import ComparisonReport
from runtrail.observability.reporter import Report
from runtrail.observability.trace import Trace
from runtrail.runtime.checkpoint import Checkpoint
from runtrail.runtime.queue import TaskQueue
from runtrail.runtime.task_runner import TaskRunner
from runtrail.storage.base import BaseStore


class Harness:
    """Runs an Agent against a Dataset under an Evaluator and produces a Report."""

    def __init__(self, store: BaseStore | None = None):
        self.store = store

    def run(
        self,
        agent: BaseAgent | Callable[..., dict],
        dataset: BaseDataset,
        evaluator: BaseEvaluator,
        *,
        queue: TaskQueue | None = None,
        checkpoint: Checkpoint | None = None,
    ) -> Report:
        if not isinstance(agent, BaseAgent):
            agent = LocalAgent(agent)

        run_id = str(uuid.uuid4())
        runner = TaskRunner(agent=agent, evaluator=evaluator)
        cases = list(dataset)
        completed = checkpoint.load() if checkpoint is not None else {}

        pending = [
            (str(index), case) for index, case in enumerate(cases) if str(index) not in completed
        ]

        def run_and_checkpoint(item: tuple[str, dict]) -> tuple[str, Trace]:
            case_id, case = item
            trace = runner.run_case(case)
            if checkpoint is not None:
                checkpoint.save_case(case_id, _trace_to_checkpoint_dict(trace))
            return case_id, trace

        if queue is not None:
            # A case can carry a "priority" field (higher runs first under queue's
            # bounded concurrency) — pending items are (case_id, case) tuples.
            fresh = dict(
                queue.map(run_and_checkpoint, pending, priority_key=lambda item: item[1].get("priority", 0))
            )
        else:
            fresh = dict(run_and_checkpoint(item) for item in pending)

        traces = [
            _trace_from_checkpoint(completed[str(index)])
            if str(index) in completed
            else fresh[str(index)]
            for index in range(len(cases))
        ]

        if self.store is not None:
            for trace in traces:
                self.store.save_result(
                    run_id,
                    trace.case,
                    trace.output,
                    trace.evaluation,
                    trace_id=trace.trace_id,
                    steps=trace.steps,
                    duration_ms=trace.duration_ms,
                )

        return Report(traces=traces)

    def compare(
        self,
        candidates: dict[str, BaseAgent | Callable[..., dict]],
        dataset: BaseDataset,
        evaluator: BaseEvaluator,
        *,
        queue: TaskQueue | None = None,
    ) -> ComparisonReport:
        """Run each candidate (a different model, a different Agent
        implementation, ...) against the same dataset/evaluator and return a
        side-by-side ComparisonReport — for A/B'ing models or prompts.
        """
        return ComparisonReport(
            reports={
                name: self.run(agent=agent, dataset=dataset, evaluator=evaluator, queue=queue)
                for name, agent in candidates.items()
            }
        )


def _trace_to_checkpoint_dict(trace: Trace) -> dict:
    return {
        "trace_id": trace.trace_id,
        "case": trace.case,
        "output": trace.output,
        "evaluation": trace.evaluation,
        "steps": trace.steps,
        "duration_ms": trace.duration_ms,
        "timestamp": trace.timestamp.isoformat(),
    }


def _trace_from_checkpoint(saved: dict) -> Trace:
    return Trace(
        case=saved["case"],
        output=saved["output"],
        evaluation=saved["evaluation"],
        trace_id=saved.get("trace_id", str(uuid.uuid4())),
        steps=saved.get("steps", []),
        duration_ms=saved.get("duration_ms", 0.0),
        timestamp=datetime.fromisoformat(saved["timestamp"]).astimezone(timezone.utc),
    )
