# -*- coding: utf-8 -*-
"""Remove selected wire segments from one EAGLE/Fusion signal.

Set REMOVE_NET and REMOVE_POINTS (semicolon-separated x,y pairs). A wire is
removed when either endpoint exactly matches one of the selected points.
"""

import io
import os
import re
import xml.etree.ElementTree as ET


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRD = os.path.join(ROOT, "zulu_a7.brd")


def main():
    net = os.environ["REMOVE_NET"]
    points = {
        tuple(round(float(value), 4) for value in item.split(","))
        for item in os.environ["REMOVE_POINTS"].split(";")
        if item.strip()
    }
    board = io.open(BRD, encoding="utf-8", errors="replace").read()
    signal_match = re.search(
        r'(<signal name="%s"[^>]*>)(.*?)(</signal>)' % re.escape(net),
        board, re.S)
    if not signal_match:
        raise ValueError("signal not found: %s" % net)

    removed = []

    def keep_or_remove(match):
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', match.group(0)))
        endpoints = {
            (round(float(attrs["x1"]), 4), round(float(attrs["y1"]), 4)),
            (round(float(attrs["x2"]), 4), round(float(attrs["y2"]), 4)),
        }
        if endpoints & points:
            removed.append(match.group(0))
            return ""
        return match.group(0)

    body = re.sub(r"<wire\b[^>]*/>", keep_or_remove, signal_match.group(2))
    if not removed:
        raise ValueError("no matching wires found in %s" % net)
    updated_signal = signal_match.group(1) + body + signal_match.group(3)
    updated = board[:signal_match.start()] + updated_signal + board[signal_match.end():]
    ET.fromstring(updated)
    io.open(BRD, "w", encoding="utf-8", newline="").write(updated)
    print("removed %d wire(s) from %s" % (len(removed), net))


if __name__ == "__main__":
    main()
