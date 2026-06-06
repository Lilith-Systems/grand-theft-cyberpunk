from __future__ import annotations

import contextlib
from typing import Any, Generator, Optional

# Global state for tracing
_tracing_enabled = False
_tracer: Any = None
_meter: Any = None


def enable_tracing(
    service_name: str = "nvidia-gratitude-driver",
    endpoint: Optional[str] = None,
    sample_rate: float = 1.0,
) -> None:
    """Enable OpenTelemetry tracing if dependencies are available."""
    global _tracing_enabled, _tracer, _meter

    try:
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.trace import set_tracer_provider, get_tracer
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
        from opentelemetry.metrics import set_meter_provider, get_meter

        resource = Resource(attributes={SERVICE_NAME: service_name})
        trace_provider = TracerProvider(resource=resource)

        if endpoint:
            otlp_exporter = OTLPSpanExporter(endpoint=endpoint)
            trace_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

        set_tracer_provider(trace_provider)
        _tracer = get_tracer(service_name)

        # Metrics
        metric_readers = []
        if endpoint:
            metric_exporter = OTLPMetricExporter(endpoint=endpoint)
            metric_readers.append(PeriodicExportingMetricReader(metric_exporter))

        meter_provider = MeterProvider(resource=resource, metric_readers=metric_readers)
        set_meter_provider(meter_provider)
        _meter = get_meter(service_name)

        _tracing_enabled = True
    except ImportError:
        # OpenTelemetry not available, tracing remains disabled
        _tracing_enabled = False


def is_tracing_enabled() -> bool:
    """Check if tracing is enabled."""
    return _tracing_enabled


@contextlib.contextmanager
def trace_gpu_sample() -> Generator[None, None, None]:
    """Context manager for GPU sampling trace."""
    if not _tracing_enabled or _tracer is None:
        yield
        return

    with _tracer.start_as_current_span("gpu_sample") as span:
        try:
            yield span
        except Exception as e:
            span.record_exception(e)
            raise


@contextlib.contextmanager
def trace_routing_decision(route: str, reason: str) -> Generator[None, None, None]:
    """Context manager for routing decision trace."""
    if not _tracing_enabled or _tracer is None:
        yield
        return

    with _tracer.start_as_current_span("routing_decision") as span:
        span.set_attribute("route", route)
        span.set_attribute("reason", reason)
        try:
            yield span
        except Exception as e:
            span.record_exception(e)
            raise


@contextlib.contextmanager
def trace_log_write(path: str) -> Generator[None, None, None]:
    """Context manager for log write trace."""
    if not _tracing_enabled or _tracer is None:
        yield
        return

    with _tracer.start_as_current_span("log_write") as span:
        span.set_attribute("path", path)
        try:
            yield span
        except Exception as e:
            span.record_exception(e)
            raise