#!/usr/bin/env python3
"""Extend the board to 2.750 inches without moving the breadboard pin field."""

import argparse
import re
import xml.etree.ElementTree as ET
from pathlib import Path


OLD_X = "60.96"
NEW_X = "69.85"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    board = args.board.read_text(encoding="utf-8")
    replacements = (
        (r'<wire x1="0" y1="0" x2="60\.96" y2="0" width="0" layer="20"/>',
         '<wire x1="0" y1="0" x2="69.85" y2="0" width="0" layer="20"/>'),
        (r'<wire x1="60\.96" y1="0" x2="60\.96" y2="25\.4" width="0" layer="20"/>',
         '<wire x1="69.85" y1="0" x2="69.85" y2="25.4" width="0" layer="20"/>'),
        (r'<wire x1="60\.96" y1="25\.4" x2="0" y2="25\.4" width="0" layer="20"/>',
         '<wire x1="69.85" y1="25.4" x2="0" y2="25.4" width="0" layer="20"/>'),
        (r'<wire x1="0" y1="0" x2="60\.96" y2="0" width="0\.1524" layer="21"/>',
         '<wire x1="0" y1="0" x2="69.85" y2="0" width="0.1524" layer="21"/>'),
        (r'<wire x1="60\.96" y1="0" x2="60\.96" y2="25\.4" width="0\.1524" layer="21"/>',
         '<wire x1="69.85" y1="0" x2="69.85" y2="25.4" width="0.1524" layer="21"/>'),
        (r'<wire x1="60\.96" y1="25\.4" x2="0" y2="25\.4" width="0\.1524" layer="21"/>',
         '<wire x1="69.85" y1="25.4" x2="0" y2="25.4" width="0.1524" layer="21"/>'),
    )
    for pattern, replacement in replacements:
        board, count = re.subn(pattern, replacement, board, count=1)
        if count != 1:
            parser.error("expected one outline match for %s" % pattern)

    board = board.replace(
        "1.000 x 2.400 in", "1.000 x 2.750 in", 1)
    board = board.replace(
        "Board 25.40 x 60.96 mm.", "Board 25.40 x 69.85 mm.", 1)
    ET.fromstring(board)
    output = args.output or args.board
    output.write_text(board, encoding="utf-8")
    print("extended board outline from %s to %s mm" % (OLD_X, NEW_X))


if __name__ == "__main__":
    main()
