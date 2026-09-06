# -*- coding: utf-8 -*-
"""Remove redundant AIN16 branches and complete retained layer transitions."""

import io
import math
import os
import re
import xml.etree.ElementTree as ET


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRD = os.path.join(ROOT, "zulu_a7.brd")
NETS = ("AIN16_N", "AIN16_P")


def update_signal(match):
    opening, name, body, closing = match.groups()
    if name not in NETS:
        return match.group(0)

    if name == "AIN16_N":
        marker = '<wire x1="47.1" y1="7.89"'
        if marker not in body:
            raise ValueError("AIN16_N third-terminal branch marker not found")
        prefix, suffix = body.split(marker, 1)
        prefix, removed = re.subn(
            r'<wire\b[^>]*width="0\.0762"[^>]*/>\s*', "", prefix)
        prefix += (
            '<wire x1="42.5" y1="12.74" x2="42.5" y2="12.5" '
            'width="0.0762" layer="1"/>')
        body = prefix + marker + suffix
    else:
        removed = 0
    print("%-8s removed %d redundant segment(s)" % (name, removed))
    return opening + body + closing


def routed_length(board, net):
    body = re.search(
        r'<signal name="%s"[^>]*>(.*?)</signal>' % net, board, re.S).group(1)
    total = 0.0
    for match in re.finditer(
            r'<wire x1="([-\d.]+)" y1="([-\d.]+)" '
            r'x2="([-\d.]+)" y2="([-\d.]+)"[^>]*layer="(?:1|3|4|6|7|16)"',
            body):
        x1, y1, x2, y2 = map(float, match.groups())
        total += math.hypot(x2 - x1, y2 - y1)
    return total


def main():
    board = io.open(BRD, encoding="utf-8", errors="replace").read()
    updated = re.sub(
        r'(<signal name="([^"]+)"[^>]*>)(.*?)(</signal>)',
        update_signal, board, flags=re.S)
    ET.fromstring(updated)
    io.open(BRD, "w", encoding="utf-8", newline="").write(updated)
    negative = routed_length(updated, "AIN16_N")
    positive = routed_length(updated, "AIN16_P")
    print("AIN16_N %.4f mm, AIN16_P %.4f mm, mismatch %.4f mm"
          % (negative, positive, abs(negative - positive)))


if __name__ == "__main__":
    main()
