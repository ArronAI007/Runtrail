# 大规模 Benchmark 部署

## 存储

开发环境使用零配置的 `SQLiteStore`；生产环境切换至 `PostgresStore`：

```python
from runtrail.storage.postgres_store import PostgresStore

store = PostgresStore(dsn="postgresql://user:pass@host:5432/runtrail")
harness = Harness(store=store)
```

## 并发与限流

通过 `runtime.queue` 控制并发 Agent 数与速率，避免打爆被测服务或模型网关。

## 沙箱隔离

跑不可信 Agent 代码时（无论是 `SubprocessAgent` 跑整个 Agent，还是 `CodeExecEvaluator`/`CodeExecTool` 跑 Agent 输出的代码片段），三者共享同一套资源限制机制：

```python
from runtrail.evaluator import CodeExecEvaluator

# 生产测试：开沙箱 + 资源限制
evaluator = CodeExecEvaluator(sandbox=True, cpu_limit=5, memory_limit_mb=256)

# 开发环境：关沙箱，直接进程内执行，换取速度（绝不能喂未知 Agent 输出）
fast_evaluator = CodeExecEvaluator(sandbox=False)
```

`memory_limit_mb` 依赖 POSIX `RLIMIT_AS`，在 macOS 上不可靠（Darwin 内核的已知限制，`setrlimit` 本身可能直接报错），已经用 Linux 容器验证生效——生产部署跑在 Linux 上就是这套限制真正生效的地方。见[安全提示](../README.md#🛡️-安全提示)。

## 可观测性

```python
from runtrail.observability.otel_metrics import OTelMetrics

OTelMetrics(endpoint="http://otel-collector:4318").record_run(report)
```

推送 `pass_rate`、`total_cases`、`passed_cases`、按 `failure_category` 分类的计数到现有 OpenTelemetry Collector，需要 `pip install 'runtrail[otel]'`。

## Docker

```bash
docker compose -f docker/docker-compose.yml up -d
```

> 镜像与 compose 配置已写好但未在真实集群跑通，参见 [Roadmap](roadmap.md) 的"已知差距"部分。
