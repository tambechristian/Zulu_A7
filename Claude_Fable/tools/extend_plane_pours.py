#!/usr/bin/env python3
"""Extend full-board copper-pour outlines into the 2.750-inch connector strip."""

import argparse
import re
import xml.etree.ElementTree as ET
from pathlib import Path


OLD_RIGHT = "60.6362"
NEW_RIGHT = "69.5262"
PLANE_LAYERS = {"1", "2", "5", "16"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--clear-fill-cache",
        action="store_true",
        help="remove cached polygon fill geometry so Fusion rebuilds it",
    )
    args = parser.parse_args()

    board = args.board.read_text(encoding="utf-8")
    changed = []

    def extend(match):
        attrs, body = match.group(1), match.group(2)
        layer_match = re.search(r'\blayer="(\d+)"', attrs)
        if not layer_match or layer_match.group(1) not in PLANE_LAYERS:
            return match.group(0)
        outline_end = body.find("</polygonoutlineobjects>")
        if outline_end < 0:
            parser.error("layer %s polygon has no outline" % layer_match.group(1))
        outline = body[:outline_end]
        updated_outline, count = re.subn(
            r'(\bx=")(?:%s|%s)(")' % (
                re.escape(OLD_RIGHT), re.escape(NEW_RIGHT)),
            r"\g<1>%s\2" % NEW_RIGHT,
            outline,
        )
        if count != 2:
            parser.error(
                "expected two right-edge vertices on layer %s, found %d"
                % (layer_match.group(1), count))
        changed.append(layer_match.group(1))
        body = updated_outline + body[outline_end:]
        if args.clear_fill_cache:
            body, fill_count = re.subn(
                r"<polygonfilldetails>.*?</polygonfilldetails>",
                "",
                body,
                count=1,
                flags=re.DOTALL,
            )
            if fill_count != 1:
                parser.error(
                    "expected one fill cache on layer %s, found %d"
                    % (layer_match.group(1), fill_count))
        return "<polygonpour%s>%s</polygonpour>" % (attrs, body)

    updated = re.sub(
        r"<polygonpour\b([^>]*)>(.*?)</polygonpour>",
        extend,
        board,
        flags=re.DOTALL,
    )
    missing = PLANE_LAYERS - set(changed)
    if missing:
        parser.error("missing full-board pours on layers %s" %
                     ", ".join(sorted(missing)))
    ET.fromstring(updated)
    output = args.output or args.board
    output.write_text(updated, encoding="utf-8")
    print(
        "extended plane pours on layers %s from x=%s to x=%s"
        % (", ".join(sorted(changed, key=int)), OLD_RIGHT, NEW_RIGHT)
    )


if __name__ == "__main__":
    main()
