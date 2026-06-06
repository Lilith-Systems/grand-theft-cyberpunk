#!/usr/bin/env python3
"""Fail-closed GitHub submission review gate."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence


@dataclass(frozen=True)
class Check:
    name: str
    command: tuple[str, ...]


CHECKS = (
    Check("tests", (sys.executable, "-m", "pytest")),
    Check("lint", (sys.executable, "-m", "ruff", "check", "src", "tests")),
    Check("security", (sys.executable, "-m", "bandit", "-q", "-r", "src")),
    Check("dependencies", (sys.executable, "-m", "pip_audit")),
)


def run_command(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)


def validate_ai_review(review_file: Path) -> tuple[bool, str]:
    try:
        payload = json.loads(review_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"AI review unavailable or invalid: {exc}"
    if payload.get("verdict") != "approve":
        return False, f"AI review blocked submission: {payload.get('verdict', 'missing verdict')}"
    findings = payload.get("findings")
    if not isinstance(findings, list):
        return False, "AI review invalid: findings must be a list"
    return True, "AI review approved"


def evaluate(
    root: Path,
    review_file: Path,
    runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]] = run_command,
) -> int:
    failed = False
    for check in CHECKS:
        result = runner(check.command, root)
        status = "PASS" if result.returncode == 0 else "FAIL"
        print(f"[{status}] {check.name}")
        if result.returncode:
            failed = True
            output = (result.stdout + result.stderr).strip()
            if output:
                print(output[-4000:])
    ai_ok, message = validate_ai_review(review_file)
    print(f"[{'PASS' if ai_ok else 'FAIL'}] {message}")
    return 1 if failed or not ai_ok else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--ai-review",
        type=Path,
        default=Path(os.environ.get("AI_REVIEW_FILE", ".github/ai-review.json")),
    )
    args = parser.parse_args()
    return evaluate(args.root.resolve(), args.ai_review.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
