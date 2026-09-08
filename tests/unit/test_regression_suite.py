import pytest

from runtrail.observability.reporter import Report
from runtrail.observability.trace import Trace
from runtrail.runtime.regression import RegressionSuite


def _report(results: dict[str, bool]) -> Report:
    return Report(
        traces=[
            Trace(
                case={"input": inp},
                output={"output": inp},
                evaluation={"passed": passed, "score": 1.0 if passed else 0.0},
            )
            for inp, passed in results.items()
        ]
    )


def test_has_baseline_is_false_until_one_is_saved(tmp_path):
    suite = RegressionSuite("my_suite", baseline_dir=tmp_path)

    assert suite.has_baseline() is False

    suite.save_baseline(_report({"a": True, "b": True}))

    assert suite.has_baseline() is True


def test_load_baseline_raises_when_none_saved(tmp_path):
    suite = RegressionSuite("my_suite", baseline_dir=tmp_path)

    with pytest.raises(FileNotFoundError, match="my_suite"):
        suite.load_baseline()


def test_check_detects_a_newly_failing_case(tmp_path):
    suite = RegressionSuite("my_suite", baseline_dir=tmp_path)
    suite.save_baseline(_report({"a": True, "b": True}))

    result = suite.check(_report({"a": True, "b": False}))

    assert result.regressed is True
    assert [c["input"] for c in result.newly_failing] == ["b"]
    assert result.pass_rate_delta == pytest.approx(-0.5)


def test_check_reports_no_regression_when_pass_rate_holds_or_improves(tmp_path):
    suite = RegressionSuite("my_suite", baseline_dir=tmp_path)
    suite.save_baseline(_report({"a": True, "b": False}))

    result = suite.check(_report({"a": True, "b": True}))

    assert result.regressed is False
    assert result.newly_failing == []
    assert [c["input"] for c in result.newly_passing] == ["b"]
    assert result.pass_rate_delta == pytest.approx(0.5)


def test_check_ignores_cases_not_present_in_the_baseline(tmp_path):
    suite = RegressionSuite("my_suite", baseline_dir=tmp_path)
    suite.save_baseline(_report({"a": True}))

    result = suite.check(_report({"a": True, "new_case": False}))

    assert result.regressed is False
    assert result.newly_failing == []


def test_summary_mentions_the_pass_rate_change_and_regressed_cases(tmp_path):
    suite = RegressionSuite("my_suite", baseline_dir=tmp_path)
    suite.save_baseline(_report({"a": True, "b": True}))

    result = suite.check(_report({"a": True, "b": False}))
    text = result.summary()

    assert "REGRESSED" in text
    assert "'b'" in text
