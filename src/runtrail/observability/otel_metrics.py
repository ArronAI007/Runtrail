from typing import Any

from runtrail.observability.reporter import Report


class OTelMetrics:
    """Pushes run metrics (pass rate, case/step/token counts, per-category
    failure counts) to an OpenTelemetry Collector via OTLP, or to any injected
    MeterProvider (useful for tests / custom exporters). A Collector can in
    turn feed these to Prometheus. Requires the 'otel' extra:
    pip install 'runtrail[otel]'.
    """

    def __init__(self, endpoint: str | None = None, *, meter_provider: Any = None):
        self.endpoint = endpoint
        self._meter_provider = meter_provider

    def _meter(self) -> Any:
        if self._meter_provider is not None:
            return self._meter_provider.get_meter("runtrail")

        try:
            from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
            from opentelemetry.sdk.metrics import MeterProvider
            from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        except ImportError as exc:
            raise ImportError(
                "OTelMetrics requires the 'otel' extra: pip install 'runtrail[otel]'"
            ) from exc

        exporter = OTLPMetricExporter(endpoint=self.endpoint)
        reader = PeriodicExportingMetricReader(exporter)
        provider = MeterProvider(metric_readers=[reader])
        return provider.get_meter("runtrail")

    def record_run(self, report: Report) -> None:
        meter = self._meter()
        stats = report.stats()

        pass_rate = meter.create_gauge("runtrail.run.pass_rate", description="Fraction of cases passed")
        pass_rate.set(stats["pass_rate"])

        total_cases = meter.create_counter("runtrail.run.total_cases")
        total_cases.add(stats["total"])

        passed_cases = meter.create_counter("runtrail.run.passed_cases")
        passed_cases.add(stats["passed"])

        avg_duration_ms = meter.create_gauge("runtrail.run.avg_duration_ms")
        avg_duration_ms.set(stats["avg_duration_ms"])

        avg_steps = meter.create_gauge("runtrail.run.avg_steps", description="Average steps per case")
        avg_steps.set(stats["avg_steps"])

        total_tokens = meter.create_counter("runtrail.run.total_tokens")
        total_tokens.add(stats["total_tokens"])

        failure_category = meter.create_counter("runtrail.run.failure_category")
        for category, count in stats["failure_category_counts"].items():
            failure_category.add(count, {"category": category})
