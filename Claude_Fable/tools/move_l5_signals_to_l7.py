# -*- coding: utf-8 -*-
"""Move legacy non-power signal traces from the L5 plane to signal layer L7."""

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
        if name == "VCC3V3":
            return match.group(0)

        def move_wire(wire):
            moved[0] += 1
            return wire.group(0).replace('layer="5"', 'layer="7"')

        body = re.sub(r'<wire\b[^>]*\blayer="5"[^>]*/>', move_wire, body)
        return opening + body + closing

    updated_body = re.sub(
        r'(<signal name="([^"]+)"[^>]*>)(.*?)(</signal>)', move_signal,
        signals.group(2), flags=re.S)
    if moved[0] != 957:
        raise ValueError("expected 957 non-VCC3V3 L5 wires, found %d" % moved[0])

    updated = (board[:signals.start()] + signals.group(1) + updated_body
               + signals.group(3) + board[signals.end():])
    ET.fromstring(updated)
    io.open(BRD, "w", encoding="utf-8", newline="").write(updated)
    print("moved %d non-power signal wires from L5 to L7" % moved[0])


if __name__ == "__main__":
    main()
