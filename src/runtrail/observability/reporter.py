import csv
import html
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from runtrail.observability.trace import Trace


@dataclass
class Report:
    """Aggregated results of one Harness.run() call."""

    traces: list[Trace]

    @property
    def total(self) -> int:
        return len(self.traces)

    @property
    def passed(self) -> int:
        return sum(1 for t in self.traces if t.evaluation.get("passed"))

    def summary(self) -> str:
        total = self.total
        passed = self.passed
        rate = (passed / total * 100) if total else 0.0
        return f"{passed}/{total} passed ({rate:.1f}%)"

    def stats(self) -> dict:
        """Aggregate metrics used by OTelMetrics, the CLI report, and the Web UI."""
        total = self.total
        durations = [t.duration_ms for t in self.traces]
        step_counts = [len(t.steps) for t in self.traces]
        total_tokens = sum(
            step.get("tokens", {}).get("total_tokens", 0)
            for t in self.traces
            for step in t.steps
            if isinstance(step.get("tokens"), dict)
        )
        failure_category_counts: dict[str, int] = {}
        for t in self.traces:
            category = t.evaluation.get("failure_category")
            if category is not None:
                # FailureCategory is a (str, Enum) — use it directly as the key rather
                # than str(category), which would give "FailureCategory.UNKNOWN" instead
                # of "unknown" (Enum.__str__ shadows the underlying str value).
                failure_category_counts[category] = failure_category_counts.get(category, 0) + 1

        return {
            "total": total,
            "passed": self.passed,
            "pass_rate": self.passed / total if total else 0.0,
            "avg_duration_ms": sum(durations) / total if total else 0.0,
            "avg_steps": sum(step_counts) / total if total else 0.0,
            "total_tokens": total_tokens,
            "failure_category_counts": failure_category_counts,
        }

    def uncertain_cases(self) -> list[dict]:
        """Failed cases in the shape HITLService.enqueue_for_review() expects."""
        return [
            {"case": t.case, "output": t.output, "evaluation": t.evaluation}
            for t in self.traces
            if not t.evaluation.get("passed", True)
        ]

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "passed": self.passed,
            "cases": [
                {
                    "trace_id": t.trace_id,
                    "input": t.case.get("input"),
                    "ground_truth": t.case.get("ground_truth"),
                    "output": t.output,
                    "evaluation": t.evaluation,
                    "steps": t.steps,
                    "duration_ms": t.duration_ms,
                    "timestamp": t.timestamp.isoformat(),
                }
                for t in self.traces
            ],
        }

    @classmethod
    def from_json(cls, path: str | Path) -> "Report":
        """Reconstruct a Report from a Report.to_json() file — e.g. to compare
        two runs, or to feed the CLI/RegressionSuite. `case` only carries
        `input`/`ground_truth` back (the rest of the original case dict, if
        any, isn't part of the JSON shape).
        """
        data = json.loads(Path(path).read_text())
        traces = [
            Trace(
                case={"input": c["input"], "ground_truth": c.get("ground_truth")},
                output=c["output"],
                evaluation=c["evaluation"],
                trace_id=c.get("trace_id", ""),
                steps=c.get("steps", []),
                duration_ms=c.get("duration_ms", 0.0),
                timestamp=(
                    datetime.fromisoformat(c["timestamp"])
                    if c.get("timestamp")
                    else datetime.now(timezone.utc)
                ),
            )
            for c in data["cases"]
        ]
        return cls(traces=traces)

    def to_json(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False))

    def to_csv(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["trace_id", "input", "output", "passed", "score", "failure_category", "duration_ms"]
            )
            for t in self.traces:
                writer.writerow(
                    [
                        t.trace_id,
                        t.case.get("input"),
                        t.output.get("output"),
                        t.evaluation.get("passed"),
                        t.evaluation.get("score"),
                        t.evaluation.get("failure_category", ""),
                        t.duration_ms,
                    ]
                )

    def export_failures_jsonl(self, path: str | Path) -> int:
        """Write failed cases as JSONL — one {input, ground_truth, output,
        evaluation} object per line, ready to feed a fine-tuning or
        prompt-optimization pipeline. Returns the number of cases written.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        failures = [t for t in self.traces if not t.evaluation.get("passed", True)]
        with path.open("w") as f:
            for t in failures:
                f.write(
                    json.dumps(
                        {
                            "input": t.case.get("input"),
                            "ground_truth": t.case.get("ground_truth"),
                            "output": t.output,
                            "evaluation": t.evaluation,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        return len(failures)

    def to_markdown(self, path: str | Path) -> None:
        """Export a human-readable Markdown report — for write-ups, PR
        descriptions, or internal status reports.
        """
        stats = self.stats()
        lines = [
            "# Runtrail Evaluation Report",
            "",
            f"**{self.summary()}**",
            "",
            "## Stats",
            "",
            "| Metric | Value |",
            "|---|---|",
            f"| Total cases | {stats['total']} |",
            f"| Passed | {stats['passed']} |",
            f"| Pass rate | {stats['pass_rate'] * 100:.1f}% |",
            f"| Avg duration | {stats['avg_duration_ms']:.1f}ms |",
            f"| Avg steps | {stats['avg_steps']:.1f} |",
            f"| Total tokens | {stats['total_tokens']} |",
            "",
        ]

        if stats["failure_category_counts"]:
            lines += ["## Failure Categories", "", "| Category | Count |", "|---|---|"]
            for category, count in sorted(
                stats["failure_category_counts"].items(), key=lambda kv: -kv[1]
            ):
                lines.append(f"| {category} | {count} |")
            lines.append("")

        failed = [t for t in self.traces if not t.evaluation.get("passed", True)]
        if failed:
            lines += ["## Failed Cases", ""]
            for t in failed:
                lines += [
                    f"### `{t.trace_id}`",
                    "",
                    f"- **Input:** {t.case.get('input')!r}",
                    f"- **Ground truth:** {t.case.get('ground_truth')!r}",
                    f"- **Output:** {t.output.get('output')!r}",
                    f"- **Failure category:** {t.evaluation.get('failure_category', 'n/a')}",
                    "",
                ]

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines))

    def to_html(self, path: str | Path) -> None:
        """Export a standalone, shareable HTML report (inline CSS, no external
        assets) — for a browser-viewable summary rather than a raw JSON dump.
        """
        stats = self.stats()

        def esc(value: object) -> str:
            return html.escape(str(value))

        failure_rows = "".join(
            f"<tr><td>{esc(category)}</td><td>{count}</td></tr>"
            for category, count in sorted(
                stats["failure_category_counts"].items(), key=lambda kv: -kv[1]
            )
        )
        failed_traces = [t for t in self.traces if not t.evaluation.get("passed", True)]
        failed_rows = "".join(
            f"<tr><td>{esc(t.trace_id)}</td><td>{esc(t.case.get('input'))}</td>"
            f"<td>{esc(t.output.get('output'))}</td>"
            f"<td>{esc(t.evaluation.get('failure_category', ''))}</td></tr>"
            for t in failed_traces
        )

        failure_section = (
            f"<h2>Failure Categories</h2>"
            f"<table><tr><th>Category</th><th>Count</th></tr>{failure_rows}</table>"
            if failure_rows
            else ""
        )
        failed_section = (
            f"<h2>Failed Cases</h2>"
            f"<table><tr><th>Trace ID</th><th>Input</th><th>Output</th>"
            f"<th>Failure Category</th></tr>{failed_rows}</table>"
            if failed_rows
            else ""
        )

        content = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Runtrail Evaluation Report</title>
<style>
body {{ font-family: -apple-system, Helvetica, Arial, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; }}
table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
th, td {{ border: 1px solid #ccc; padding: 6px 10px; text-align: left; }}
th {{ background: #f5f5f5; }}
</style></head>
<body>
<h1>Runtrail Evaluation Report</h1>
<p><strong>{esc(self.summary())}</strong></p>
<h2>Stats</h2>
<table>
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>Total cases</td><td>{stats["total"]}</td></tr>
<tr><td>Passed</td><td>{stats["passed"]}</td></tr>
<tr><td>Pass rate</td><td>{stats["pass_rate"] * 100:.1f}%</td></tr>
<tr><td>Avg duration</td><td>{stats["avg_duration_ms"]:.1f}ms</td></tr>
<tr><td>Avg steps</td><td>{stats["avg_steps"]:.1f}</td></tr>
<tr><td>Total tokens</td><td>{stats["total_tokens"]}</td></tr>
</table>
{failure_section}
{failed_section}
</body></html>"""

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
