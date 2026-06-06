from ngd.state import EWMASmoother, GpuSample, HysteresisRouter


def sample(free: float) -> GpuSample:
    return GpuSample(ts=0, source="test", vram_free_mb=free)


def test_ewma_and_routes() -> None:
    smoother = EWMASmoother(alpha=1)
    # model=4096, margin=0 -> breach=2048, clear=4096
    router = HysteresisRouter(model_vram_mb=4096, safety_margin_mb=0, cooldown_seconds=0)
    assert router.decide(sample(5000), smoother.update("free", 5000)).route == "LOCAL_CEREBELLUM"
    assert router.decide(sample(3000), smoother.update("free", 3000)).route == "HYBRID"
    assert router.decide(sample(500), smoother.update("free", 500)).route == "CLOUD_CORTEX"


def test_cooldown_behavior() -> None:
    """Test that cooldown properly prevents route flip-flopping."""
    smoother = EWMASmoother(alpha=1)
    # 4000 MB default model VRAM: breach=2000, clear=4512 (4000+512 default margin)
    router = HysteresisRouter(model_vram_mb=4000, safety_margin_mb=512, cooldown_seconds=10)

    # Start above clear threshold
    assert router.decide(sample(5000), smoother.update("free", 5000)).route == "LOCAL_CEREBELLUM"

    # Drop below breach - should trigger cooldown
    status = router.decide(sample(1500), smoother.update("free", 1500))
    assert status.route == "CLOUD_CORTEX"
    assert status.cooldown_active

    # Even if VRAM recovers, cooldown should hold
    status = router.decide(sample(5000), smoother.update("free", 5000))
    assert status.route == "CLOUD_CORTEX"
    assert status.cooldown_active


def test_no_vram_fallback() -> None:
    """Test that None VRAM returns HYBRID as safe default."""
    smoother = EWMASmoother(alpha=1)
    router = HysteresisRouter(model_vram_mb=4000, safety_margin_mb=512, cooldown_seconds=0)
    sample_none = GpuSample(ts=0, source="test", vram_free_mb=None)
    status = router.decide(sample_none, smoother.update("free", None))
    assert status.route == "HYBRID"


def test_ewma_smoothing() -> None:
    """Test EWMA smoothing with alpha < 1."""
    smoother = EWMASmoother(alpha=0.5)
    v1 = smoother.update("free", 1000.0)
    v2 = smoother.update("free", 2000.0)
    # With alpha=0.5: v2 = 0.5 * 2000 + 0.5 * 1000 = 1500
    assert abs(v2 - 1500.0) < 0.1


def test_schema_version_in_route_status() -> None:
    """Test that RouteStatus includes schema_version."""
    smoother = EWMASmoother(alpha=1)
    router = HysteresisRouter(model_vram_mb=4000, safety_margin_mb=512, cooldown_seconds=0)
    status = router.decide(sample(5000), smoother.update("free", 5000))
    d = status.to_dict()
    assert "schema_version" in d
    assert d["schema_version"] == 1
    assert "issued_at" in d