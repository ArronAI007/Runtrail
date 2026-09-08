import json
from dataclasses import dataclass
from pathlib import Path

from runtrail.observability.reporter import Report


@dataclass
class ComparisonReport:
    """Side-by-side results of running several candidates (different models,
    different Agent implementations, ...) against the same dataset/evaluator.
    """

    reports: dict[str, Report]

    def best(self, *, key: str = "pass_rate") -> str:
        return max(self.reports, key=lambda name: self.reports[name].stats()[key])

    def summary_table(self) -> str:
        rows = [
            (name, r.stats()["pass_rate"], r.stats()["avg_duration_ms"], r.stats()["total_tokens"])
            for name, r in self.reports.items()
        ]
        header = f"{'candidate':<20}{'pass_rate':>12}{'avg_duration_ms':>18}{'total_tokens':>14}"
        lines = [header, "-" * len(header)]
        for name, pass_rate, avg_duration_ms, total_tokens in rows:
            lines.append(f"{name:<20}{pass_rate * 100:>11.1f}%{avg_duration_ms:>18.1f}{total_tokens:>14}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {name: report.stats() for name, report in self.reports.items()}

    def to_json(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False))
