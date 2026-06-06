from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from time import time
from typing import Optional, Dict, Any


@dataclass
class GpuSample:
    ts: float
    source: str
    gpu_name: str = "unknown"
    vram_total_mb: Optional[float] = None
    vram_used_mb: Optional[float] = None
    vram_free_mb: Optional[float] = None
    gpu_util_pct: Optional[float] = None
    mem_util_pct: Optional[float] = None
    temperature_c: Optional[float] = None
    power_w: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RouteStatus:
    ts: float
    route: str
    reason: str
    smoothed_vram_free_mb: Optional[float]
    cooldown_until: float
    cooldown_active: bool
    sample: Dict[str, Any]
    schema_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Add issued_at for precise timestamp
        from datetime import datetime, timezone
        d["issued_at"] = datetime.fromtimestamp(self.ts, tz=timezone.utc).isoformat()
        return d


class EWMASmoother:
    def __init__(self, alpha: float = 0.22):
        if not 0 < alpha <= 1:
            raise ValueError("alpha must be in (0, 1]")
        self.alpha = alpha
        self.values: Dict[str, float] = {}

    def update(self, key: str, value: Optional[float]) -> Optional[float]:
        if value is None:
            return self.values.get(key)
        if key not in self.values:
            self.values[key] = float(value)
        else:
            self.values[key] = self.alpha * float(value) + (1.0 - self.alpha) * self.values[key]
        return self.values[key]


class HysteresisRouter:
    """
    Conservative route selector with model-aware thresholds.

    CLEAR (LOCAL_CEREBELLUM): local model can load.
    MARGINAL (HYBRID): local lightweight checks only; cloud for heavy planning.
    BREACH (CLOUD_CORTEX): do not reload local model until cooldown expires.

    Thresholds are derived from model VRAM footprint:
    - clear_free_mb = model_vram_mb + safety_margin (default 512 MB)
    - breach_free_mb = model_vram_mb * 0.5
    """

    SCHEMA_VERSION = 1

    def __init__(
        self,
        model_vram_mb: float = 4500,  # 7B 4-bit quantized model default
        safety_margin_mb: float = 512,
        cooldown_seconds: float = 90,
        status_path: Optional[Path] = None,
    ):
        self.model_vram_mb = model_vram_mb
        self.safety_margin_mb = safety_margin_mb
        self.clear_free_mb = model_vram_mb + safety_margin_mb
        self.breach_free_mb = model_vram_mb * 0.5
        self.cooldown_seconds = cooldown_seconds
        self.cooldown_until = 0.0

        # Hydrate cooldown from persisted status on init
        if status_path and status_path.exists():
            try:
                data = json.loads(status_path.read_text(encoding="utf-8"))
                self.cooldown_until = float(data.get("cooldown_until", 0.0))
            except Exception:
                pass

    def decide(self, sample: GpuSample, smoothed_free_mb: Optional[float]) -> RouteStatus:
        now = time()
        cooldown_active = now < self.cooldown_until

        if smoothed_free_mb is None:
            return RouteStatus(
                ts=now,
                route="HYBRID",
                reason="No VRAM metric available; safest route is hybrid.",
                smoothed_vram_free_mb=None,
                cooldown_until=self.cooldown_until,
                cooldown_active=cooldown_active,
                sample=sample.to_dict(),
            )

        if smoothed_free_mb < self.breach_free_mb:
            # Extend cooldown (max) instead of resetting to prevent perpetual refresh on oscillation
            self.cooldown_until = max(self.cooldown_until, now + self.cooldown_seconds)
            return RouteStatus(
                ts=now,
                route="CLOUD_CORTEX",
                reason=f"Smoothed free VRAM {smoothed_free_mb:.0f} MB below breach threshold.",
                smoothed_vram_free_mb=smoothed_free_mb,
                cooldown_until=self.cooldown_until,
                cooldown_active=True,
                sample=sample.to_dict(),
            )

        if cooldown_active:
            return RouteStatus(
                ts=now,
                route="CLOUD_CORTEX",
                reason="Cooldown lock active after recent breach; refusing local reload.",
                smoothed_vram_free_mb=smoothed_free_mb,
                cooldown_until=self.cooldown_until,
                cooldown_active=True,
                sample=sample.to_dict(),
            )

        if smoothed_free_mb < self.clear_free_mb:
            return RouteStatus(
                ts=now,
                route="HYBRID",
                reason=f"Smoothed free VRAM {smoothed_free_mb:.0f} MB below clear threshold.",
                smoothed_vram_free_mb=smoothed_free_mb,
                cooldown_until=self.cooldown_until,
                cooldown_active=False,
                sample=sample.to_dict(),
            )

        return RouteStatus(
            ts=now,
            route="LOCAL_CEREBELLUM",
            reason=f"Smoothed free VRAM {smoothed_free_mb:.0f} MB above clear threshold.",
            smoothed_vram_free_mb=smoothed_free_mb,
            cooldown_until=self.cooldown_until,
            cooldown_active=False,
            sample=sample.to_dict(),
        )
