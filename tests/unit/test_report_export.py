from runtrail.observability.reporter import Report
from runtrail.observability.trace import Trace


def _make_report() -> Report:
    return Report(
        traces=[
            Trace(
                case={"input": "2+2", "ground_truth": "4"},
                output={"output": "4"},
                evaluation={"passed": True, "score": 1.0},
                duration_ms=10.0,
            ),
            Trace(
                case={"input": "<script>bad</script>", "ground_truth": "safe"},
                output={"output": "wrong"},
                evaluation={"passed": False, "score": 0.0, "failure_category": "planning_error"},
                duration_ms=20.0,
            ),
        ]
    )


def test_from_json_round_trips_a_saved_report(tmp_path):
    path = tmp_path / "report.json"
    original = _make_report()
    original.to_json(path)

    loaded = Report.from_json(path)

    assert loaded.total == 2
    assert loaded.passed == 1
    assert loaded.traces[0].case["input"] == "2+2"
    assert loaded.traces[0].case["ground_truth"] == "4"
    assert loaded.traces[1].evaluation["failure_category"] == "planning_error"


def test_to_markdown_includes_summary_stats_and_failed_cases(tmp_path):
    path = tmp_path / "report.md"
    _make_report().to_markdown(path)

    content = path.read_text()

    assert "# Runtrail Evaluation Report" in content
    assert "1/2 passed" in content
    assert "planning_error" in content
    assert "<script>bad</script>" in content  # markdown, not HTML — no escaping needed


def test_to_html_escapes_case_content_and_includes_stats(tmp_path):
    path = tmp_path / "report.html"
    _make_report().to_html(path)

    content = path.read_text()

    assert "<title>Runtrail Evaluation Report</title>" in content
    assert "1/2 passed" in content
    assert "planning_error" in content
    assert "<script>bad</script>" not in content
    assert "&lt;script&gt;bad&lt;/script&gt;" in content


def test_to_html_handles_a_fully_passing_report_with_no_failure_tables(tmp_path):
    path = tmp_path / "report.html"
    report = Report(
        traces=[
            Trace(case={"input": "x"}, output={"output": "x"}, evaluation={"passed": True, "score": 1.0})
        ]
    )

    report.to_html(path)

    content = path.read_text()
    assert "Failed Cases" not in content
    assert "Failure Categories" not in content
