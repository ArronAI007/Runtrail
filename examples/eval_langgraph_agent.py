"""Evaluate a LangGraph agent two ways: in-process (wrap the compiled graph
directly) or over HTTP (if it's served, e.g. via LangServe). See
docs/eval_langgraph.md for the full walkthrough. Requires `pip install
langgraph` for the in-process path.
"""

from typing import Any, TypedDict

from runtrail import Harness, SimpleEvaluator
from runtrail.agent.base import BaseAgent
from runtrail.agent.remote_agent import RemoteAgent
from runtrail.dataset import InMemoryDataset


class State(TypedDict):
    question: str
    answer: str


def _build_graph() -> Any:
    from langgraph.graph import END, StateGraph

    def solve(state: State) -> State:
        if "2+2" in state["question"]:
            return {"answer": "4"}
        return {"answer": "unknown"}

    graph = StateGraph(State)
    graph.add_node("solve", solve)
    graph.set_entry_point("solve")
    graph.add_edge("solve", END)
    return graph.compile()


class LangGraphAgent(BaseAgent):
    """Wraps a compiled LangGraph graph as a BaseAgent — no HTTP hop, runs
    in-process. `run()`'s job is just translating Runtrail's plain-string
    `task_input` into your graph's State shape and back.
    """

    def __init__(self, compiled_graph: Any):
        self.compiled_graph = compiled_graph

    def run(self, task_input: str) -> dict:
        result = self.compiled_graph.invoke({"question": task_input, "answer": ""})
        return {"output": result["answer"]}


DATASET = InMemoryDataset(
    [
        {"input": "what is 2+2", "ground_truth": "4"},
        {"input": "something unknowable", "ground_truth": "unknown"},
    ]
)


def eval_in_process() -> None:
    agent = LangGraphAgent(_build_graph())
    report = Harness().run(agent=agent, dataset=DATASET, evaluator=SimpleEvaluator())
    print("in-process:", report.summary())


def eval_over_http() -> None:
    # If your graph is served (e.g. `langgraph_sdk`/LangServe exposing
    # POST /invoke), RemoteAgent needs no LangGraph-specific code at all —
    # it just POSTs {"input": task_input} and expects {"output": ...} back.
    agent = RemoteAgent(endpoint="http://localhost:8080/invoke")
    report = Harness().run(agent=agent, dataset=DATASET, evaluator=SimpleEvaluator())
    print("remote:", report.summary())


if __name__ == "__main__":
    eval_in_process()
    # eval_over_http()  # needs a real server at the endpoint above
