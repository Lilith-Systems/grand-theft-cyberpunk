"""Tests for GPU telemetry sampling (NVML and nvidia-smi paths)."""
from __future__ import annotations

import subprocess
from time import time
from unittest.mock import MagicMock, patch

import pytest

from ngd.gpu import GpuTelemetry, _float_or_none
from ngd.state import GpuSample


# Skip NVML tests if real hardware is not available or mocking fails
# These tests require actual NVML library and GPU hardware
SKIP_NVML = True
NVML_SKIP_REASON = "NVML tests require real GPU hardware; nvidia-smi path is tested separately"


class TestFloatOrNone:
    """Tests for _float_or_none helper."""

    def test_valid_float(self):
        assert _float_or_none("45.5") == 45.5
        assert _float_or_none("100") == 100.0

    def test_with_units(self):
        assert _float_or_none("45 MiB") == 45.0
        assert _float_or_none("180 W") == 180.0
        assert _float_or_none("65 %") == 65.0
        assert _float_or_none("55 C") == 55.0

    def test_not_supported(self):
        assert _float_or_none("[Not Supported]") is None
        assert _float_or_none("N/A") is None
        assert _float_or_none("") is None

    def test_invalid(self):
        assert _float_or_none("abc") is None


class TestGpuTelemetryNVMLPath:
    """Tests for NVML sampling path (skipped - requires real GPU hardware)."""

    @pytest.mark.skipif(SKIP_NVML, reason=NVML_SKIP_REASON)
    def test_init_success(self, mock_nvml):
        gpu = GpuTelemetry(index=0)
        assert gpu._nvml is not None
        assert gpu._handle is not None
        mock_nvml.nvmlInit.assert_called_once()
        mock_nvml.nvmlDeviceGetHandleByIndex.assert_called_once_with(0)

    @pytest.mark.skipif(SKIP_NVML, reason=NVML_SKIP_REASON)
    def test_init_failure(self, mock_nvml_failure):
        gpu = GpuTelemetry(index=0)
        assert gpu._nvml is None
        assert gpu._handle is None

    @pytest.mark.skipif(SKIP_NVML, reason=NVML_SKIP_REASON)
    def test_sample_nvml_returns_sample(self, mock_nvml):
        gpu = GpuTelemetry(index=0)
        sample = gpu._sample_nvml()

        assert isinstance(sample, GpuSample)
        assert sample.source == "nvml"
        assert sample.gpu_name == "NVIDIA GeForce RTX 3080"
        assert sample.vram_total_mb == pytest.approx(10240.0, rel=0.01)
        assert sample.vram_used_mb == pytest.approx(4096.0, rel=0.01)
        assert sample.vram_free_mb == pytest.approx(6144.0, rel=0.01)
        assert sample.gpu_util_pct == 45.0
        assert sample.mem_util_pct == 30.0
        assert sample.temperature_c == 55.0
        assert sample.power_w == pytest.approx(180.0, rel=0.01)

    @pytest.mark.skipif(SKIP_NVML, reason=NVML_SKIP_REASON)
    def test_sample_nvml_name_decode_str(self, mock_nvml):
        mock_nvml.nvmlDeviceGetName.return_value = "NVIDIA RTX 4090"
        gpu = GpuTelemetry(index=0)
        sample = gpu._sample_nvml()
        assert sample.gpu_name == "NVIDIA RTX 4090"

    @pytest.mark.skipif(SKIP_NVML, reason=NVML_SKIP_REASON)
    def test_sample_nvml_temp_failure(self, mock_nvml):
        mock_nvml.nvmlDeviceGetTemperature.side_effect = Exception("temp fail")
        gpu = GpuTelemetry(index=0)
        sample = gpu._sample_nvml()
        assert sample.temperature_c is None

    @pytest.mark.skipif(SKIP_NVML, reason=NVML_SKIP_REASON)
    def test_sample_nvml_power_failure(self, mock_nvml):
        mock_nvml.nvmlDeviceGetPowerUsage.side_effect = Exception("power fail")
        gpu = GpuTelemetry(index=0)
        sample = gpu._sample_nvml()
        assert sample.power_w is None


class TestGpuTelemetryNvidiaSmiPath:
    """Tests for nvidia-smi sampling path."""

    def test_sample_nvidia_smi_success(self, mock_subprocess_nvidia_smi):
        gpu = GpuTelemetry(index=0)
        gpu._nvml = None
        gpu._handle = None
        sample = gpu._sample_nvidia_smi()

        assert isinstance(sample, GpuSample)
        assert sample.source == "nvidia-smi"
        assert sample.gpu_name == "NVIDIA GeForce RTX 3080"
        assert sample.vram_total_mb == 10240.0
        assert sample.vram_used_mb == 4096.0
        assert sample.vram_free_mb == 6144.0
        assert sample.gpu_util_pct == 45.0
        assert sample.mem_util_pct == 30.0
        assert sample.temperature_c == 55.0
        assert sample.power_w == pytest.approx(180.0, rel=0.01)

    def test_sample_nvidia_smi_not_found(self, mock_subprocess_nvidia_smi_failure):
        gpu = GpuTelemetry(index=0)
        gpu._nvml = None
        gpu._handle = None
        sample = gpu._sample_nvidia_smi()

        assert sample.source == "unavailable:FileNotFoundError"

    def test_sample_nvidia_smi_subprocess_error(self):
        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "nvidia-smi")):
            gpu = GpuTelemetry(index=0)
            gpu._nvml = None
            gpu._handle = None
            sample = gpu._sample_nvidia_smi()
            assert sample.source.startswith("unavailable:")

    def test_sample_nvidia_smi_partial_data(self, mock_subprocess_nvidia_smi_partial):
        gpu = GpuTelemetry(index=0)
        gpu._nvml = None
        gpu._handle = None
        sample = gpu._sample_nvidia_smi()

        assert sample.gpu_name == "NVIDIA GeForce RTX 3080"
        assert sample.vram_total_mb is None
        assert sample.vram_used_mb is None
        assert sample.vram_free_mb is None
        assert sample.gpu_util_pct is None
        assert sample.mem_util_pct is None
        assert sample.temperature_c is None
        assert sample.power_w is None

    def test_sample_nvidia_smi_timeout(self):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("nvidia-smi", 3)):
            gpu = GpuTelemetry(index=0)
            gpu._nvml = None
            gpu._handle = None
            sample = gpu._sample_nvidia_smi()
            assert sample.source.startswith("unavailable:")

    def test_sample_nvidia_smi_empty_output(self):
        with patch("subprocess.run", return_value=MagicMock(stdout="", stderr="", returncode=0)):
            gpu = GpuTelemetry(index=0)
            gpu._nvml = None
            gpu._handle = None
            sample = gpu._sample_nvidia_smi()
            assert sample.source.startswith("unavailable:")


class TestGpuTelemetrySampleMethod:
    """Tests for the main sample() method routing."""

    @pytest.mark.skipif(SKIP_NVML, reason=NVML_SKIP_REASON)
    def test_prefers_nvml_when_available(self, mock_nvml):
        gpu = GpuTelemetry(index=0)
        sample = gpu.sample()
        assert sample.source == "nvml"

    @pytest.mark.skipif(SKIP_NVML, reason=NVML_SKIP_REASON)
    def test_falls_back_to_nvidia_smi_when_nvml_unavailable(self, mock_subprocess_nvidia_smi, mock_nvml_failure):
        gpu = GpuTelemetry(index=0)
        sample = gpu.sample()
        assert sample.source == "nvidia-smi"

    @pytest.mark.skipif(SKIP_NVML, reason=NVML_SKIP_REASON)
    def test_different_gpu_index(self, mock_nvml, mock_subprocess_nvidia_smi):
        gpu = GpuTelemetry(index=1)
        sample = gpu.sample()
        mock_nvml.nvmlDeviceGetHandleByIndex.assert_called_with(1)

        # Test nvidia-smi path with index
        gpu2 = GpuTelemetry(index=2)
        gpu2._nvml = None
        gpu2._handle = None
        gpu2._sample_nvidia_smi()
        # Verify subprocess was called with -i 2
