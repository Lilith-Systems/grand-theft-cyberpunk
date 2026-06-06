"""
SLO (Service Level Objectives) definitions for NVIDIA Gratitude Driver.

Defines availability and latency targets for telemetry collection.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SLO:
    """Service Level Objective definition."""
    name: str
    description: str
    target: float  # 0.0 to 1.0 (e.g., 0.999 for 99.9%)
    window: str  # e.g., "30d", "7d", "24h"
    unit: str = "ratio"


# Telemetry Collection SLOs
TELEMETRY_COLLECTION_AVAILABILITY = SLO(
    name="telemetry_collection_availability",
    description="Percentage of successful telemetry collection cycles",
    target=0.999,  # 99.9%
    window="30d",
)

TELEMETRY_COLLECTION_LATENCY_P50 = SLO(
    name="telemetry_collection_latency_p50",
    description="Median latency for telemetry sampling and routing decision",
    target=0.1,  # 100ms
    window="30d",
    unit="seconds",
)

TELEMETRY_COLLECTION_LATENCY_P95 = SLO(
    name="telemetry_collection_latency_p95",
    description="95th percentile latency for telemetry sampling and routing decision",
    target=0.5,  # 500ms
    window="30d",
    unit="seconds",
)

TELEMETRY_COLLECTION_LATENCY_P99 = SLO(
    name="telemetry_collection_latency_p99",
    description="99th percentile latency for telemetry sampling and routing decision",
    target=1.0,  # 1s
    window="30d",
    unit="seconds",
)

# GPU Metrics Export SLOs
METRICS_EXPORT_AVAILABILITY = SLO(
    name="metrics_export_availability",
    description="Percentage of successful Prometheus metric exports",
    target=0.999,
    window="30d",
)

HEALTH_ENDPOINT_AVAILABILITY = SLO(
    name="health_endpoint_availability",
    description="Health check endpoint availability",
    target=0.9999,  # 99.99%
    window="30d",
)

# Log Delivery SLOs
LOG_DELIVERY_AVAILABILITY = SLO(
    name="log_delivery_availability",
    description="Percentage of log entries successfully written to disk",
    target=0.9999,
    window="30d",
)

LOG_ROTATION_SUCCESS = SLO(
    name="log_rotation_success",
    description="Percentage of successful log rotations without data loss",
    target=1.0,  # 100%
    window="30d",
)


ALL_SLOs = [
    TELEMETRY_COLLECTION_AVAILABILITY,
    TELEMETRY_COLLECTION_LATENCY_P50,
    TELEMETRY_COLLECTION_LATENCY_P95,
    TELEMETRY_COLLECTION_LATENCY_P99,
    METRICS_EXPORT_AVAILABILITY,
    HEALTH_ENDPOINT_AVAILABILITY,
    LOG_DELIVERY_AVAILABILITY,
    LOG_ROTATION_SUCCESS,
]


def get_slo_by_name(name: str) -> Optional[SLO]:
    """Get SLO by name."""
    for slo in ALL_SLOs:
        if slo.name == name:
            return slo
    return None


def generate_slo_report() -> str:
    """Generate a human-readable SLO report."""
    lines = ["# NVIDIA Gratitude Driver - SLO Definitions", ""]
    for slo in ALL_SLOs:
        if slo.unit == "ratio":
            target_str = f"{slo.target * 100:.2f}%"
        else:
            target_str = f"{slo.target}{slo.unit}"
        lines.append(f"- **{slo.name}**: {slo.description}")
        lines.append(f"  - Target: {target_str} over {slo.window}")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    print(generate_slo_report())