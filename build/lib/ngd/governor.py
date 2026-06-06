from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from time import time
from typing import Dict, Any

from .logging_config import get_logger


@dataclass
class PromptDecision:
    ts: float
    prompt_hash: str
    route_hint: str
    compression_hint: str
    provider_respect: str
    estimated_chars: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class NemotronGovernor:
    """
    Quota-respecting helper. It does not call an API and does not bypass rate limits.
    It helps reduce waste by detecting repeated prompts and recommending compression/caching.
    """

    # Cache TTL in seconds (30 days default)
    CACHE_TTL_SECONDS = 30 * 24 * 3600

    def __init__(self, cache_path: Path):
        self.cache_path = cache_path
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.cache_path.exists():
            _ = self.cache_path.write_text("{}", encoding="utf-8")
        self._logger = get_logger(__name__)

    def _load_cache(self) -> dict[str, Any]:
        try:
            data: Any = json.loads(self.cache_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
            return {}
        except Exception:
            return {}

    def _save_cache(self, cache: dict[str, Any]) -> None:
        tmp = self.cache_path.with_suffix(".tmp")
        _ = tmp.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")
        _ = tmp.replace(self.cache_path)

    def decide(self, prompt: str, route_status: str = "unknown") -> PromptDecision:
        # Use full SHA256 to eliminate collision risk
        h = hashlib.sha256(prompt.encode("utf-8", errors="replace")).hexdigest()
        cache = self._load_cache()
        now = time()

        # Evict stale entries
        cache = {k: v for k, v in cache.items() if now - v.get("last_seen", 0) < self.CACHE_TTL_SECONDS}

        seen = h in cache
        cache[h] = {"last_seen": now, "chars": len(prompt), "count": cache.get(h, {}).get("count", 0) + 1}
        self._save_cache(cache)

        if seen:
            compression_hint = "Repeated prompt hash: use cached answer or send delta only."
        elif len(prompt) > 12000:
            compression_hint = "Large prompt: send objective, constraints, file hashes, failing traces, and pruned AST context."
        elif len(prompt) > 4000:
            compression_hint = "Medium prompt: compress logs and preserve only state mutations, errors, and interfaces."
        else:
            compression_hint = "Small prompt: direct request is acceptable."

        if route_status == "CLOUD_CORTEX":
            route_hint = "Cloud OK, but batch related questions and use exponential backoff on provider errors."
        elif route_status == "LOCAL_CEREBELLUM":
            route_hint = "Local precheck first; send only high-entropy synthesis to Nemotron."
        else:
            route_hint = "Hybrid: local intent parse + cloud strategic reasoning."

        self._logger.debug(
            "prompt decision",
            extra={
                "prompt_hash": h,
                "prompt_length": len(prompt),
                "seen_before": seen,
                "route_status": route_status,
                "compression_hint": compression_hint,
                "route_hint": route_hint,
            },
        )

        return PromptDecision(
            ts=now,
            prompt_hash=h,
            route_hint=route_hint,
            compression_hint=compression_hint,
            provider_respect="Do not bypass rate limits, rotate accounts, or automate abusive traffic. Optimize by reducing waste.",
            estimated_chars=len(prompt),
        )