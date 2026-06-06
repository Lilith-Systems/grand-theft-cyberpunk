"""Pytest fixtures for mocking NVML, psutil, subprocess."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_nvml():
    """Mock pynvml module for NVML path testing."""
    mock = MagicMock()
    mock.nvmlInit.return_value = None
    mock.nvmlDeviceGetHandleByIndex.return_value = "mock_handle"
    mock.nvmlDeviceGetName.return_value = b"NVIDIA GeForce RTX 3080"
    mock.nvmlDeviceGetMemoryInfo.return_value = MagicMock(
        total=10 * 1024 * 1024 * 1024,  # 10 GB
        used=4 * 1024 * 1024 * 1024,    # 4 GB
        free=6 * 1024 * 1024 * 1024,    # 6 GB
    )
    mock.nvmlDeviceGetUtilizationRates.return_value = MagicMock(gpu=45, memory=30)
    mock.nvmlDeviceGetTemperature.return_value = 55
    mock.nvmlDeviceGetPowerUsage.return_value = 180000  # in mW
    mock.NVML_TEMPERATURE_GPU = 0

    with patch.dict(sys.modules, {"pynvml": mock}):
        yield mock


@pytest.fixture
def mock_nvml_failure():
    """Mock pynvml that fails to initialize."""
    # Remove any cached ngd.gpu module to allow re-import with mocked pynvml
    modules_to_remove = [k for k in sys.modules if k.startswith('ngd.gpu')]
    for mod in modules_to_remove:
        sys.modules.pop(mod, None)

    real_import = __import__

    def mock_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "pynvml":
            raise ImportError("No module named 'pynvml'")
        return real_import(name, globals, locals, fromlist, level)

    with patch.dict(sys.modules, {"pynvml": None}):
        with patch("builtins.__import__", side_effect=mock_import):
            yield


@pytest.fixture
def mock_subprocess_nvidia_smi():
    """Mock subprocess.run for nvidia-smi path testing."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="NVIDIA GeForce RTX 3080, 10240, 4096, 6144, 45, 30, 55, 180.0",
            stderr="",
            returncode=0,
        )
        yield mock_run


@pytest.fixture
def mock_subprocess_nvidia_smi_failure():
    """Mock subprocess.run for nvidia-smi failure."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError("nvidia-smi not found")
        yield mock_run


@pytest.fixture
def mock_subprocess_nvidia_smi_partial():
    """Mock subprocess.run for nvidia-smi with partial/unavailable data."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="NVIDIA GeForce RTX 3080, [Not Supported], [Not Supported], [Not Supported], [Not Supported], [Not Supported], [Not Supported], [Not Supported]",
            stderr="",
            returncode=0,
        )
        yield mock_run


@pytest.fixture
def mock_psutil_no_chrome():
    """Mock psutil with no Chrome processes."""
    with patch("psutil.process_iter") as mock_iter:
        mock_iter.return_value = []
        yield mock_iter


@pytest.fixture
def mock_psutil_with_chrome():
    """Mock psutil with Chrome processes."""
    mock_proc1 = MagicMock()
    mock_proc1.info = {
        "name": "chrome.exe",
        "cmdline": ["chrome.exe", "--type=renderer"],
        "memory_info": MagicMock(rss=200 * 1024 * 1024),
    }

    mock_proc2 = MagicMock()
    mock_proc2.info = {
        "name": "chrome.exe",
        "cmdline": ["chrome.exe", "--type=gpu-process"],
        "memory_info": MagicMock(rss=150 * 1024 * 1024),
    }

    mock_proc3 = MagicMock()
    mock_proc3.info = {
        "name": "chrome.exe",
        "cmdline": ["chrome.exe"],
        "memory_info": MagicMock(rss=100 * 1024 * 1024),
    }

    # Non-Chrome process should be ignored
    mock_proc4 = MagicMock()
    mock_proc4.info = {
        "name": "notepad.exe",
        "cmdline": ["notepad.exe"],
        "memory_info": MagicMock(rss=50 * 1024 * 1024),
    }

    with patch("psutil.process_iter") as mock_iter:
        mock_iter.return_value = [mock_proc1, mock_proc2, mock_proc3, mock_proc4]
        yield mock_iter


@pytest.fixture
def mock_psutil_exception():
    """Mock psutil raising exception."""
    with patch("psutil.process_iter", side_effect=Exception("psutil error")):
        yield


@pytest.fixture
def temp_cache_path(tmp_path):
    """Temporary cache path for NemotronGovernor."""
    return tmp_path / "prompt_hash_cache.json"


@pytest.fixture
def temp_runtime_dir(tmp_path):
    """Temporary runtime directory."""
    return tmp_path / "runtime"


@pytest.fixture
def mock_time():
    """Mock time.time for deterministic testing."""
    with patch("time.time", return_value=1234567890.0) as mock:
        yield mock
