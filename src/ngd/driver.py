from __future__ import annotations

import argparse
import json
import os
import signal
import threading
import time
from contextvars import ContextVar
from pathlib import Path
from time import sleep
from typing import Any

from prometheus_client import Counter, Gauge, Histogram, start_http_server
from .gpu import GpuTelemetry
from .browser import sample_chrome_processes
from .state import EWMASmoother, HysteresisRouter
from .logging_config import (
    add_logging_args,
    logging_config_from_args,
    setup_logging,
    get_logger,
)

# Optional OpenTelemetry tracing
_enable_tracing = os.environ.get("NGD_enable_tracing", "").lower() in ("1", "true", "yes")
_otel_endpoint = os.environ.get("NGD_otel_endpoint")
_otel_service_name = os.environ.get("NGD_otel_service_name", "nvidia-gratitude-driver")
_otel_sample_rate = float(os.environ.get("NGD_otel_sample_rate", "1.0"))

if _enable_tracing:
    from .tracing import enable_tracing
    enable_tracing(
        service_name=_otel_service_name,
        endpoint=_otel_endpoint,
        sample_rate=_otel_sample_rate,
    )


# Prometheus metrics - lazy init to avoid duplicate registration on module reload
def _init_prometheus_metrics():
    """Initialize Prometheus metrics lazily to avoid duplicate registration."""
    global VRAM_FREE_GAUGE, VRAM_USED_GAUGE, VRAM_TOTAL_GAUGE, GPU_UTIL_GAUGE
    global MEM_UTIL_GAUGE, TEMPERATURE_GAUGE, POWER_GAUGE
    global ROUTE_COUNTER, SAMPLE_LATENCY, SAMPLE_ERRORS
    global _PROMETHEUS_INITIALIZED
    
    if "_PROMETHEUS_INITIALIZED" not in globals() or not _PROMETHEUS_INITIALIZED:
        VRAM_FREE_GAUGE = Gauge("ngd_vram_free_mb", "Free VRAM in MB")
        VRAM_USED_GAUGE = Gauge("ngd_vram_used_mb", "Used VRAM in MB")
        VRAM_TOTAL_GAUGE = Gauge("ngd_vram_total_mb", "Total VRAM in MB")
        GPU_UTIL_GAUGE = Gauge("ngd_gpu_util_percent", "GPU utilization percent")
        MEM_UTIL_GAUGE = Gauge("ngd_mem_util_percent", "Memory utilization percent")
        TEMPERATURE_GAUGE = Gauge("ngd_temperature_c", "GPU temperature in Celsius")
        POWER_GAUGE = Gauge("ngd_power_w", "GPU power draw in Watts")

        ROUTE_COUNTER = Counter("ngd_route_total", "Total routing decisions", ["route", "reason"])
        SAMPLE_LATENCY = Histogram("ngd_sample_latency_seconds", "Time spent sampling and routing")
        SAMPLE_ERRORS = Counter("ngd_sample_errors_total", "Total sampling errors")
        _PROMETHEUS_INITIALIZED = True

# Correlation ID for request tracing
_request_correlation_id: ContextVar[str] = ContextVar("request_correlation_id", default="")


def get_request_correlation_id() -> str:
    return _request_correlation_id.get()


def set_request_correlation_id(cid: str) -> None:
    _ = _request_correlation_id.set(cid)


def clear_request_correlation_id() -> None:
    _ = _request_correlation_id.set("")


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    _ = tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    _ = tmp.replace(path)


def append_jsonl(path: Path, payload: dict[str, Any], max_bytes: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size >= max_bytes:
        rotated = path.with_suffix(path.suffix + ".1")
        rotated.unlink(missing_ok=True)
        _ = path.replace(rotated)
    with path.open("a", encoding="utf-8") as f:
        _ = f.write(json.dumps(payload, sort_keys=True) + "\n")


class HealthServer:
    """Simple HTTP server for health checks and Prometheus metrics."""

    def __init__(self, port: int = 8080):
        self.port = port
        self._server = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the metrics server in a background thread."""
        self._thread = threading.Thread(target=self._run_server, daemon=True)
        self._thread.start()

    def _run_server(self) -> None:
        _ = start_http_server(self.port)

    def stop(self) -> None:
        """Stop the server (not strictly needed for daemon thread)."""
        pass


def main(argv: list[str] | None = None) -> int:
    global _enable_tracing, _otel_endpoint, _otel_service_name, _otel_sample_rate

    parser = argparse.ArgumentParser(description="NVIDIA Gratitude Driver: safe user-mode telemetry/router.")
    _ = parser.add_argument("--runtime", default="runtime/nvidia_gratitude_driver", help="Runtime output directory.")
    _ = parser.add_argument("--interval", type=float, default=1.0, help="Sampling interval seconds.")
    _ = parser.add_argument("--gpu-index", type=int, default=0, help="GPU index.")
    _ = parser.add_argument("--model-vram-mb", type=float, default=4500, help="VRAM footprint of local model (MB). Determines clear/breach thresholds.")
    _ = parser.add_argument("--safety-margin-mb", type=float, default=512, help="Safety margin above model VRAM for CLEAR threshold (MB).")
    _ = parser.add_argument("--cooldown-seconds", type=float, default=90, help="Cooldown after breach.")
    _ = parser.add_argument("--max-log-mb", type=float, default=10, help="Rotate telemetry log at this size.")
    _ = parser.add_argument("--no-browser-telemetry", action="store_true", help="Disable aggregate Chrome process telemetry.")
    _ = parser.add_argument("--metrics-port", type=int, default=9090, help="Prometheus metrics HTTP port (0 to disable).")
    _ = parser.add_argument("--health-port", type=int, default=8080, help="Health check HTTP port (0 to disable).")
    # OpenTelemetry tracing args
    _ = parser.add_argument("--enable-tracing", action="store_true", help="Enable OpenTelemetry tracing (env: NGD_enable_tracing)")
    _ = parser.add_argument("--otel-endpoint", type=str, help="OTLP endpoint (e.g., http://localhost:4317, env: NGD_otel_endpoint)")
    _ = parser.add_argument("--otel-service-name", type=str, default="nvidia-gratitude-driver", help="Service name for traces (env: NGD_otel_service_name)")
    _ = parser.add_argument("--otel-sample-rate", type=float, default=1.0, help="Trace sampling rate 0.0-1.0 (env: NGD_otel_sample_rate)")
    add_logging_args(parser)
    args = parser.parse_args(argv)

    # Update tracing config from CLI args (CLI overrides env)
    if args.enable_tracing:
        _enable_tracing = True
    if args.otel_endpoint:
        _otel_endpoint = args.otel_endpoint
    if args.otel_service_name:
        _otel_service_name = args.otel_service_name
    if args.otel_sample_rate:
        _otel_sample_rate = args.otel_sample_rate

    # Initialize tracing if enabled
    if _enable_tracing:
        from .tracing import enable_tracing
        enable_tracing(
            service_name=_otel_service_name,
            endpoint=_otel_endpoint,
            sample_rate=_otel_sample_rate,
        )

    # Initialize Prometheus metrics
    _init_prometheus_metrics()

    # Setup logging
    logging_config = logging_config_from_args(args)
    logging_config.log_file = logging_config.log_file or (Path(args.runtime) / "driver.log")
    setup_logging(logging_config)
    logger = get_logger(__name__)

    runtime = Path(args.runtime)
    status_path = runtime / "status.json"
    log_path = runtime / "telemetry.jsonl"

    gpu = GpuTelemetry(index=args.gpu_index)
    smoother = EWMASmoother(alpha=0.22)
    router = HysteresisRouter(
        model_vram_mb=args.model_vram_mb,
        safety_margin_mb=args.safety_margin_mb,
        cooldown_seconds=args.cooldown_seconds,
        status_path=status_path,
    )

    # Start health/metrics servers
    health_server = None
    if args.metrics_port > 0 or args.health_port > 0:
        port = args.metrics_port if args.metrics_port > 0 else args.health_port
        health_server = HealthServer(port)
        health_server.start()
        logger.info("started metrics/health server")

    running = True

    def stop(signum: int, frame: Any) -> None:
        nonlocal running
        running = False

    _ = signal.signal(signal.SIGINT, stop)
    _ = signal.signal(signal.SIGTERM, stop)

    logger.info("starting runtime")
    logger.info("press Ctrl+C to stop")

    try:
        while running:
            _start_time = time.time()

            # Trace GPU sampling
            if _enable_tracing:
                from .tracing import trace_gpu_sample
                with trace_gpu_sample():
                    with SAMPLE_LATENCY.time():
                        sample = gpu.sample()
            else:
                with SAMPLE_LATENCY.time():
                    sample = gpu.sample()

            # Update Prometheus metrics
            VRAM_FREE_GAUGE.set(sample.vram_free_mb or 0)
            VRAM_USED_GAUGE.set(sample.vram_used_mb or 0)
            VRAM_TOTAL_GAUGE.set(sample.vram_total_mb or 0)
            GPU_UTIL_GAUGE.set(sample.gpu_util_pct or 0)
            MEM_UTIL_GAUGE.set(sample.mem_util_pct or 0)
            if sample.temperature_c is not None:
                TEMPERATURE_GAUGE.set(sample.temperature_c)
            if sample.power_w is not None:
                POWER_GAUGE.set(sample.power_w)

            # Trace routing decision
            if _enable_tracing:
                from .tracing import trace_routing_decision
                with trace_routing_decision("", ""):
                    smoothed_free = smoother.update("vram_free_mb", sample.vram_free_mb)
                    status = router.decide(sample, smoothed_free)
            else:
                smoothed_free = smoother.update("vram_free_mb", sample.vram_free_mb)
                status = router.decide(sample, smoothed_free)

            payload = status.to_dict()
            payload["human"] = {
                "route": status.route,
                "reason": status.reason,
                "cooldown_seconds_remaining": max(0.0, status.cooldown_until - time.time()),
            }
            if not args.no_browser_telemetry:
                payload["browser"] = sample_chrome_processes().to_dict()

            # Increment route counter
            ROUTE_COUNTER.labels(route=status.route, reason=status.reason).inc()

            # Trace log writes
            if _enable_tracing:
                from .tracing import trace_log_write
                with trace_log_write(str(status_path)):
                    write_json_atomic(status_path, payload)
                with trace_log_write(str(log_path)):
                    append_jsonl(log_path, payload, max(1, int(args.max_log_mb * 1024 * 1024)))
            else:
                write_json_atomic(status_path, payload)
                append_jsonl(log_path, payload, max(1, int(args.max_log_mb * 1024 * 1024)))

            logger.debug("sample complete")
            sleep(max(0.1, args.interval))
    except Exception:
        SAMPLE_ERRORS.inc()
        logger.exception("driver loop error")
        return 1

    logger.info("stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())