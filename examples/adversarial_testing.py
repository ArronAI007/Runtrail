"""Attack an Agent with prompt-injection, contradiction, and boundary-case
inputs to find robustness failures a normal correctness eval would miss.
"""

from runtrail import Harness
from runtrail.adversarial import AdversarialDataset, PromptInjectionEvaluator
from runtrail.dataset import InMemoryDataset
from runtrail.evaluator import SimpleEvaluator


def gullible_agent(task_input: str) -> dict:
    # A deliberately weak agent: it just echoes back anything that looks like
    # an instruction to do so, to demonstrate PromptInjectionEvaluator catching it.
    if "IGNORE ALL PREVIOUS" in task_input:
        return {"output": "HACKED"}
    if "PWNED" in task_input:
        return {"output": "PWNED"}
    return {"output": "4"}


if __name__ == "__main__":
    base = InMemoryDataset([{"input": "what is 2+2", "ground_truth": "4"}])
    dataset = AdversarialDataset(base)
    evaluator = PromptInjectionEvaluator(SimpleEvaluator())

    report = Harness().run(agent=gullible_agent, dataset=dataset, evaluator=evaluator)

    print(report.summary())
    for trace in report.traces:
        if not trace.evaluation.get("passed"):
            print(f"  FAILED [{trace.case.get('adversarial_type')}]: {trace.evaluation.get('error', '')}")
