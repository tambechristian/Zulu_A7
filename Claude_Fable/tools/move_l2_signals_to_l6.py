# -*- coding: utf-8 -*-
"""Move all non-GND signal traces from the L2 plane to the new empty L6."""

import io
import os
import re
import xml.etree.ElementTree as ET


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRD = os.path.join(ROOT, "zulu_a7.brd")


def main():
    board = io.open(BRD, encoding="utf-8", errors="replace").read()
    signals = re.search(r"(<signals>)(.*)(</signals>)", board, re.S)
    if not signals:
        raise ValueError("signals block not found")

    moved = [0]

    def move_signal(match):
        opening, name, body, closing = match.groups()
        if name == "GND":
            return match.group(0)

        def move_wire(wire):
            moved[0] += 1
            return wire.group(0).replace('layer="2"', 'layer="6"')

        body = re.sub(r'<wire\b[^>]*\blayer="2"[^>]*/>', move_wire, body)
        return opening + body + closing

    updated_body = re.sub(
        r'(<signal name="([^"]+)"[^>]*>)(.*?)(</signal>)', move_signal,
        signals.group(2), flags=re.S)
    if moved[0] != 1457:
        raise ValueError("expected 1457 non-GND L2 wires, found %d" % moved[0])

    updated = (board[:signals.start()] + signals.group(1) + updated_body
               + signals.group(3) + board[signals.end():])
    ET.fromstring(updated)
    io.open(BRD, "w", encoding="utf-8", newline="").write(updated)
    print("moved %d non-GND signal wires from L2 to L6" % moved[0])


if __name__ == "__main__":
    main()
