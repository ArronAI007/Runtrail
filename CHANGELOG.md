# Changelog

All notable changes to this project are documented here. Format loosely
follows [Keep a Changelog](https://keepachangelog.com/); this project has not
made a tagged release yet, so everything below is `[Unreleased]`.

## [Unreleased]

### Added

- Core abstractions: `BaseAgent`, `BaseEvaluator`, `BaseDataset`, `BaseTool`, `BaseStore`
- Agent adapters: `LocalAgent`, `SubprocessAgent` (POSIX resource limits), `RemoteAgent` (HTTP)
- `Harness.run()` (with `TaskQueue` concurrency/priority and `Checkpoint` resume) and `Harness.compare()` for multi-candidate comparison reports
- Evaluators: `SimpleEvaluator`, `NormalizedMatchEvaluator`, `JSONSchemaEvaluator`, `ToolCallEvaluator`, `CodeExecEvaluator` (sandboxed, togglable), `LLMJudge`
- `FailureClassifier`, auto-attached to `TaskRunner`
- Datasets: `InMemoryDataset`, `FileDataset` (JSONL), `BenchmarkAdapter` (generic GAIA/AgentBench-style loader), `PerturbedDataset`
- Tools: `LocalFunctionTool`, `MCPAdapter`, `OpenAPIAdapter`, `CodeExecTool`, `ToolMock` (fault/latency/garble injection, optional real-tool wrapping)
- `DAGEngine` for multi-Agent task graphs, including declarative YAML definitions
- `runtrail.security.sandbox`: shared POSIX resource-limit helper used by `SubprocessAgent`/`CodeExecEvaluator`/`CodeExecTool`
- Storage: `SQLiteStore` (thread-safe, zero-config) and `PostgresStore`, both with Trace/HITL persistence, run listing, and aggregate stats
- `Trace` step-level recording (`output['steps']` convention), `trace_id`, per-case duration
- `Report`: `stats()`, `to_json`/`from_json`/`to_csv`/`to_markdown`/`to_html`/`export_failures_jsonl`, `uncertain_cases()`
- `HITLService` + `Annotation` for human-in-the-loop review queues
- Web UI (`runtrail ui`, FastAPI): dashboard, per-run Trace browser, per-trace detail, HITL review/annotate
- `OTelMetrics` (OTLP export or injected `MeterProvider`)
- `LiteLLMAdapter` (`complete`/`complete_with_usage`) — routes through litellm, so any provider or OpenAI-compatible gateway (One-API, etc.) works via `api_base`/`api_key`
- `RegressionSuite`/`RegressionResult` — baseline-tracked regression testing for Agents, keyed to `runtrail regress` for CI gating
- `runtrail.adversarial`: `AdversarialDataset` (prompt-injection/contradiction/boundary templates), `PromptInjectionEvaluator`, `LLMAdversarialGenerator`
- CLI: `runtrail ui`, `runtrail report`, `runtrail regress`
- Docker/Compose deployment (Postgres-backed, healthcheck-gated startup) — built and run for real, including a verified write path to Postgres from inside the container
- CI: lint (`ruff`, now including `examples/`), type-check (`mypy`), tests across Python 3.10–3.12, with a live Postgres service

### Known gaps

See [docs/roadmap.md](docs/roadmap.md)'s "已知差距" section for the current honest list (e.g. `FailureClassifier` can't yet reach `hallucination`/`planning_error`, no step-redundancy detection, Web UI has no auth, `RegressionSuite` matches cases by `input` string so duplicates within a suite collide, `AdversarialDataset`'s templates are fixed and not exhaustive).
