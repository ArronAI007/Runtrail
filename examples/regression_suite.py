"""Track a historical case set across Agent changes and fail loudly if a
previously-passing case regresses — the Agent analogue of a unit-test
regression suite. Run once to seed the baseline, then again after any
prompt/code change:

    python examples/regression_suite.py --save-baseline   # first run
    python examples/regression_suite.py                   # after a change
"""

import sys

from runtrail import Harness, SimpleEvaluator
from runtrail.dataset import InMemoryDataset
from runtrail.runtime.regression import RegressionSuite

REGRESSION_CASES = [
    {"input": "what is 2+2", "ground_truth": "4"},
    {"input": "capital of France", "ground_truth": "Paris"},
]


_ANSWERS = {"what is 2+2": "4", "capital of France": "Paris"}


def my_agent(task_input: str) -> dict:
    return {"output": _ANSWERS.get(task_input, "unknown")}


if __name__ == "__main__":
    report = Harness().run(
        agent=my_agent,
        dataset=InMemoryDataset(REGRESSION_CASES),
        evaluator=SimpleEvaluator(),
    )
    print(report.summary())

    suite = RegressionSuite("quickstart_agent")

    if "--save-baseline" in sys.argv or not suite.has_baseline():
        suite.save_baseline(report)
        print("baseline saved")
    else:
        result = suite.check(report)
        print(result.summary())
        if result.regressed:
            raise SystemExit(1)
