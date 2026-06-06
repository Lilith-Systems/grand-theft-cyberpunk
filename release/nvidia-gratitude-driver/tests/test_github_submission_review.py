import importlib.util
import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / ".github" / "scripts" / "submission_review_gate.py"
SPEC = importlib.util.spec_from_file_location("submission_review_gate", SCRIPT)
assert SPEC and SPEC.loader
gate = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = gate
SPEC.loader.exec_module(gate)


def result(code: int) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], code, "", "")


def test_gate_approves_only_when_all_checks_and_ai_approve(tmp_path: Path) -> None:
    review = tmp_path / "review.json"
    review.write_text(json.dumps({"verdict": "approve", "findings": []}), encoding="utf-8")
    assert gate.evaluate(tmp_path, review, lambda command, cwd: result(0)) == 0


def test_gate_fails_when_ai_is_unavailable(tmp_path: Path) -> None:
    assert gate.evaluate(tmp_path, tmp_path / "missing.json", lambda command, cwd: result(0)) == 1


def test_gate_fails_when_a_deterministic_check_fails(tmp_path: Path) -> None:
    review = tmp_path / "review.json"
    review.write_text(json.dumps({"verdict": "approve", "findings": []}), encoding="utf-8")
    assert gate.evaluate(tmp_path, review, lambda command, cwd: result(1)) == 1


def test_ai_review_schema_is_fail_closed(tmp_path: Path) -> None:
    review = tmp_path / "review.json"
    review.write_text(json.dumps({"verdict": "approve", "findings": "none"}), encoding="utf-8")
    assert gate.validate_ai_review(review)[0] is False
