#!/usr/bin/env python3
"""Simple test runner for NGD."""
import sys
sys.path.insert(0, "src")

from tests.test_state import test_ewma_and_routes
test_ewma_and_routes()
print("test_state passed")

from tests.test_term_events import test_parses_mouse_and_focus
test_parses_mouse_and_focus()
print("test_term_events passed")

from tests.test_browser import test_browser_telemetry_is_aggregate
test_browser_telemetry_is_aggregate()
print("test_browser passed")

print("All tests passed!")