from __future__ import annotations

import csv
import subprocess
from time import time
from typing import Any, Optional

from .state import GpuSample

# pynvml (nvidia-ml-py) lacks type stubs; suppress import errors
try:
    import pynvml  # type: ignore[import-untyped]
except ImportError:
    pynvml = None


def _float_or_none(value: str) -> Optional[float]:
    try:
        cleaned = value.strip().replace(" MiB", "").replace(" W", "").replace(" %", "").replace(" C", "")
        if cleaned in {"", "[Not Supported]", "N/A"}:
            return None
        return float(cleaned)
    except Exception:
        return None


class _NvmlMemoryInfoProtocol:
    """Protocol for nvmlDeviceGetMemoryInfo return type."""
    total: int
    used: int
    free: int


class _NvmlUtilizationProtocol:
    """Protocol for nvmlDeviceGetUtilizationRates return type."""
    gpu: int
    memory: int


class GpuTelemetry:
    def __init__(self, index: int = 0):
        self.index = index
        self._nvml: Any = None
        self._handle: Any = None
        if pynvml is not None:
            try:
                pynvml.nvmlInit()
                self._nvml = pynvml
                self._handle = pynvml.nvmlDeviceGetHandleByIndex(index)
            except Exception:
                self._nvml = None
                self._handle = None

    def sample(self) -> GpuSample:
        if self._nvml is not None and self._handle is not None:
            return self._sample_nvml()
        return self._sample_nvidia_smi()

    def _sample_nvml(self) -> GpuSample:
        n = self._nvml
        h = self._handle
        assert n is not None and h is not None  # narrowed by sample()
        name: Any = n.nvmlDeviceGetName(h)
        if isinstance(name, bytes):
            name = name.decode("utf-8", errors="replace")

        mem: _NvmlMemoryInfoProtocol = n.nvmlDeviceGetMemoryInfo(h)
        util: _NvmlUtilizationProtocol = n.nvmlDeviceGetUtilizationRates(h)

        try:
            temp = float(n.nvmlDeviceGetTemperature(h, n.NVML_TEMPERATURE_GPU))
        except Exception:
            temp = None

        try:
            power_w = float(n.nvmlDeviceGetPowerUsage(h)) / 1000.0
        except Exception:
            power_w = None

        return GpuSample(
            ts=time(),
            source="nvml",
            gpu_name=str(name),
            vram_total_mb=mem.total / (1024 * 1024),
            vram_used_mb=mem.used / (1024 * 1024),
            vram_free_mb=mem.free / (1024 * 1024),
            gpu_util_pct=float(util.gpu),
            mem_util_pct=float(util.memory),
            temperature_c=temp,
            power_w=power_w,
        )

    def _sample_nvidia_smi(self) -> GpuSample:
        query = ",".join([
            "name",
            "memory.total",
            "memory.used",
            "memory.free",
            "utilization.gpu",
            "utilization.memory",
            "temperature.gpu",
            "power.draw",
        ])
        cmd = [
            "nvidia-smi",
            f"--query-gpu={query}",
            "--format=csv,noheader,nounits",
            "-i",
            str(self.index),
        ]
        try:
            cp = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=3)
            lines = cp.stdout.strip().splitlines()
            if not lines:
                return GpuSample(ts=time(), source="unavailable:EmptyOutput")
            row = next(csv.reader([lines[0]]))
            return GpuSample(
                ts=time(),
                source="nvidia-smi",
                gpu_name=row[0].strip(),
                vram_total_mb=_float_or_none(row[1]),
                vram_used_mb=_float_or_none(row[2]),
                vram_free_mb=_float_or_none(row[3]),
                gpu_util_pct=_float_or_none(row[4]),
                mem_util_pct=_float_or_none(row[5]),
                temperature_c=_float_or_none(row[6]),
                power_w=_float_or_none(row[7]),
            )
        except Exception as exc:
            return GpuSample(ts=time(), source=f"unavailable:{type(exc).__name__}")
