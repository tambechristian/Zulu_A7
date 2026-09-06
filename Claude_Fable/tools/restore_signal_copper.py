#!/usr/bin/env python3
"""Restore selected signals' routed copper from a known-good board."""

import argparse
import re
import shutil
from pathlib import Path


SIGNAL_RE = re.compile(
    r'(<signal name="(?P<name>[^"]+)"[^>]*>)(?P<body>.*?)(</signal>)',
    re.DOTALL,
)
WIRE_RE = re.compile(r'<wire\b[^>]*/>')
VIA_RE = re.compile(r'<via\b[^>]*(?:/>|>.*?</via>)', re.DOTALL)
LAYER_RE = re.compile(r'\blayer="(\d+)"')


def routed_copper(body):
    objects = VIA_RE.findall(body)
    for wire in WIRE_RE.findall(body):
        layer = LAYER_RE.search(wire)
        if layer and 1 <= int(layer.group(1)) <= 16:
            objects.append(wire)
    return objects


def remove_routed_copper(body):
    body = VIA_RE.sub("", body)

    def remove_wire(match):
        layer = LAYER_RE.search(match.group(0))
        if layer and 1 <= int(layer.group(1)) <= 16:
            return ""
        return match.group(0)

    return WIRE_RE.sub(remove_wire, body)


def signal_bodies(board):
    return {match.group("name"): match.group("body") for match in SIGNAL_RE.finditer(board)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board", type=Path)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("signals", nargs="+")
    parser.add_argument("--backup", type=Path)
    args = parser.parse_args()

    board = args.board.read_text(encoding="utf-8")
    baseline = args.baseline.read_text(encoding="utf-8")
    baseline_bodies = signal_bodies(baseline)
    requested = set(args.signals)
    missing = requested - baseline_bodies.keys()
    if missing:
        parser.error("signals absent from baseline: " + ", ".join(sorted(missing)))

    restored = {}

    def replace_signal(match):
        name = match.group("name")
        if name not in requested:
            return match.group(0)
        copper = routed_copper(baseline_bodies[name])
        body = remove_routed_copper(match.group("body"))
        indent = re.search(r'\n(\s*)<', body)
        pad = indent.group(1) if indent else "        "
        insertion = "".join("\n" + pad + obj.strip() for obj in copper)
        restored[name] = len(copper)
        return match.group(1) + body.rstrip() + insertion + "\n" + match.group(4)

    updated = SIGNAL_RE.sub(replace_signal, board)
    not_found = requested - restored.keys()
    if not_found:
        parser.error("signals absent from board: " + ", ".join(sorted(not_found)))
    if updated == board:
        parser.error("restoration made no changes")

    if args.backup:
        args.backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.board, args.backup)
    args.board.write_text(updated, encoding="utf-8")
    print("Restored %d signals (%d copper objects)." % (
        len(restored), sum(restored.values())))
    for name in sorted(restored):
        print("  %s: %d" % (name, restored[name]))


if __name__ == "__main__":
    main()
