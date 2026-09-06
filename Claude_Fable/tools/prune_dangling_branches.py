# -*- coding: utf-8 -*-
"""Prune routed copper branches whose free end connects to no same-net object."""

import collections
import io
import math
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import escape as E


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRD = os.environ.get("PRUNE_BOARD", os.path.join(ROOT, "zulu_a7.brd"))
EPS = 0.002


def segment_distance(a, b, p):
    vx, vy = b[0] - a[0], b[1] - a[1]
    vv = vx * vx + vy * vy
    if vv == 0:
        return math.hypot(p[0] - a[0], p[1] - a[1])
    t = max(0.0, min(1.0, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / vv))
    return math.hypot(p[0] - (a[0] + t * vx), p[1] - (a[1] + t * vy))


def signal_support(board):
    support = collections.defaultdict(set)
    for net, x, y, _hx, _hy, _side in E.board_copper(board, skip=()):
        if net is not None:
            support[net].add((round(x, 4), round(y, 4)))
    for match in re.finditer(
            r'<signal name="([^"]+)"[^>]*>(.*?)</signal>', board, re.S):
        for via in re.finditer(r'<via x="([-\d.]+)" y="([-\d.]+)"', match.group(2)):
            support[match.group(1)].add(
                (round(float(via.group(1)), 4), round(float(via.group(2)), 4)))
    return support


def prune_signal(name, body, support):
    removed = []
    while True:
        wires = []
        for match in re.finditer(
                r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" '
                r'y2="([-\d.]+)" width="[\d.]+" layer="(\d+)"[^>]*/>', body):
            layer = int(match.group(5))
            if not 1 <= layer <= 16:
                continue
            a = (round(float(match.group(1)), 4), round(float(match.group(2)), 4))
            b = (round(float(match.group(3)), 4), round(float(match.group(4)), 4))
            wires.append((match, layer, a, b))

        degree = collections.Counter()
        for _match, layer, a, b in wires:
            degree[(layer, a)] += 1
            degree[(layer, b)] += 1

        victim = None
        for match, layer, a, b in wires:
            for point in (a, b):
                if degree[(layer, point)] != 1 or point in support:
                    continue
                crossings = sum(
                    1 for _other, other_layer, first, second in wires
                    if other_layer == layer
                    and segment_distance(first, second, point) <= EPS)
                if crossings == 1:
                    victim = match
                    break
            if victim is not None:
                break
        if victim is None:
            break
        removed.append(victim.group(0))
        body = body[:victim.start()] + body[victim.end():]
    return body, removed


def main():
    board = io.open(BRD, encoding="utf-8", errors="replace").read()
    support = signal_support(board)
    selected = {
        item.strip() for item in os.environ.get(
            "PRUNE_NETS",
            "VCC3V3,A12,D4,UDQM,FLASH-D02,FPGA-TDI,TDI,CLK-12M-FPGA"
        ).split(",") if item.strip()
    }
    all_signals = "*" in selected
    counts = {}

    def update(match):
        opening, name, body, closing = match.groups()
        if not all_signals and name not in selected:
            return match.group(0)
        body, removed = prune_signal(name, body, support[name])
        if removed:
            counts[name] = len(removed)
        return opening + body + closing

    updated = re.sub(
        r'(<signal name="([^"]+)"[^>]*>)(.*?)(</signal>)',
        update, board, flags=re.S)
    if not counts:
        raise ValueError("no dangling branches found in selected nets")
    ET.fromstring(updated)
    io.open(BRD, "w", encoding="utf-8", newline="").write(updated)
    print("pruned %d wire(s) from %d net(s)" % (sum(counts.values()), len(counts)))
    for net in sorted(counts):
        print("  %-16s %d" % (net, counts[net]))


if __name__ == "__main__":
    main()
