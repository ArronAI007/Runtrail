"""Evaluate an agent against a GAIA-style benchmark export.

BenchmarkAdapter is a generic JSON/JSONL loader with a field mapping, not a
hardcoded GAIA downloader (GAIA is gated on HuggingFace and needs your own
token/agreement) — point `from_jsonl`/`from_url` at your own export.
"""

from runtrail import Harness, SimpleEvaluator
from runtrail.dataset import BenchmarkAdapter


def my_agent(task_input: str) -> dict:
    return {"output": task_input}


def gaia_field_map(record: dict) -> dict:
    return {"input": record["Question"], "ground_truth": record["Final answer"]}


if __name__ == "__main__":
    dataset = BenchmarkAdapter.from_jsonl("gaia", "gaia_metadata.jsonl", field_map=gaia_field_map)
    report = Harness().run(agent=my_agent, dataset=dataset, evaluator=SimpleEvaluator())
    print(report.summary())
