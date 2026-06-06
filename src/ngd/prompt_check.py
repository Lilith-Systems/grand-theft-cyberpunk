from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from .governor import NemotronGovernor
from .logging_config import add_logging_args, logging_config_from_args, setup_logging, get_logger


def main() -> int:
    parser = argparse.ArgumentParser(description="Quota-respecting Nemotron prompt governor.")
    _ = parser.add_argument("--runtime", default="runtime/nvidia_gratitude_driver")
    _ = parser.add_argument("--route-status", default="unknown")
    add_logging_args(parser)
    args = parser.parse_args()

    # Setup logging
    logging_config = logging_config_from_args(args)
    logging_config.log_file = logging_config.log_file or (Path(args.runtime) / "prompt_check.log")
    setup_logging(logging_config)
    logger = get_logger(__name__)

    prompt = sys.stdin.read()
    # Never log the prompt content - only hash and metadata
    prompt_hash = hashlib.sha256(prompt.encode("utf-8", errors="replace")).hexdigest()[:16]
    logger.info("prompt check started", extra={"prompt_hash": prompt_hash, "prompt_length": len(prompt), "route_status": args.route_status})

    gov = NemotronGovernor(Path(args.runtime) / "prompt_hash_cache.json")
    decision = gov.decide(prompt, route_status=args.route_status)

    logger.info("prompt check complete", extra={"prompt_hash": prompt_hash, "decision": decision.to_dict()})
    print(json.dumps(decision.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
