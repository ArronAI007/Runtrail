import pytest

from runtrail.runtime.dag_engine import DAGEngine, DAGNode


def test_run_executes_nodes_in_dependency_order_and_routes_outputs():
    calls = []

    def planner(_task_input):
        calls.append("planner")
        return {"plan": "do the thing"}

    def executor(upstream):
        calls.append("executor")
        return {"result": f"executed based on {upstream['planner']['plan']}"}

    dag = {
        "planner": DAGNode(agent=planner, depends_on=[]),
        "executor": DAGNode(agent=executor, depends_on=["planner"]),
    }

    outputs = DAGEngine().run(dag)

    assert calls == ["planner", "executor"]
    assert outputs["executor"]["result"] == "executed based on do the thing"


def test_run_raises_on_unknown_dependency():
    dag = {"a": DAGNode(agent=lambda x: {}, depends_on=["missing"])}

    with pytest.raises(ValueError, match="unknown dependency"):
        DAGEngine().run(dag)


def test_run_raises_on_cycle():
    dag = {
        "a": DAGNode(agent=lambda x: {}, depends_on=["b"]),
        "b": DAGNode(agent=lambda x: {}, depends_on=["a"]),
    }

    with pytest.raises(ValueError, match="cycle"):
        DAGEngine().run(dag)


def test_from_yaml_builds_and_runs_a_declarative_dag(tmp_path):
    yaml_path = tmp_path / "dag.yaml"
    yaml_path.write_text(
        "nodes:\n"
        "  planner:\n"
        "    agent: tests.unit.fixtures.dag_agents:planner_agent\n"
        "    depends_on: []\n"
        "  executor:\n"
        "    agent: tests.unit.fixtures.dag_agents:executor_agent\n"
        "    depends_on: [planner]\n"
    )

    outputs = DAGEngine.from_yaml(yaml_path).run()

    assert outputs["executor"]["result"] == "executed based on do the thing"
