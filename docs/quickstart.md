# 快速入门

## 安装

```bash
pip install runtrail
```

## 运行第一个评测

```python
from runtrail import Harness, SimpleEvaluator
from runtrail.dataset import InMemoryDataset

def my_agent(task_input: str):
    return {"output": f"reply for: {task_input}"}

ds = InMemoryDataset([{"input": "what is 2+2", "ground_truth": "4"}])

harness = Harness()
report = harness.run(agent=my_agent, dataset=ds, evaluator=SimpleEvaluator())

print(report.summary())
report.to_json("./output/report.json")
```

## 下一步

- [核心概念](core_concepts.md) 了解 Agent / Evaluator / Dataset / Storage 的分层设计
- [接口扩展](extend.md) 接入你自己的 Agent
- [HITL 指南](hitl.md) 加入人工复核
