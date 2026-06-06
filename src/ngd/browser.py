from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore[assignment]

psutil_module: Optional[Any] = psutil


@dataclass
class BrowserTelemetry:
    detected: bool
    process_count: int
    working_set_mb: float
    gpu_process_count: int
    renderer_process_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def sample_chrome_processes() -> BrowserTelemetry:
    """Return aggregate Chrome process telemetry without reading browser content."""
    if psutil_module is None:
        return BrowserTelemetry(False, 0, 0.0, 0, 0)

    processes: list[Any] = []
    gpu_count = 0
    renderer_count = 0
    total_bytes = 0
    assert psutil_module is not None
    for process in psutil_module.process_iter(["name", "cmdline", "memory_info"]):
        if process.info.get("name", "").lower() != "chrome.exe":
            continue
        processes.append(process)
        cmdline: list[str] = process.info.get("cmdline") or []
        command = " ".join(cmdline)
        gpu_count += "--type=gpu-process" in command
        renderer_count += "--type=renderer" in command
        memory = process.info.get("memory_info")
        total_bytes += memory.rss if memory else 0
    return BrowserTelemetry(
        detected=bool(processes),
        process_count=len(processes),
        working_set_mb=round(total_bytes / (1024 * 1024), 2),
        gpu_process_count=gpu_count,
        renderer_process_count=renderer_count,
    )
