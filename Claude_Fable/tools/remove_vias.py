#!/usr/bin/env python3
"""Remove exact via coordinates from selected signals in an EAGLE board."""

import argparse
import re
import shutil
from pathlib import Path


SIGNAL_RE = re.compile(
    r'(<signal name="(?P<name>[^"]+)"[^>]*>)(?P<body>.*?)(</signal>)',
    re.DOTALL,
)
VIA_RE = re.compile(r'<via\b[^>]*(?:/>|>.*?</via>)', re.DOTALL)


def attr(tag, name):
    match = re.search(r'\b%s="([^"]+)"' % re.escape(name), tag)
    return match.group(1) if match else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board", type=Path)
    parser.add_argument("locations", nargs="+", help="NET:X:Y")
    parser.add_argument("--backup", type=Path)
    args = parser.parse_args()

    targets = set()
    for location in args.locations:
        try:
            net, x, y = location.rsplit(":", 2)
            targets.add((net, round(float(x), 4), round(float(y), 4)))
        except ValueError:
            parser.error("invalid location %r; expected NET:X:Y" % location)

    board = args.board.read_text(encoding="utf-8")
    removed = set()

    def replace_signal(signal_match):
        net = signal_match.group("name")

        def replace_via(via_match):
            tag = via_match.group(0)
            x, y = attr(tag, "x"), attr(tag, "y")
            if x is None or y is None:
                return tag
            key = (net, round(float(x), 4), round(float(y), 4))
            if key in targets:
                removed.add(key)
                return ""
            return tag

        body = VIA_RE.sub(replace_via, signal_match.group("body"))
        return signal_match.group(1) + body + signal_match.group(4)

    updated = SIGNAL_RE.sub(replace_signal, board)
    missing = targets - removed
    if missing:
        parser.error("vias not found: " + ", ".join(
            "%s:%.4f:%.4f" % location for location in sorted(missing)))
    if args.backup:
        args.backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.board, args.backup)
    args.board.write_text(updated, encoding="utf-8")
    print("Removed %d vias." % len(removed))


if __name__ == "__main__":
    main()
