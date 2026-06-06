from ngd.browser import sample_chrome_processes


def test_browser_telemetry_is_aggregate():
    telemetry = sample_chrome_processes().to_dict()
    assert set(telemetry) == {
        "detected", "process_count", "working_set_mb", "gpu_process_count", "renderer_process_count"
    }
