"""Tests for NemotronGovernor prompt deduplication and routing hints."""
from __future__ import annotations

import json
from time import time

import pytest

from ngd.governor import NemotronGovernor, PromptDecision


class TestNemotronGovernor:
    """Tests for NemotronGovernor cache and decision logic."""

    def test_cache_miss_returns_decision(self, temp_cache_path):
        """First prompt should be a cache miss with appropriate hint."""
        gov = NemotronGovernor(temp_cache_path)
        decision = gov.decide("Test prompt for Nemotron", "HYBRID")

        assert isinstance(decision, PromptDecision)
        assert decision.prompt_hash == "4b78ba38175213a072c0a486a2f0328f7f51922bbfbcf0303271d2296c65c082"
        assert "Small prompt" in decision.compression_hint
        assert "Hybrid" in decision.route_hint
        assert decision.provider_respect == "Do not bypass rate limits, rotate accounts, or automate abusive traffic. Optimize by reducing waste."

    def test_cache_hit_detects_repeated_prompt(self, temp_cache_path):
        """Repeated prompt should be detected and suggest cache usage."""
        gov = NemotronGovernor(temp_cache_path)

        # First call - cache miss
        decision1 = gov.decide("Unique prompt for testing", "HYBRID")
        assert "Small prompt" in decision1.compression_hint

        # Second call - same prompt, should be cache hit
        decision2 = gov.decide("Unique prompt for testing", "HYBRID")
        assert "Repeated prompt hash" in decision2.compression_hint
        assert decision2.prompt_hash == decision1.prompt_hash

    def test_large_prompt_suggests_compression(self, temp_cache_path):
        """Prompts >12k chars should suggest aggressive compression."""
        gov = NemotronGovernor(temp_cache_path)
        large_prompt = "x" * 15000

        decision = gov.decide(large_prompt, "CLOUD_CORTEX")
        assert "Large prompt" in decision.compression_hint
        assert "objective, constraints, file hashes" in decision.compression_hint

    def test_medium_prompt_suggests_medium_compression(self, temp_cache_path):
        """Prompts 4000-12000 chars should suggest medium compression."""
        gov = NemotronGovernor(temp_cache_path)
        medium_prompt = "x" * 8000

        decision = gov.decide(medium_prompt, "LOCAL_CEREBELLUM")
        assert "Medium prompt" in decision.compression_hint
        assert "state mutations, errors, and interfaces" in decision.compression_hint

    def test_route_hints_differ_by_status(self, temp_cache_path):
        """Route hints should vary based on route_status."""
        gov = NemotronGovernor(temp_cache_path)

        cloud = gov.decide("test", "CLOUD_CORTEX")
        local = gov.decide("test", "LOCAL_CEREBELLUM")
        hybrid = gov.decide("test", "HYBRID")

        assert "batch related questions" in cloud.route_hint
        assert "exponential backoff" in cloud.route_hint
        assert "Local precheck" in local.route_hint
        assert "high-entropy synthesis" in local.route_hint
        assert "local intent parse" in hybrid.route_hint
        assert "cloud strategic reasoning" in hybrid.route_hint

    def test_cache_persists_to_disk(self, temp_cache_path):
        """Cache should be persisted and survive re-instantiation."""
        gov1 = NemotronGovernor(temp_cache_path)
        gov1.decide("persistent prompt", "HYBRID")

        # New governor instance should see cached entry
        gov2 = NemotronGovernor(temp_cache_path)
        decision = gov2.decide("persistent prompt", "HYBRID")
        assert "Repeated prompt hash" in decision.compression_hint

    def test_cache_ttl_evicts_stale_entries(self, temp_cache_path):
        """Entries older than CACHE_TTL_SECONDS should be evicted."""
        gov = NemotronGovernor(temp_cache_path)
        gov.decide("old prompt", "HYBRID")

        # Manually age the cache entry
        import json
        cache = json.loads(temp_cache_path.read_text())
        for key in cache:
            cache[key]["last_seen"] = 0  # ancient timestamp
        temp_cache_path.write_text(json.dumps(cache))

        # New decision should not see the aged entry
        gov2 = NemotronGovernor(temp_cache_path)
        decision = gov2.decide("old prompt", "HYBRID")
        assert "Small prompt" in decision.compression_hint  # Not a repeat

    def test_full_sha256_hash_used(self, temp_cache_path):
        """Governor should use full 64-char SHA256, not truncated."""
        gov = NemotronGovernor(temp_cache_path)
        decision = gov.decide("hash test", "HYBRID")

        # Full SHA256 is 64 hex characters
        assert len(decision.prompt_hash) == 64

    def test_estimated_chars_accurate(self, temp_cache_path):
        """estimated_chars should match prompt length."""
        gov = NemotronGovernor(temp_cache_path)

        for length in [10, 100, 1000, 50000]:
            prompt = "x" * length
            decision = gov.decide(prompt, "HYBRID")
            assert decision.estimated_chars == length


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
