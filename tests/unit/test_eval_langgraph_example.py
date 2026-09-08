import sys
from pathlib import Path

import pytest

pytest.importorskip("langgraph")

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "examples"))
import eval_langgraph_agent


def test_langgraph_agent_wrapper_runs_a_real_compiled_graph_through_harness():
    from runtrail import Harness, SimpleEvaluator

    agent = eval_langgraph_agent.LangGraphAgent(eval_langgraph_agent._build_graph())
    report = Harness().run(
        agent=agent, dataset=eval_langgraph_agent.DATASET, evaluator=SimpleEvaluator()
    )

    assert report.passed == 2
    assert report.total == 2
