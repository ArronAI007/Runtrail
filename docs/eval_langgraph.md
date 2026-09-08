# 教程：评测一个 LangGraph Agent

Runtrail 不关心你的 Agent 是怎么实现的——只要能塞进 `BaseAgent.run(task_input) -> dict` 或者一个 HTTP 端点，就能跑评测。LangGraph 有两种典型接入方式，选哪种取决于你的图跑在哪。

## 方式一：进程内直接跑图（推荐，最快）

如果你的 LangGraph 图和评测代码在同一个 Python 环境里，直接包一层 `BaseAgent`，完全不用起 HTTP 服务：

```python
from typing import Any, TypedDict

from langgraph.graph import StateGraph, END
from runtrail.agent.base import BaseAgent


class State(TypedDict):
    question: str
    answer: str


def solve(state: State) -> State:
    # 你的图节点逻辑
    return {"answer": "..."}


graph = StateGraph(State)
graph.add_node("solve", solve)
graph.set_entry_point("solve")
graph.add_edge("solve", END)
compiled_graph = graph.compile()


class LangGraphAgent(BaseAgent):
    """run() 的活就是把 Runtrail 的纯字符串 task_input 翻译成图的 State，再把
    图的输出翻译回 Runtrail 期望的 {"output": ...} 形状。"""

    def __init__(self, compiled_graph: Any):
        self.compiled_graph = compiled_graph

    def run(self, task_input: str) -> dict:
        result = self.compiled_graph.invoke({"question": task_input, "answer": ""})
        return {"output": result["answer"]}
```

跑评测和跑任何其他 Agent 一模一样：

```python
from runtrail import Harness, SimpleEvaluator
from runtrail.dataset import InMemoryDataset

dataset = InMemoryDataset([{"input": "what is 2+2", "ground_truth": "4"}])
report = Harness().run(agent=LangGraphAgent(compiled_graph), dataset=dataset, evaluator=SimpleEvaluator())
print(report.summary())
```

这个模式已经用真实的 `langgraph` 包（`pip install langgraph`，测试锁定 `langgraph>=0.2`）跑通并纳入单元测试：见 `examples/eval_langgraph_agent.py` 的 `eval_in_process()` 和 `tests/unit/test_eval_langgraph_example.py`。

## 方式二：图已经用 HTTP 服务对外提供（LangServe 等）

如果图跑在别的进程/机器上，用 `RemoteAgent`——不需要任何 LangGraph 专用代码，`RemoteAgent` 只是 POST `{"input": task_input}` 并期望拿到 `{"output": ...}`：

```python
from runtrail.agent import RemoteAgent

agent = RemoteAgent(endpoint="http://localhost:8080/invoke")
report = Harness().run(agent=agent, dataset=dataset, evaluator=SimpleEvaluator())
```

如果你的服务端点不是这个请求/响应形状（比如 LangServe 默认的 `/invoke` 走的是 `{"input": {...}}` 包一层、返回 `{"output": {...}}`），在 `RemoteAgent` 和图之间加一层薄适配——最简单的办法是自己写个 `BaseAgent` 内部持有一个 `httpx.Client`，按你服务端点的实际协议整形请求体，其余复用 `RemoteAgent` 的思路（见 `src/runtrail/agent/remote_agent.py`）。

## 选哪个？

- 能进程内跑就进程内跑（方式一）——没有网络往返，`Trace.duration_ms` 测的是图本身的耗时，不掺杂 HTTP 开销。
- 图部署在别处、或者故意要测"网络这一段"（超时、重试、服务端崩溃）时用方式二，配合 `RemoteAgent` 天然的异常处理（`TaskRunner` 会把连接失败/超时都记成一个失败 case，不会打断整批评测）。

## 下一步

- [接口扩展](extend.md)：想给 Agent 加分步 Trace（`output['steps']`）、接自定义 Evaluator，看这里
- [工具混沌测试](api.md#runtrailtoolkit)：用 `ToolMock` 测试图里某个工具节点返回超时/乱码时 Agent 的表现
- [HITL 指南](hitl.md)：LangGraph Agent 评测出的失败案例，怎么转人工复核
