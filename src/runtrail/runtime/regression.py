from dataclasses import dataclass, field
from pathlib import Path

from runtrail.observability.reporter import Report


@dataclass
class RegressionResult:
    """The outcome of comparing a fresh Report against a saved baseline."""

    baseline_stats: dict
    current_stats: dict
    newly_failing: list[dict] = field(default_factory=list)
    newly_passing: list[dict] = field(default_factory=list)

    @property
    def pass_rate_delta(self) -> float:
        """Informational only — the two reports can cover different case sets
        (e.g. a run with brand-new cases added), so this isn't what decides
        `regressed`. A regression means a case that used to pass now doesn't.
        """
        return self.current_stats["pass_rate"] - self.baseline_stats["pass_rate"]

    @property
    def regressed(self) -> bool:
        return bool(self.newly_failing)

    def summary(self) -> str:
        arrow = "v" if self.pass_rate_delta < 0 else ("^" if self.pass_rate_delta > 0 else "=")
        pass_rate_line = (
            f"pass rate: {self.baseline_stats['pass_rate'] * 100:.1f}% -> "
            f"{self.current_stats['pass_rate'] * 100:.1f}% "
            f"({arrow} {self.pass_rate_delta * 100:+.1f}pp)"
        )
        lines = [pass_rate_line]
        if self.newly_failing:
            lines.append(f"REGRESSED: {len(self.newly_failing)} case(s) newly failing:")
            for case in self.newly_failing:
                lines.append(f"  - {case['input']!r}")
        else:
            lines.append("no newly-failing cases")
        if self.newly_passing:
            lines.append(f"newly passing: {len(self.newly_passing)} case(s)")
        return "\n".join(lines)


class RegressionSuite:
    """Tracks a named historical baseline Report and flags regressions when
    you re-run the same case set after changing an Agent's prompt/code — the
    Agent analogue of a software regression test suite.

    Cases are matched between baseline and current run by their `input`
    value, so the suite (the dataset) should stay stable across runs for the
    comparison to be meaningful.
    """

    def __init__(self, name: str, baseline_dir: str | Path = ".runtrail_baselines"):
        self.name = name
        self.path = Path(baseline_dir) / f"{name}.json"

    def has_baseline(self) -> bool:
        return self.path.exists()

    def save_baseline(self, report: Report) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        report.to_json(self.path)

    def load_baseline(self) -> Report:
        if not self.has_baseline():
            raise FileNotFoundError(
                f"No baseline saved yet for suite '{self.name}' at {self.path} "
                "— call save_baseline() first"
            )
        return Report.from_json(self.path)

    def check(self, report: Report) -> RegressionResult:
        baseline = self.load_baseline()
        baseline_by_input = {t.case.get("input"): t for t in baseline.traces}

        newly_failing = []
        newly_passing = []
        for trace in report.traces:
            input_key = trace.case.get("input")
            baseline_trace = baseline_by_input.get(input_key)
            if baseline_trace is None:
                continue  # not part of the baseline — nothing to regress against

            was_passing = bool(baseline_trace.evaluation.get("passed"))
            is_passing = bool(trace.evaluation.get("passed"))
            if was_passing and not is_passing:
                newly_failing.append(
                    {
                        "input": input_key,
                        "baseline_output": baseline_trace.output,
                        "current_output": trace.output,
                    }
                )
            elif not was_passing and is_passing:
                newly_passing.append({"input": input_key})

        return RegressionResult(
            baseline_stats=baseline.stats(),
            current_stats=report.stats(),
            newly_failing=newly_failing,
            newly_passing=newly_passing,
        )
