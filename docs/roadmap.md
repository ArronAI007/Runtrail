# Roadmap

## v0.1.0 - MVP（核心骨架）— 完成

- 核心抽象基类：BaseAgent、BaseEvaluator、BaseDataset、BaseTool、BaseStore
- 基础任务调度、单任务执行；单个 Agent 异常不中断整批评测（`TaskRunner` 层面容错）
- ✅ SQLite 存储、基础Trace记录（`SQLiteStore`，线程安全，可被 `TaskQueue`/Web UI 并发访问）
- ✅ 规则评估：精确匹配（`SimpleEvaluator`）、归一化匹配（`NormalizedMatchEvaluator`）、JSON Schema 校验（`JSONSchemaEvaluator`，需要 `pip install 'runtrail[schema]'`）、工具调用准确率（`ToolCallEvaluator`）
- ✅ 代码执行评估（`CodeExecEvaluator`，subprocess 沙箱执行 Agent 输出代码并比对 stdout）
- ✅ LLM‑as‑Judge（`LLMJudge`）+ 模型网关适配（`LiteLLMAdapter`，需要 `pip install 'runtrail[gateway]'`；不重复造网关，直接透传 litellm 的 kwargs——`api_base`/`api_key` 可指向 One-API 等 OpenAI 兼容代理，也可以直连各大厂商 API）
- ✅ 模型/Agent 对比实验：`Harness.compare({name: agent, ...}, dataset, evaluator) -> ComparisonReport`，一键跑多个候选并生成对比表 + JSON 报告（`summary_table()`/`to_json()`/`best()`）
- ✅ 故障自动归因分类，已接入 `TaskRunner`：Agent 崩溃或评估失败时自动打 `failure_category` 标签（启发式规则版，覆盖 tool_call_error/tool_response_error/context_overflow/infinite_loop/prompt_defect/unknown；hallucination/planning_error 需要语义判断，尚未接回 `LLMJudge`，见下方"已知差距"）
- ✅ 子进程隔离Agent运行，支持 CPU/内存/超时资源限制（`SubprocessAgent`，POSIX）
- ✅ 远程 HTTP Agent 适配（`RemoteAgent`，需要 `pip install 'runtrail[remote]'`）
- ✅ DAG任务编排：依赖调度、Agent 间消息路由、声明式 YAML 任务定义（`DAGEngine`，YAML 需要 `pip install 'runtrail[yaml]'`）
- ✅ 自定义数据集：`InMemoryDataset` + 本地 JSONL 文件（`FileDataset`）
- 最小可运行示例；单元测试；CI

## v0.2.0 - 能力补齐 — 完成

- ✅ 任务队列并发限流 + 重试退避策略 + 任务优先级（`TaskQueue`：自建的优先级堆调度而非 `ThreadPoolExecutor` 的纯 FIFO 队列，`priority` 数值越大越先跑；接入 `Harness.run(queue=...)`，数据集里每条 case 可带 `"priority"` 字段直接驱动调度顺序）
- ✅ 断点续跑 Checkpoint（`Checkpoint`，接入 `Harness.run(checkpoint=...)`，按 case 级恢复，不重跑已完成用例）
- ✅ Tool Mock（`ToolMock`）：固定假返回/异常注入、`timeout_after_sec` 模拟超时、`garble=True` 模拟工具返回乱码；可选 `wrapped=` 包一个真实 `BaseTool` 按 `failure_rate` 概率混合真实/故障调用，做真实集成的混沌测试；另有任务级扰动测试（`PerturbedDataset` + `add_typo_noise`/`shuffle_whitespace`/`add_distractor_text`，区别于工具级扰动）
- ✅ 工具层统一适配：本地函数（`LocalFunctionTool`）、OpenAPI 3.x 操作（`OpenAPIAdapter`，需要 `runtrail[remote]`，仅支持 path/query 参数 + JSON body，不解析跨文件 `$ref`）、MCP 工具（`MCPAdapter`，需要 `runtrail[mcp]`，走 stdio，每次调用起一个子进程会话，无持久连接）、沙箱代码执行（`CodeExecTool`）
- ✅ 沙箱安全机制统一：`CodeExecEvaluator`/`CodeExecTool` 现在也有 `cpu_limit`/`memory_limit_mb`（复用 `SubprocessAgent` 同一套 `resource_limit_preexec_fn`），并新增 `sandbox: bool` 开关——`True`（默认）走 subprocess 隔离，`False` 走进程内 `exec()`（无隔离/无限制/无超时，仅供开发环境跑可信代码时提速，绝不能用于未知 Agent 输出）。memory_limit_mb 在 macOS 上因 Darwin 的 `RLIMIT_AS` 内核限制不可靠（已用 Docker 里的真实 Linux 容器验证生效），CPU 限制（`RLIMIT_CPU`）两个平台都可靠
- ✅ 细粒度评估维度：工具调用准确率（`ToolCallEvaluator`）、平均步数与 token 消耗（`Report.stats()`/`OTelMetrics`，见 v0.3.0）
- ✅ 基础报告导出 JSON（`Report.to_json`）+ CSV（`Report.to_csv`）+ 失败用例 JSONL（`Report.export_failures_jsonl`，可直接喂微调/提示词优化流水线）
- 步骤冗余度（同一工具被重复/无意义调用的检测）：尚未实现——`avg_steps` 只是计数，不判断"是否冗余"
- 数据库导入自定义数据集：尚未实现（`FileDataset` 目前只支持本地 JSONL）

## v0.3.0 - HITL & UI Alpha — 完成

- ✅ HITL 后端标注服务（`HITLService`，队列/标注落 `BaseStore`：`SQLiteStore`/`PostgresStore` 均实现）
- ✅ 可选轻量Web UI（FastAPI，`runtrail ui`）：`/` 总览仪表盘（pass rate 进度条、故障分类统计、任务列表）、`/runs/{run_id}` Trace 列表（支持 `?failed_only=true` 筛选失败案例）、`/traces/{trace_id}` 单条 Trace 详情（含 steps）、`/api/reviews`、`/api/reviews/{id}/annotate`、`/api/runs`、`/api/runs/{run_id}`、`/api/traces/{trace_id}`、`/api/stats`
- ✅ 公开数据集适配（`BenchmarkAdapter`）：通用 JSON/JSONL 字段映射加载器，兼容 GAIA `metadata.jsonl`、AgentBench 任务导出等格式；**不包含** GAIA 在 HuggingFace 上的门禁下载（需要用户自己的 token/协议）
- ✅ Trace 记录到单步：`output['steps']` 约定（thought/tool_call/llm_call，`LiteLLMAdapter.complete_with_usage()` 提供真实 token 用量），`Trace` 有唯一 `trace_id`，`BaseStore.load_trace(trace_id)` 可单独查询；不使用该约定的 Agent 仍能拿到完整 Trace（`steps=[]`）
- ✅ CLI 报告输出：`runtrail report <path>`，读取 `Report.to_json()` 产物，打印摘要 + 故障分类统计

## v0.4.0 - 生产就绪 — 完成

- ✅ PostgreSQL 存储支持（`PostgresStore`，与 `SQLiteStore` 同接口，含 HITL 队列表、Trace 单查、run 聚合统计；已用真实本地 Postgres 实例验证）
- ✅ OpenTelemetry metrics（`OTelMetrics`，OTLP 导出 + 可注入 MeterProvider 测试；`pass_rate`/`total_cases`/`passed_cases`/`avg_duration_ms`/`avg_steps`/`total_tokens`/按 `failure_category` 分类的计数）
- ✅ Agent回归测试套件正式化：`RegressionSuite`（`runtrail.runtime.regression`）——按 case 的 `input` 匹配基线与当前运行，`newly_failing`/`newly_passing`/`pass_rate_delta`；`runtrail regress <suite> <report.json> [--save-baseline]` CLI 命令可直接接入 CI 门禁（回归时 exit code 非零）；`examples/regression_suite.py` 是真实用法，不再是手写占位
- ✅ 标准化 Markdown/HTML 评测报告导出：`Report.to_markdown`/`to_html` 已实现（HTML 内联转义，Markdown 直出），供论文/内部汇报使用；`Report.from_json` 补上了反向反序列化（供 `runtrail report`/`RegressionSuite`/跨运行对比复用）
- ✅ 对抗评测模式：`runtrail.adversarial`——`AdversarialDataset`（确定性模板：prompt injection、矛盾诱导、边界输入，LLM-free）+ `PromptInjectionEvaluator`（检测 Agent 是否被注入攻击劫持）+ `LLMAdversarialGenerator`（用 LiteLLMAdapter 生成语义级对抗改写，模板做不到的那种）
- ✅ Docker / docker‑compose 部署：已用真实 Docker 构建镜像、`docker compose up` 起完整栈（Postgres + Web UI），验证过健康检查门控启动顺序、`RUNTRAIL_STORE_DSN` 真的被读取、容器内 `0.0.0.0` 绑定可从宿主机访问、写入真正落到 Postgres——过程中修了四个之前从未跑过所以从未发现的真实 bug（见下方"已知差距"外的修复记录，都已合入）
- ✅ CI 流水线：`ruff`（含 `examples/`）+ `mypy` + `pytest --cov`（含真实 Postgres service container），全部在本地跑过和 CI 里将跑的完全一致的命令组合验证过
- 完整文档

## v1.0.0

- API稳定；完整集成测试；生产案例；社区示例丰富

## 已知差距（诚实记账，不是"未来探索"）

这些是本该属于上面某个版本、但这一轮没有做到的具体缺口：

- `FailureClassifier` 打不出 `hallucination`/`planning_error`——需要接 `LLMJudge` 做语义判断，目前只有规则匹配
- `FileDataset`/`BenchmarkAdapter` 不支持数据库导入，只支持本地文件和 HTTP JSON/JSONL
- 没有"步骤冗余度"检测——`avg_steps` 只是平均步数，不判断哪些步骤是重复/无意义的
- Web UI 没有鉴权——`runtrail ui` 默认监听 `127.0.0.1`，暴露到公网前自己加反向代理鉴权
- `RegressionSuite` 按 case 的 `input` 字符串匹配基线，如果同一个 suite 里两条 case 的 `input` 完全相同会互相覆盖——用有区分度的输入，或者以后可能需要加显式 case id
- `AdversarialDataset` 的攻击模板是固定的几个（prompt injection 关键词、矛盾话术、边界字符串），不是穷举，绕过这几个模板的攻击测不出来；语义级/生成式攻击要用 `LLMAdversarialGenerator`（需要真实模型调用）

## 未来探索（可选加分项）

不是承诺的版本里程碑，是有价值但暂不计划排期的方向：

- 同一任务集合批量对比不同 Agent 实现在对抗数据集上的鲁棒性排名（`Harness.compare()` + `AdversarialDataset` 已经能拼出来，只是还没包装成一个专门的便捷方法）
