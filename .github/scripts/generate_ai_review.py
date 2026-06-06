#!/usr/bin/env python3
"""Generate a fail-closed review using an OpenAI-compatible chat endpoint."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path


def changed_diff(root: Path, base: str) -> str:
    result = subprocess.run(
        ["git", "diff", "--unified=1", f"{base}...HEAD"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "git diff failed")
    return result.stdout[-60_000:]


def generate(endpoint: str, token: str, model: str, diff: str) -> dict[str, object]:
    prompt = (
        "Review this GitHub submission for correctness, missing tests, and security. "
        "Return JSON only: {\"verdict\":\"approve|reject\",\"findings\":[\"...\"]}. "
        "Reject on any material issue.\n\n" + diff
    )
    body = json.dumps(
        {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0}
    ).encode()
    request = urllib.request.Request(
        endpoint,
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    content = payload["choices"][0]["message"]["content"]
    return json.loads(content)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--base", default=os.environ.get("REVIEW_BASE", "origin/main"))
    args = parser.parse_args()
    verdict: dict[str, object]
    try:
        token = os.environ["AI_REVIEW_TOKEN"]
        endpoint = os.environ["AI_REVIEW_ENDPOINT"]
        model = os.environ["AI_REVIEW_MODEL"]
        verdict = generate(endpoint, token, model, changed_diff(args.root, args.base))
    except (KeyError, OSError, RuntimeError, ValueError, urllib.error.URLError) as exc:
        verdict = {"verdict": "unavailable", "findings": [f"AI reviewer unavailable: {exc}"]}
    args.output.write_text(json.dumps(verdict) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
