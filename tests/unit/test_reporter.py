import csv
import json

from runtrail.evaluator.failure_classifier import FailureCategory
from runtrail.observability.reporter import Report
from runtrail.observability.trace import Trace


def _make_report() -> Report:
    return Report(
        traces=[
            Trace(
                case={"input": "a", "ground_truth": "a"},
                output={"output": "a"},
                evaluation={"passed": True, "score": 1.0},
                steps=[{"type": "thought"}, {"type": "tool_call", "tokens": {"total_tokens": 10}}],
                duration_ms=20.0,
            ),
            Trace(
                case={"input": "b", "ground_truth": "right"},
                output={"output": "wrong"},
                evaluation={"passed": False, "score": 0.0, "failure_category": "planning_error"},
                steps=[],
                duration_ms=40.0,
            ),
        ]
    )


def test_stats_aggregates_pass_rate_duration_steps_and_tokens():
    stats = _make_report().stats()

    assert stats["total"] == 2
    assert stats["passed"] == 1
    assert stats["pass_rate"] == 0.5
    assert stats["avg_duration_ms"] == 30.0
    assert stats["avg_steps"] == 1.0
    assert stats["total_tokens"] == 10
    assert stats["failure_category_counts"] == {"planning_error": 1}


def test_stats_uses_the_plain_string_value_for_a_real_failure_category_enum():
    # Regression test: FailureCategory is a (str, Enum). str(FailureCategory.UNKNOWN)
    # gives "FailureCategory.UNKNOWN" (Enum.__str__), not the plain value "unknown" —
    # stats() must key on the value, not str(), or downstream JSON/OTel labels break.
    report = Report(
        traces=[
            Trace(
                case={"input": "a"},
                output={},
                evaluation={"passed": False, "score": 0.0, "failure_category": FailureCategory.UNKNOWN},
            )
        ]
    )

    stats = report.stats()

    assert stats["failure_category_counts"] == {"unknown": 1}
    assert "FailureCategory.UNKNOWN" not in stats["failure_category_counts"]
    assert json.dumps(stats["failure_category_counts"]) == '{"unknown": 1}'


def test_stats_handles_an_empty_report():
    stats = Report(traces=[]).stats()

    assert stats["total"] == 0
    assert stats["pass_rate"] == 0.0
    assert stats["avg_duration_ms"] == 0.0


def test_to_dict_includes_trace_id_steps_and_duration():
    report = _make_report()

    cases = report.to_dict()["cases"]

    assert cases[0]["trace_id"] == report.traces[0].trace_id
    assert cases[0]["steps"] == report.traces[0].steps
    assert cases[0]["duration_ms"] == 20.0


def test_to_csv_writes_one_row_per_case(tmp_path):
    path = tmp_path / "report.csv"
    _make_report().to_csv(path)

    with path.open() as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 2
    assert rows[0]["input"] == "a"
    assert rows[0]["passed"] == "True"
    assert rows[1]["failure_category"] == "planning_error"


def test_export_failures_jsonl_writes_only_failed_cases(tmp_path):
    path = tmp_path / "failures.jsonl"
    count = _make_report().export_failures_jsonl(path)

    assert count == 1
    lines = path.read_text().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["input"] == "b"
    assert record["ground_truth"] == "right"
    assert record["output"] == {"output": "wrong"}


def test_export_failures_jsonl_writes_nothing_when_all_cases_pass(tmp_path):
    report = Report(
        traces=[
            Trace(case={"input": "a"}, output={"output": "a"}, evaluation={"passed": True, "score": 1.0})
        ]
    )
    path = tmp_path / "failures.jsonl"

    count = report.export_failures_jsonl(path)

    assert count == 0
    assert path.read_text() == ""
