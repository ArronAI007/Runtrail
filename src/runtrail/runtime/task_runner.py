import time

from runtrail.agent.base import BaseAgent
from runtrail.evaluator.base import BaseEvaluator
from runtrail.evaluator.failure_classifier import FailureClassifier
from runtrail.observability.trace import Trace


class TaskRunner:
    """Runs a single task case through an Agent and Evaluator, producing a Trace.

    A failed case (Agent exception, or evaluator reporting passed=False) gets an
    automatic 'failure_category' tag from FailureClassifier. Wall-clock duration
    is always measured; step-level detail is read from output['steps'] if the
    Agent reports it (see Trace's docstring for the shape).
    """

    def __init__(
        self,
        agent: BaseAgent,
        evaluator: BaseEvaluator,
        failure_classifier: FailureClassifier | None = None,
    ):
        self.agent = agent
        self.evaluator = evaluator
        self.failure_classifier = failure_classifier or FailureClassifier()

    def run_case(self, case: dict) -> Trace:
        start = time.perf_counter()
        try:
            output = self.agent.run(case["input"])
        except Exception as exc:  # noqa: BLE001 — any Agent failure must not abort the batch
            duration_ms = (time.perf_counter() - start) * 1000
            evaluation = {"passed": False, "score": 0.0, "error": f"{type(exc).__name__}: {exc}"}
            evaluation["failure_category"] = self.failure_classifier.classify({}, evaluation)
            return Trace(case=case, output={}, evaluation=evaluation, duration_ms=duration_ms)

        duration_ms = (time.perf_counter() - start) * 1000
        steps, output = _extract_steps(output)

        evaluation = self.evaluator.evaluate(output, case.get("ground_truth"))
        if not evaluation.get("passed", True):
            evaluation = {
                **evaluation,
                "failure_category": self.failure_classifier.classify(output, evaluation),
            }
        return Trace(case=case, output=output, evaluation=evaluation, steps=steps, duration_ms=duration_ms)


def _extract_steps(output: dict) -> tuple[list[dict], dict]:
    if not isinstance(output, dict) or "steps" not in output:
        return [], output
    steps = output["steps"]
    clean_output = {k: v for k, v in output.items() if k != "steps"}
    return steps, clean_output
