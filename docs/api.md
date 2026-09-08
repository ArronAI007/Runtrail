# API Reference

## `runtrail.Harness`

| 方法 | 说明 |
|------|------|
| `run(agent, dataset, evaluator, *, queue=None, checkpoint=None) -> Report` | 对数据集中的每条用例执行 Agent 并评估，返回汇总报告；`queue` 传 `TaskQueue` 启用并发，`checkpoint` 传 `Checkpoint` 启用断点续跑。case 里带 `"priority"` 字段（数值越大越先跑）会被 `queue` 用来排序 |
| `compare(candidates, dataset, evaluator, *, queue=None) -> ComparisonReport` | `candidates` 是 `{名字: agent}`，对每个候选跑一遍 `run()`，返回可一键对比的 `ComparisonReport` |

`Harness(store=...)` 传入 `BaseStore` 时，每条 Trace（含 `trace_id`/`steps`/`duration_ms`）都会持久化。

## `runtrail.observability.ComparisonReport`

`Harness.compare()` 的返回值：

| 方法 | 说明 |
|------|------|
| `.reports: dict[str, Report]` | 每个候选各自的完整 `Report` |
| `best(key="pass_rate") -> str` | 按某个 `stats()` 指标取最优候选名 |
| `summary_table() -> str` | ASCII 对比表（candidate/pass_rate/avg_duration_ms/total_tokens），适合 CLI 打印 |
| `to_dict()` / `to_json(path)` | 每个候选的 `stats()`，供横向对比报告落盘 |

## `runtrail.observability.Trace`

一条用例的完整执行记录：`trace_id`（自动生成的唯一 ID）、`case`、`output`、`evaluation`、`steps`（见下）、`duration_ms`（TaskRunner 自动测量的墙钟耗时）、`timestamp`。

### `steps` 约定

Agent 在返回的 dict 里加一个 `"steps"` 键（一个 `list[dict]`），TaskRunner 会把它摘出来存进 `Trace.steps`，不会污染 `output`。没有这个键的 Agent 仍然拿到完整 Trace，只是 `steps=[]`。常见的 step 形状：

```python
{"type": "thought", "content": "..."}
{"type": "tool_call", "tool": "search", "args": {...}, "result": ..., "duration_ms": ...}
{"type": "llm_call", "input": ..., "output": ..., "tokens": {"prompt_tokens": .., "completion_tokens": .., "total_tokens": ..}}
```

`Report.stats()`/`OTelMetrics` 会把 `tokens.total_tokens` 汇总成总 token 消耗。

## `runtrail.observability.Report`

| 方法 | 说明 |
|------|------|
| `summary() -> str` | 人类可读的评测摘要 |
| `stats() -> dict` | 聚合指标：`total`/`passed`/`pass_rate`/`avg_duration_ms`/`avg_steps`/`total_tokens`/`failure_category_counts` |
| `uncertain_cases() -> list[dict]` | 失败用例，直接喂给 `HITLService.enqueue_for_review()` |
| `to_json(path)` | 导出为 JSON 报告（含每条 case 的 `trace_id`/`ground_truth`/`steps`/`duration_ms`） |
| `Report.from_json(path)`（classmethod） | 反序列化 `to_json()` 产物，重建 `Report`——`runtrail report`、`RegressionSuite`、CI 里比较两次运行都靠它 |
| `to_csv(path)` | 导出为 CSV（trace_id/input/output/passed/score/failure_category/duration_ms） |
| `export_failures_jsonl(path) -> int` | 只导出失败用例的 JSONL（input/ground_truth/output/evaluation），供微调/提示词优化用；返回写入条数 |
| `to_markdown(path)` | 导出 Markdown 报告（摘要表格 + 故障分类 + 失败用例明细），适合贴进 PR 描述/论文/内部汇报 |
| `to_html(path)` | 导出独立的 HTML 报告（内联 CSS，无外部资源，浏览器直接打开），内容做了 HTML 转义 |

## `runtrail.evaluator`

| 类 | 说明 |
|------|------|
| `SimpleEvaluator` | 精确字符串匹配 |
| `NormalizedMatchEvaluator` | 大小写/空白不敏感匹配 |
| `JSONSchemaEvaluator(schema)` | 校验 `output` 是否符合 JSON Schema（需要 `runtrail[schema]`） |
| `ToolCallEvaluator` | 比对 `output['tool_calls']` 与期望调用序列，产出 `tool_call_accuracy` |
| `CodeExecEvaluator(timeout_sec=10.0, *, sandbox=True, cpu_limit=None, memory_limit_mb=None)` | 执行 `output` 里的 Python 代码并比对 stdout；`sandbox=True` 走 subprocess（可选 CPU/内存限制），`sandbox=False` 走进程内 `exec()`（无隔离，仅供开发环境跑可信代码） |
| `LLMJudge(model, *, rubric=None, gateway=None)` | LLM‑as‑Judge，默认走 `LiteLLMAdapter`；返回值带 `tokens`（如果网关支持 `complete_with_usage`） |
| `FailureClassifier` | 对失败用例打 `failure_category` 标签，已自动接入 `TaskRunner` |

## `runtrail.gateway.LiteLLMAdapter`

`LiteLLMAdapter(model, **litellm_kwargs)`：不重复造模型网关，直接透传给 `litellm.completion()`。`complete(prompt) -> str`；`complete_with_usage(prompt) -> (str, dict)` 额外返回真实 `{prompt_tokens, completion_tokens, total_tokens}`。传 `api_base`/`api_key` 可指向 One-API 等 OpenAI 兼容网关，不用直连某个厂商。需要 `runtrail[gateway]`。

## `runtrail.toolkit`

| 类 | 说明 |
|------|------|
| `LocalFunctionTool(name, fn)` | 把一个普通 Python 函数包成 `BaseTool` |
| `OpenAPIAdapter(spec, operation_id, *, base_url=None)` / `.from_url(spec_url, operation_id)` | 调用 OpenAPI 3.x 规范里的一个 operation；只支持 path/query 参数 + JSON body，不解析跨文件 `$ref`。需要 `runtrail[remote]` |
| `MCPAdapter(command, tool_name, *, default_args=None)` | 通过 stdio 调用 MCP 服务器上的一个 tool；每次 `call()` 起一个新的服务器子进程会话，无持久连接。需要 `runtrail[mcp]`（锁定 mcp 1.x，2.x 把 `FastMCP` 重命名成 `MCPServer` 是破坏性变更） |
| `CodeExecTool(timeout_sec=10.0, *, sandbox=True, cpu_limit=None, memory_limit_mb=None)` | 执行 `call(code=...)` 传入的 Python 代码，返回 `{stdout, stderr, returncode}`；`sandbox`/`cpu_limit`/`memory_limit_mb` 语义同 `CodeExecEvaluator` |
| `ToolMock(name, *, wrapped=None, fake_response=None, raise_=None, delay_sec=0.0, timeout_after_sec=None, garble=False, failure_rate=1.0)` | 工具故障注入：固定假返回、抛异常、模拟超时（真实 `sleep` 后 `raise TimeoutError`）、`garble=True` 模拟乱码返回；传 `wrapped=` 一个真实 `BaseTool` 时按 `failure_rate` 概率在真实调用和故障之间切换 |

## `runtrail.dataset`

| 类 | 说明 |
|------|------|
| `InMemoryDataset(cases)` | 接收 `list[dict]`，每条记录至少包含 `input`，可选 `ground_truth` |
| `FileDataset(path)` | 本地 JSONL 文件 |
| `BenchmarkAdapter.from_jsonl/from_url(name, path_or_url, field_map=None)` | 通用 GAIA/AgentBench 兼容加载器 |
| `PerturbedDataset(base, perturb)` | 对每条用例的 `input` 做任务级扰动测试 |

## `runtrail.storage.BaseStore`

`SQLiteStore`（零配置）与 `PostgresStore`（生产）都实现：

| 方法 | 说明 |
|------|------|
| `save_result(run_id, case, output, evaluation, *, trace_id=None, steps=None, duration_ms=None)` | 持久化一条结果 |
| `load_run(run_id) -> list[dict]` | 某次运行的全部 Trace |
| `load_trace(trace_id) -> dict \| None` | 按 `trace_id` 查询单条 Trace |
| `list_runs() -> list[dict]` | 所有 run 的 `{run_id, total, passed, pass_rate}` 概览——Web UI 的任务列表数据源 |
| `overall_stats() -> dict` | 跨所有 run 的聚合统计——Web UI 仪表盘数据源 |
| `enqueue_review`/`list_pending_reviews`/`record_annotation` | HITL 队列 |

## `runtrail.runtime.TaskQueue`

`TaskQueue(max_concurrency=1, rate_limit_per_sec=None, max_retries=0, backoff_base_sec=1.0)`：自建的优先级堆调度（不是 `ThreadPoolExecutor` 的纯 FIFO），失败自动指数退避重试。

| 方法 | 说明 |
|------|------|
| `submit(fn, *args, priority=0, **kwargs) -> Future` | `priority` 越大越先被 worker 取走执行（同优先级按提交顺序） |
| `map(fn, items, *, priority_key=None) -> list` | `priority_key(item) -> int` 决定每项的优先级；`Harness.run(queue=...)` 用它读取每条 case 的 `"priority"` 字段 |
| `shutdown(wait=True)` | 停掉所有 worker 线程 |

## `runtrail.security.sandbox`

`SubprocessAgent`/`CodeExecEvaluator`/`CodeExecTool` 共享的沙箱基础设施：

| 函数 | 说明 |
|------|------|
| `resource_limit_preexec_fn(cpu_limit, memory_limit_mb) -> Callable \| None` | 构造一个 `subprocess.run(preexec_fn=...)`，用 POSIX rlimit 限制 CPU/内存；都为 `None` 时返回 `None`。`memory_limit_mb`（`RLIMIT_AS`）在 macOS 上不可靠，Linux 上可靠 |
| `exec_in_process(code) -> (stdout, error)` | `sandbox=False` 时用的无隔离执行路径：进程内 `exec()`，无资源限制、无超时 |

## `runtrail.runtime.RegressionSuite`

跟踪一个命名的历史基线 `Report`，检测 Agent 改动后有没有让原本通过的 case 变失败——软件回归测试套件的 Agent 版。按 case 的 `input` 值匹配基线和当前运行，所以同一个 suite 里不要用重复的 `input`。

| 方法 | 说明 |
|------|------|
| `has_baseline() -> bool` | 这个 suite 是否已经存过基线 |
| `save_baseline(report)` | 把 `report` 存成新基线（覆盖旧的） |
| `load_baseline() -> Report` | 读回基线；没有的话 `FileNotFoundError` |
| `check(report) -> RegressionResult` | 拿 `report` 和基线比对 |

`RegressionResult`：`.newly_failing`/`.newly_passing`（`list[dict]`，各带 `input`）、`.pass_rate_delta`（仅供参考，不影响判定）、`.regressed`（`bool`，只要有 `newly_failing` 就是 `True`——新增的失败 case 不算回归，因为它们本来就不在基线里）、`.summary() -> str`。

CLI：`runtrail regress <suite_name> <report.json> [--save-baseline] [--baseline-dir]`，检测到回归时进程 exit code 非零，可以直接接 CI 门禁。

## `runtrail.adversarial`

| 类 | 说明 |
|------|------|
| `AdversarialDataset(base, *, include_boundary_cases=True)` | 包一个 `BaseDataset`，对每条 case 生成 prompt injection（2 种模板）+ 矛盾诱导（1 种）变体，外加固定的边界输入（空串/超长串/乱码）；每条生成的 case 带 `adversarial_type` 字段（`prompt_injection`/`contradiction`/`boundary`），确定性、不用 LLM |
| `PromptInjectionEvaluator(wrapped)` | 包一个 `BaseEvaluator`；额外检查 Agent 输出里有没有 `AdversarialDataset` 注入的诱饵字符串（`HACKED`/`PWNED`），命中就强制判失败，不管 `wrapped` 本来怎么判 |
| `LLMAdversarialGenerator(model, *, gateway=None)` | 用 LLM（默认 `LiteLLMAdapter`）把已有 case 的 `input` 改写成语义级的对抗版本——固定模板做不到的攻击；`.generate(case)` / `.generate_dataset(base) -> InMemoryDataset`。需要 `runtrail[gateway]` |

## `runtrail.observability.OTelMetrics`

`OTelMetrics(endpoint=None, *, meter_provider=None).record_run(report)` 推送 `runtrail.run.{pass_rate,total_cases,passed_cases,avg_duration_ms,avg_steps,total_tokens,failure_category}` 到 OTLP Collector（或注入的 `MeterProvider`，用于测试）。

## CLI

| 命令 | 说明 |
|------|------|
| `runtrail ui [--host] [--port] [--db-path]` | 启动 Web UI |
| `runtrail report <path>` | 打印一份 `Report.to_json()` 产物的 CLI 摘要 |
| `runtrail regress <suite_name> <report_path> [--save-baseline] [--baseline-dir]` | 对比 `RegressionSuite` 基线，回归时 exit code 非零（CI 门禁用） |

完整接口定义见各模块的 `base.py`；本页会随实现推进持续补充。
