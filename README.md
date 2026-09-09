# Runtrail

生产级 Agent Harness：面向开发者 & 研究者的 Agent 调度、自动化评测、人在回路(HITL)、链路追踪、Benchmark 框架。

> ⚠️ **Runtrail 不是 Agent 开发框架**。
> 它是 Agent 的测试底座：可以拿来跑、评测、对比任意 Agent（自定义 / LangGraph / AutoGen / 远程 HTTP‑Agent）。

[![CI Status](https://github.com/ArronAI007/Runtrail/actions/workflows/ci.yml/badge.svg)](https://github.com/ArronAI007/Runtrail/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/ArronAI007/Runtrail)](LICENSE)

## ✨ 为什么做这个项目｜差异化亮点

市面上大量 Agent Harness 存在痛点：强耦合 Agent 实现、仅适合 Demo、缺少故障归因、无原生 HITL、缺少断点续跑、无工具 Mock、大规模 Benchmark 容易崩溃。

**Runtrail 核心差异：**
- 🧩 **完全解耦分层架构**：Agent、Evaluator、Tool、Dataset、Storage 全部可插拔接口，不绑定任何 Agent 库。支持本地进程 / 隔离子进程沙箱 / 远程 RPC Agent 三种运行模式。
- 📊 **混合评估引擎**：规则校验 + LLM‑as‑Judge + 代码执行评估 + 真值比对；自动故障归因分类（幻觉/工具调用错误/上下文溢出/规划错误等）。
- 👤 **原生 HITL 人在回路**：半自动评测流水线，内置轻量 Web UI 做人工复核打分，标注数据可回流 Judge。
- ⏯️ **任务断点续跑 & DAG 多‑Agent 评测**：支持复杂任务 DAG，中断后可恢复执行；支持多 Agent 协作 / 对抗评测。
- 🛠️ **工具 Mock & 扰动测试**：模拟工具超时、异常返回，做 Agent 鲁棒性测试，不依赖真实外部服务。
- 🔍 **完整 Agent Trace 链路追踪**：结构化存储每一步思考、工具IO、LLM 请求、评估结果；OpenTelemetry 指标输出。
- ⚡ **Agent 回归测试套件**：修改 Agent 提示词/代码后自动跑历史用例，检测性能退化。
- 📦 **开箱即用，分层部署**：开发环境 SQLite 零依赖；生产环境切换 PostgreSQL；UI 为可选组件，支持纯 CLI / API 无界面运行。
- 🔌 **兼容现有生态**：对接 LiteLLM / One‑API，无需重复造模型网关；兼容 GAIA / AgentBench 公开数据集。

## 🚀 快速开始

### 1. 安装

> ⚠️ PyPI 上 `runtrail` 这个包名已被另一个无关项目占用，`pip install runtrail` 装的不是本项目。目前请从源码安装：

```bash
git clone https://github.com/ArronAI007/Runtrail.git
cd Runtrail
pip install -e ".[ui]"
```

### 2. 最小示例：评测一个自定义 Agent

```python
from runtrail import Harness, SimpleEvaluator
from runtrail.dataset import InMemoryDataset

# 1. 定义待测试 Agent（可以是任意你自己实现的Agent）
def my_agent(task_input: str):
    return {"output": f"reply for: {task_input}"}

# 2. 加载测试数据集
ds = InMemoryDataset([
    {"input": "what is 2+2", "ground_truth": "4"}
])

# 3. 启动 Harness
harness = Harness()
report = harness.run(agent=my_agent, dataset=ds, evaluator=SimpleEvaluator())

# 4. 输出报告
print(report.summary())
report.to_json("./output/report.json")
```

### 3. 启动 Web UI（可选）

```bash
runtrail ui
```

## 📚 文档

- [快速入门](docs/quickstart.md)
- [核心概念](docs/core_concepts.md)
- [接口扩展：自定义 Agent / Evaluator / Dataset / Tool / Store](docs/extend.md)
- [教程：评测一个 LangGraph Agent](docs/eval_langgraph.md)
- [HITL 人在回路使用指南](docs/hitl.md)
- [大规模 Benchmark 部署](docs/production_deploy.md)
- [API Reference](docs/api.md)
- [Roadmap（含已知差距）](docs/roadmap.md)

## 📂 Examples

- `examples/eval_gaia.py`：跑 GAIA 风格公开数据集评测
- `examples/eval_langgraph_agent.py`：评测 LangGraph Agent（进程内 + HTTP 两种方式）
- `examples/multi_agent_collab.py`：多 Agent 协作评测（DAG）
- `examples/hitl_pipeline.py`：HITL 人工标注流水线
- `examples/compare_models.py`：批量对比不同模型/Agent 效果
- `examples/tool_robustness.py`：工具故障注入的鲁棒性测试
- `examples/adversarial_testing.py`：对抗评测——prompt injection / 矛盾诱导 / 边界输入攻击测试
- `examples/regression_suite.py`：Agent 回归测试套件（保存基线 + 检测退化，可接 CI）

## 🏗️ 架构概览

查看 [架构文档](docs/architecture.md)

## 🛡️ 安全提示

代码沙箱执行能力默认关闭；大规模运行建议开启沙箱隔离，防止恶意 Agent 代码。

## 🤝 贡献

欢迎 PR / Issue，请阅读 [Contributing Guide](CONTRIBUTING.md)

## 📄 License

Apache-2.0，详见 [LICENSE](LICENSE)
