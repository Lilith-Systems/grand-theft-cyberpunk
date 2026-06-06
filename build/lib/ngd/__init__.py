"""
NVIDIA Gratitude Driver - Safe user-mode NVIDIA telemetry and edge-cloud routing companion.
"""

__version__ = "0.1.0"

# Export key modules
from .config import Config, LoggingConfig, load_config
from .driver import main as driver_main
from .gpu import GpuTelemetry
from .state import EWMASmoother, HysteresisRouter
from .logging_config import LoggingConfig as LoggingConfigClass, setup_logging, get_logger
from .slo import ALL_SLOs, SLO, generate_slo_report

# Optional tracing - only export if tracing is available
_tracing_available = False
try:
    from .tracing import (
        enable_tracing,
        trace_gpu_sample,
        trace_routing_decision,
        trace_log_write,
        is_tracing_enabled,
    )
    _tracing_available = True
except ImportError:
    pass

__all__ = [
    "Config",
    "LoggingConfig",
    "load_config",
    "driver_main",
    "GpuTelemetry",
    "EWMASmoother",
    "HysteresisRouter",
    "LoggingConfigClass",
    "setup_logging",
    "get_logger",
    "ALL_SLOs",
    "SLO",
    "generate_slo_report",
]
if _tracing_available:
    __all__.extend([
        "enable_tracing",
        "trace_gpu_sample",
        "trace_routing_decision",
        "trace_log_write",
        "is_tracing_enabled",
    ])