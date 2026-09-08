# HITL 人在回路使用指南

Runtrail 支持半自动评测流水线：自动评估未能确定的用例转入人工复核队列。

```python
from runtrail.hitl.hitl_service import HITLService

service = HITLService(store=harness.store)
service.enqueue_for_review(report.uncertain_cases())
```

启动 Web UI（`runtrail ui`）后，标注员可以在 `/` 页面看到复核队列，通过 `POST /api/reviews/{review_id}/annotate` 提交打分（也可以直接用 `HITLService.submit_annotation` 走代码路径）。`/api/runs/{run_id}` 可查看某次运行的完整结果。详见 [架构文档](architecture.md)。

标注数据回流训练/微调 Judge 模型这一环，目前还没有实现——`HITLService` 只负责队列和标注的存取，不做任何自动回流。
