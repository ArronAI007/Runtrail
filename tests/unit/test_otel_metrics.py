from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

from runtrail.evaluator.failure_classifier import FailureCategory
from runtrail.observability.otel_metrics import OTelMetrics
from runtrail.observability.reporter import Report
from runtrail.observability.trace import Trace


def _collect_metrics(reader: InMemoryMetricReader) -> dict[str, list]:
    data = reader.get_metrics_data()
    collected: dict[str, list] = {}
    for resource_metrics in data.resource_metrics:
        for scope_metrics in resource_metrics.scope_metrics:
            for metric in scope_metrics.metrics:
                collected[metric.name] = list(metric.data.data_points)
    return collected


def test_record_run_emits_pass_rate_and_case_counts():
    reader = InMemoryMetricReader()
    provider = MeterProvider(metric_readers=[reader])

    report = Report(
        traces=[
            Trace(case={"input": "a"}, output={"output": "a"}, evaluation={"passed": True, "score": 1.0}),
            Trace(case={"input": "b"}, output={}, evaluation={"passed": False, "score": 0.0}),
        ]
    )

    OTelMetrics(meter_provider=provider).record_run(report)

    metrics = _collect_metrics(reader)
    assert metrics["runtrail.run.pass_rate"][0].value == 0.5
    assert metrics["runtrail.run.total_cases"][0].value == 2
    assert metrics["runtrail.run.passed_cases"][0].value == 1


def test_record_run_emits_failure_category_counts_with_labels():
    reader = InMemoryMetricReader()
    provider = MeterProvider(metric_readers=[reader])

    report = Report(
        traces=[
            Trace(
                case={"input": "b"},
                output={},
                evaluation={"passed": False, "score": 0.0, "failure_category": "infinite_loop"},
            )
        ]
    )

    OTelMetrics(meter_provider=provider).record_run(report)

    metrics = _collect_metrics(reader)
    failure_points = metrics["runtrail.run.failure_category"]
    assert len(failure_points) == 1
    assert failure_points[0].value == 1
    assert dict(failure_points[0].attributes) == {"category": "infinite_loop"}


def test_record_run_uses_the_plain_value_for_a_real_failure_category_enum():
    # Same regression as test_reporter.py: a real FailureCategory enum member
    # must produce the plain string label "unknown", not "FailureCategory.UNKNOWN".
    reader = InMemoryMetricReader()
    provider = MeterProvider(metric_readers=[reader])

    report = Report(
        traces=[
            Trace(
                case={"input": "b"},
                output={},
                evaluation={"passed": False, "score": 0.0, "failure_category": FailureCategory.UNKNOWN},
            )
        ]
    )

    OTelMetrics(meter_provider=provider).record_run(report)

    metrics = _collect_metrics(reader)
    failure_points = metrics["runtrail.run.failure_category"]
    assert dict(failure_points[0].attributes) == {"category": "unknown"}


def test_record_run_handles_an_empty_report():
    reader = InMemoryMetricReader()
    provider = MeterProvider(metric_readers=[reader])

    OTelMetrics(meter_provider=provider).record_run(Report(traces=[]))

    metrics = _collect_metrics(reader)
    assert metrics["runtrail.run.pass_rate"][0].value == 0.0
    assert metrics["runtrail.run.total_cases"][0].value == 0
