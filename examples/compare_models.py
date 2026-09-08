"""Batch-compare different models/Agent implementations against the same
dataset and get a one-shot comparison report. Swap the two toy agents below
for e.g. two LiteLLMAdapter-backed agents on different models.
"""

from runtrail import Harness, SimpleEvaluator
from runtrail.dataset import InMemoryDataset

DATASET = InMemoryDataset(
    [
        {"input": "2+2", "ground_truth": "4"},
        {"input": "capital of France", "ground_truth": "Paris"},
    ]
)


def model_a_agent(task_input: str) -> dict:
    answers = {"2+2": "4", "capital of France": "Paris"}
    return {"output": answers.get(task_input, "unknown")}


def model_b_agent(task_input: str) -> dict:
    return {"output": "I'm not sure"}


if __name__ == "__main__":
    comparison = Harness().compare(
        {"model-a": model_a_agent, "model-b": model_b_agent},
        DATASET,
        SimpleEvaluator(),
    )
    print(comparison.summary_table())
    print(f"\nbest candidate: {comparison.best()}")
    comparison.to_json("./output/comparison.json")
