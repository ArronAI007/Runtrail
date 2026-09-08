"""Evaluate a multi-Agent DAG: planner produces a plan, executor acts on it."""

from runtrail.runtime.dag_engine import DAGEngine, DAGNode


def planner_agent(_task_input: str) -> dict:
    return {"plan": "gather requirements, then draft a proposal"}


def executor_agent(upstream: dict) -> dict:
    return {"result": f"executed: {upstream['planner']['plan']}"}


if __name__ == "__main__":
    dag = {
        "planner": DAGNode(agent=planner_agent, depends_on=[]),
        "executor": DAGNode(agent=executor_agent, depends_on=["planner"]),
    }
    outputs = DAGEngine().run(dag)
    print(outputs)
