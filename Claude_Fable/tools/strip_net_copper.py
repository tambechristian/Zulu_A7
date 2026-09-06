#!/usr/bin/env python3
"""Remove routed copper from selected board signals while preserving contacts."""

import argparse
import re
import xml.etree.ElementTree as ET
from pathlib import Path


SIGNAL_RE = re.compile(
    r'(<signal name="(?P<name>[^"]+)"[^>]*>)(?P<body>.*?)(</signal>)',
    re.DOTALL,
)
COPPER_RE = re.compile(
    r'<wire\b[^>]*/>|<via\b[^>]*?/>|<via\b[^>]*>.*?</via>',
    re.DOTALL,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board", type=Path)
    parser.add_argument("nets", help="comma-separated signal names")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    selected = {name.strip() for name in args.nets.split(",") if name.strip()}
    board = args.board.read_text(encoding="utf-8")
    removed = {}

    def strip_signal(match):
        name = match.group("name")
        if name not in selected:
            return match.group(0)
        body, count = COPPER_RE.subn("", match.group("body"))
        removed[name] = count
        return match.group(1) + body + match.group(4)

    updated = SIGNAL_RE.sub(strip_signal, board)
    missing = selected - set(removed)
    if missing:
        parser.error("signals not found: %s" % ", ".join(sorted(missing)))
    ET.fromstring(updated)
    output = args.output or args.board
    output.write_text(updated, encoding="utf-8")
    print("stripped %d copper object(s) from %d signal(s)" %
          (sum(removed.values()), len(removed)))


if __name__ == "__main__":
    main()
