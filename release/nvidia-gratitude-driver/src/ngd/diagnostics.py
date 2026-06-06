from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .browser import sample_chrome_processes
from .config import load_config
from .gpu import GpuTelemetry


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run safe NVIDIA Gratitude Driver diagnostics.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    _ = parser.add_argument(
        "--config",
        help="Path to config file (YAML or TOML).",
    )
    _ = parser.add_argument(
        "--runtime",
        help="Runtime output directory.",
    )
    _ = parser.add_argument(
        "--gpu-index",
        type=int,
        help="GPU index.",
    )
    _ = parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level.",
    )
    return parser


def _writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".diagnostic-probe"
        _ = probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except Exception:
        return False


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    # Build CLI overrides dict (only non-None values)
    cli_overrides = {
        k: v for k, v in {
            "runtime_dir": args.runtime,
            "gpu_index": args.gpu_index,
            "logging__level": args.log_level,
        }.items() if v is not None
    }

    # Load config (config file + env + CLI overrides)
    config = load_config(config_file=args.config, **cli_overrides)

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, config.logging.level),
        format=config.logging.format,
        datefmt=config.logging.datefmt,
    )
    log = logging.getLogger("ngd.diagnostics")

    runtime = config.get_runtime_path()
    sample = GpuTelemetry(index=config.gpu_index).sample()
    report = {
        "status": "pass" if sample.source != "unavailable" else "degraded",
        "gpu": sample.to_dict(),
        "chrome": sample_chrome_processes().to_dict(),
        "runtime_writable": _writable(runtime),
        "privacy": "aggregate process and GPU telemetry only; no browser content, credentials, or URLs read",
    }
    log.info(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["runtime_writable"] else 1


if __name__ == "__main__":
    sys.exit(main())