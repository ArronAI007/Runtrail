# 核心概念

Runtrail 围绕五个可插拔抽象展开，全部位于 `src/runtrail/*/base.py`：

| 抽象 | 职责 | 内置实现 |
|------|------|----------|
| `BaseAgent` | 接收任务输入，返回 Agent 输出 | `LocalAgent`、`SubprocessAgent`、`RemoteAgent` |
| `BaseEvaluator` | 对 Agent 输出打分/判定通过与否 | `RuleEvaluator`、`LLMJudge`、`CodeExecEvaluator` |
| `BaseDataset` | 提供评测用例（input / ground_truth） | `InMemoryDataset`、`FileDataset`、`BenchmarkAdapter` |
| `BaseTool` | Agent 可调用的外部工具 | `LocalFunctionTool`、`MCPAdapter`、`OpenAPIAdapter`、`CodeExecTool`、`ToolMock` |
| `BaseStore` | 持久化 Trace 与评测结果 | `SQLiteStore`、`PostgresStore` |

## 执行流程

1. `Harness.run()` 从 `Dataset` 取出用例（`Harness.compare()` 对多个候选 Agent/模型各跑一遍）
2. 依次（或按 DAG）调用 `Agent`，记录完整 `Trace`（含 `trace_id`/耗时/可选的分步 `steps`）
3. `Evaluator` 对每条结果打分，失败时自动触发 `FailureClassifier` 归因
4. 结果写入 `Store`，并生成 `Report`（JSON/CSV/失败用例 JSONL；Markdown/HTML 尚未实现）

详见 [架构文档](architecture.md)。
