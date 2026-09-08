# 接口扩展：自定义 Agent / Evaluator / Dataset / Tool / Store

Runtrail 不内置业务 Agent，所有扩展点都是抽象基类，继承即可，无需修改框架源码。这一页覆盖全部五个扩展点；HITL 流水线单独看 [HITL 指南](hitl.md)，评测 LangGraph Agent 单独看 [LangGraph 教程](eval_langgraph.md)。

## 自定义 Agent

最简单的情况——一个普通函数就够，`Harness` 会自动用 `LocalAgent` 包装：

```python
def my_agent(task_input: str) -> dict:
    return {"output": "..."}

Harness().run(agent=my_agent, dataset=ds, evaluator=SimpleEvaluator())
```

需要状态、配置、或想显式实现接口时，继承 `BaseAgent`：

```python
from runtrail.agent.base import BaseAgent

class MyAgent(BaseAgent):
    def __init__(self, model: str):
        self.model = model

    def run(self, task_input: str) -> dict:
        return {"output": ...}
```

### 报告分步 Trace（可选）

`output` dict 里加一个 `"steps"` 键，`TaskRunner` 会自动摘出来存进 `Trace.steps`（不会污染 `output` 本身），Web UI 的 Trace 详情页会渲染它，`Report.stats()`/`OTelMetrics` 会汇总里面的 `tokens.total_tokens`：

```python
def my_agent(task_input: str) -> dict:
    return {
        "output": "42",
        "steps": [
            {"type": "thought", "content": "..."},
            {"type": "tool_call", "tool": "search", "args": {...}, "result": ...},
            {"type": "llm_call", "input": ..., "output": ..., "tokens": {"total_tokens": 120}},
        ],
    }
```

不加这个键完全没问题——`Trace.steps` 就是空列表，其余功能照常。

## 自定义 Evaluator

```python
from runtrail.evaluator.base import BaseEvaluator

class MyEvaluator(BaseEvaluator):
    def evaluate(self, output: dict, ground_truth) -> dict:
        return {"passed": ..., "score": ...}
```

返回值里如果带 `"failure_category"`，会被当作 `FailureClassifier` 已经归因过，不会再自动覆盖；不带的话失败用例会自动过一遍 `FailureClassifier`（规则匹配版，见 [API Reference](api.md)）。

## 自定义 Dataset

```python
from collections.abc import Iterator
from runtrail.dataset.base import BaseDataset

class MyDataset(BaseDataset):
    def __iter__(self) -> Iterator[dict]:
        yield {"input": ..., "ground_truth": ...}

    def __len__(self) -> int:
        ...
```

每条 case 还可以带 `"priority"` 字段（整数，越大越先跑）——配合 `Harness.run(queue=TaskQueue(...))` 时会真正影响调度顺序，见 [TaskQueue API](api.md#runtrailruntimetaskqueue)。

## 自定义 Tool

```python
from runtrail.toolkit.base_tool import BaseTool

class MyTool(BaseTool):
    name = "my_tool"

    def call(self, **kwargs) -> Any:
        ...
```

想在测试里注入故障（超时/异常/乱码），不用改 Agent 代码，用 `ToolMock` 包一层：

```python
from runtrail.toolkit import ToolMock

chaos_tool = ToolMock("my_tool", wrapped=MyTool(), raise_=TimeoutError(...), failure_rate=0.3)
```

## 自定义 Store

```python
from runtrail.storage.base import BaseStore

class MyStore(BaseStore):
    def save_result(self, run_id, case, output, evaluation, *, trace_id=None, steps=None, duration_ms=None): ...
    def load_run(self, run_id) -> list[dict]: ...
    def load_trace(self, trace_id) -> dict | None: ...
    def list_runs(self) -> list[dict]: ...
    def overall_stats(self) -> dict: ...
    def enqueue_review(self, case, output, evaluation) -> str: ...
    def list_pending_reviews(self) -> list[dict]: ...
    def record_annotation(self, review_id, annotation) -> None: ...
    def close(self) -> None: ...
```

九个方法都要实现——`SQLiteStore`/`PostgresStore` 是参考实现，字段形状完全一致，抄它们的 schema 改存储后端最快。`BaseStore` 自带 `__enter__`/`__exit__`，实现了 `close()` 就能 `with MyStore(...) as store:` 用。
