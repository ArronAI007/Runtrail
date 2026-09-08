import importlib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from runtrail.agent.base import BaseAgent
from runtrail.agent.local_agent import LocalAgent


@dataclass
class DAGNode:
    """One node in a task DAG: an Agent plus its upstream dependencies.

    If `input` is left as None, the node receives a dict of its dependencies'
    outputs keyed by node name — this is the DAG's Agent-to-Agent message routing.
    """

    agent: BaseAgent | Callable[..., dict]
    depends_on: list[str] = field(default_factory=list)
    input: Any = None


class DAGEngine:
    """Orchestrates multi-Agent task DAGs: runs nodes in dependency order and
    routes each node's upstream outputs to it as input.
    """

    def __init__(self, nodes: dict[str, DAGNode] | None = None):
        self.nodes = nodes or {}

    @classmethod
    def from_yaml(cls, path: str | Path) -> "DAGEngine":
        """Build a DAGEngine from a declarative YAML task definition, e.g.:

        nodes:
          planner:
            agent: my_pkg.agents:planner_agent
            depends_on: []
          executor:
            agent: my_pkg.agents:executor_agent
            depends_on: [planner]

        `agent` is a "module.path:attribute" reference to a callable or BaseAgent
        instance. Requires the 'yaml' extra: pip install 'runtrail[yaml]'.
        """
        try:
            import yaml
        except ImportError as exc:
            raise ImportError(
                "DAGEngine.from_yaml requires the 'yaml' extra: pip install 'runtrail[yaml]'"
            ) from exc

        spec = yaml.safe_load(Path(path).read_text())
        nodes = {
            name: DAGNode(
                agent=_import_ref(node_spec["agent"]),
                depends_on=list(node_spec.get("depends_on", [])),
                input=node_spec.get("input"),
            )
            for name, node_spec in spec.get("nodes", {}).items()
        }
        return cls(nodes)

    def run(self, dag: dict[str, DAGNode] | None = None) -> dict[str, dict]:
        nodes = dag if dag is not None else self.nodes
        order = _topological_order(nodes)

        outputs: dict[str, dict] = {}
        for name in order:
            node = nodes[name]
            agent = node.agent if isinstance(node.agent, BaseAgent) else LocalAgent(node.agent)
            task_input = node.input
            if task_input is None and node.depends_on:
                task_input = {dep: outputs[dep] for dep in node.depends_on}
            outputs[name] = agent.run(task_input)

        return outputs


def _topological_order(nodes: dict[str, DAGNode]) -> list[str]:
    for node in nodes.values():
        for dep in node.depends_on:
            if dep not in nodes:
                raise ValueError(f"DAG references unknown dependency '{dep}'")

    in_degree = {name: len(node.depends_on) for name, node in nodes.items()}
    dependents: dict[str, list[str]] = {name: [] for name in nodes}
    for name, node in nodes.items():
        for dep in node.depends_on:
            dependents[dep].append(name)

    queue = [name for name, degree in in_degree.items() if degree == 0]
    order: list[str] = []
    while queue:
        name = queue.pop(0)
        order.append(name)
        for dependent in dependents[name]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    if len(order) != len(nodes):
        raise ValueError("DAG contains a cycle")

    return order


def _import_ref(ref: str) -> Any:
    module_path, sep, attr = ref.partition(":")
    if not sep:
        module_path, _, attr = ref.rpartition(".")
    module = importlib.import_module(module_path)
    return getattr(module, attr)
