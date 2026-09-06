# -*- coding: utf-8 -*-
"""Move U3 left and remove obsolete SDRAM-bus copper for a clean reroute."""

import io
import os
import re
import sys
import xml.etree.ElementTree as ET


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRD = os.path.join(ROOT, "zulu_a7.brd")
NEW_X = float(os.environ.get("SDRAM_X", "28.775"))
SDRAM = re.compile(r"^(D\d+|A\d+|BS\d|RAS#|CAS#|WE#|CKE|LDQM|UDQM|SDRAM-)")


def g(value):
    return ("%.4f" % value).rstrip("0").rstrip(".")


def main():
    board = io.open(BRD, encoding="utf-8", errors="replace").read()
    board, moved = re.subn(
        r'(<element name="U3"[^>]*? x=")[-\d.]+(")',
        lambda match: match.group(1) + g(NEW_X) + match.group(2),
        board, count=1)
    if moved != 1:
        print("expected one U3 element, moved %d" % moved)
        return 1

    stripped = []

    def clean_signal(match):
        name, attrs, body = match.group(1), match.group(2), match.group(3)
        if not SDRAM.match(name):
            return match.group(0)
        body = re.sub(r"<via\b[^>]*(?:/>|>.*?</via>)", "", body, flags=re.S)
        body = re.sub(
            r'<wire\b[^>]*\blayer="(?:1|2|3|4|5|16|19)"[^>]*/>', "", body)
        stripped.append(name)
        return '<signal name="%s"%s>%s</signal>' % (name, attrs, body)

    board = re.sub(
        r'<signal name="([^"]+)"([^>]*)>(.*?)</signal>',
        clean_signal, board, flags=re.S)
    ET.fromstring(board)
    io.open(BRD, "w", encoding="utf-8", newline="").write(board)
    print("moved U3 to x=%s and stripped %d SDRAM signal(s)" %
          (g(NEW_X), len(stripped)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
