from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from typing import Iterator

from .logging_config import add_logging_args, logging_config_from_args, setup_logging, get_logger


# Tolerates both real escape sequences and pasted stripped versions:
#   ESC [ < 35 ; 93 ; 23 M
#   [555;93;23M
MOUSE_RE = re.compile(r"(?:\x1b)?\[(?:<)?(?P<button>\d+);(?P<x>\d+);(?P<y>\d+)(?P<kind>[Mm])")
FOCUS_RE = re.compile(r"(?:\x1b)?\[(?P<kind>[IO])")


@dataclass
class TerminalEvent:
    type: str
    raw: str
    button: int | None = None
    x: int | None = None
    y: int | None = None
    action: str | None = None


def parse_terminal_events(text: str) -> Iterator[TerminalEvent]:
    matches: list[tuple[int, TerminalEvent]] = []

    for m in MOUSE_RE.finditer(text):
        matches.append((m.start(), TerminalEvent(
            type="mouse",
            raw=m.group(0),
            button=int(m.group("button")),
            x=int(m.group("x")),
            y=int(m.group("y")),
            action="press_or_motion" if m.group("kind") == "M" else "release",
        )))

    for m in FOCUS_RE.finditer(text):
        kind = m.group("kind")
        matches.append((m.start(), TerminalEvent(
            type="focus",
            raw=m.group(0),
            action="focus_in" if kind == "I" else "focus_out",
        )))

    for _, event in sorted(matches, key=lambda p: p[0]):
        yield event


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse terminal mouse and focus events from stdin.")
    add_logging_args(parser)
    args = parser.parse_args()

    # Setup logging
    logging_config = logging_config_from_args(args)
    setup_logging(logging_config)
    logger = get_logger(__name__)

    text = sys.stdin.read()
    logger.info("parsing terminal events", extra={"input_length": len(text)})
    event_count = 0
    for event in parse_terminal_events(text):
        print(json.dumps(asdict(event), ensure_ascii=False))
        event_count += 1
    logger.info("terminal events parsed", extra={"event_count": event_count})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
