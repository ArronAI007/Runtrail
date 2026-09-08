# 架构概览

## 整体架构图

```mermaid
flowchart TB
    User[用户] -->|CLI / Python SDK / HTTP API| HarnessCore[Runtrail Core]

    subgraph HarnessCore
        TaskRunner[TaskRunner 任务调度]
        DAGEngine[DAG Engine 多‑Agent编排]
        Checkpoint[Checkpoint 断点续跑]
        Queue[Task Queue 并发限流]
    end

    %% 被测Agent层：三类接入模式
    subgraph AgentLayer["Agent接入层（可插拔，不内置Agent）"]
        LocalAgent[本地进程 Agent]
        SubprocAgent[子进程沙箱 Agent]
        RemoteAgent[远程 HTTP/RPC Agent<br/>LangGraph/AutoGen/自研服务]
    end

    %% 工具层，含Mock
    subgraph ToolLayer[工具适配器层]
        RealTool[真实工具 MCP/OpenAPI]
        MockTool[Tool Mock 扰动测试]
    end

    %% 评测引擎
    subgraph EvalLayer[混合评估引擎]
        RuleEval[规则评估]
        LLMJudge[LLM‑as‑Judge]
        CodeEval[代码执行评估]
        GTEval[真值比对]
        FailureCls[故障自动归因]
    end

    %% 数据集
    subgraph DatasetLayer[数据集层]
        InMemoryDS[内存数据集]
        FileDS[文件数据集]
        BenchmarkDS[GAIA/AgentBench适配]
    end

    %% 存储层
    subgraph StorageLayer[可插拔存储]
        SQLiteStore[SQLite 开发模式]
        PGStore[PostgreSQL 生产模式]
    end

    %% 可观测 & HITL & UI
    subgraph Observability[可观测 & HITL]
        Trace[Trace全链路记录]
        Reporter[报告输出 JSON/CSV/HTML]
        OTel[OpenTelemetry Metrics]
        HITL[HITL 人工标注服务]
        WebUI[可选轻量Web UI]
    end

    %% 模型网关适配
    subgraph ModelGateway[模型网关适配]
        LiteLLM[LiteLLM / One‑API Adapter]
    end

    %% 连线关系
    HarnessCore --> AgentLayer
    AgentLayer --> ToolLayer
    HarnessCore --> EvalLayer
    HarnessCore --> DatasetLayer
    HarnessCore --> StorageLayer
    HarnessCore --> Observability
    HarnessCore --> ModelGateway

    HITL <--> WebUI
```

## 关键设计约束

1. **不实现业务 Agent**：只定义 Agent 调用接口，被测对象来自外部。
2. **UI 是可选组件**：核心逻辑不依赖前端，可以纯 CLI / SDK 使用。
3. **模型网关不重复造轮子**：做 LiteLLM/One‑API 的适配器，不自己实现模型负载均衡。
4. **存储可插拔**：开发 SQLite 零配置，生产切换 PostgreSQL。
5. **沙箱安全默认关闭**，文档明确风险。
6. **所有扩展点都是抽象基类接口**，用户继承即可自定义，不需要修改框架源码。
