"""Chaos-test an Agent's tool-use against a flaky/slow/garbled tool, without
depending on any real external service.
"""

from runtrail import Harness, SimpleEvaluator
from runtrail.dataset import InMemoryDataset
from runtrail.toolkit import LocalFunctionTool, ToolMock


def real_search(q: str) -> str:
    return f"real search result for {q}"


def make_agent(tool):
    def agent(task_input: str) -> dict:
        try:
            result = tool.call(q=task_input)
        except (TimeoutError, ConnectionError) as exc:
            return {"output": f"fallback: tool failed ({exc})"}
        return {"output": result}

    return agent


if __name__ == "__main__":
    dataset = InMemoryDataset([{"input": "weather", "ground_truth": "fallback: tool failed"}])

    flaky_tool = ToolMock(
        "search",
        wrapped=LocalFunctionTool("search", real_search),
        raise_=ConnectionError("simulated network failure"),
        failure_rate=1.0,
    )

    report = Harness().run(
        agent=make_agent(flaky_tool),
        dataset=dataset,
        evaluator=SimpleEvaluator(rule=lambda output, gt: str(output).startswith(gt)),
    )
    print(report.summary())
