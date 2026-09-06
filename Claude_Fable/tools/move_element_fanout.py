#!/usr/bin/env python3
"""Move an element and retarget copper nodes attached at its pad centers."""

import argparse
import math
import re
from pathlib import Path


SIGNAL_RE = re.compile(
    r'(<signal name="(?P<name>[^"]+)"[^>]*>)(?P<body>.*?)(</signal>)',
    re.DOTALL,
)
ROUTE_RE = re.compile(r'<(?:wire|via)\b[^>]*(?:/>|>.*?</via>)', re.DOTALL)


def number(value):
    return ("%.4f" % value).rstrip("0").rstrip(".")


def attr(text, name):
    match = re.search(r'\b%s="([^"]+)"' % re.escape(name), text)
    return match.group(1) if match else None


def replace_attr(text, name, value):
    return re.sub(
        r'(\b%s=")[^"]+(")' % re.escape(name),
        lambda match: match.group(1) + number(value) + match.group(2),
        text,
        count=1,
    )


def rotate(x, y, rotation):
    mirrored = rotation.startswith("M")
    rotation = rotation.lstrip("M")
    x, y = {
        "R0": (x, y),
        "R90": (-y, x),
        "R180": (-x, -y),
        "R270": (y, -x),
    }[rotation]
    return (-x, y) if mirrored else (x, y)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board", type=Path)
    parser.add_argument("element")
    parser.add_argument("dx", type=float)
    parser.add_argument("dy", type=float)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    board = args.board.read_text(encoding="utf-8")
    element_re = re.compile(
        r'<element name="%s" library="([^"]+)" package="([^"]+)"'
        r'(?P<attrs>[^>]*)>' % re.escape(args.element)
    )
    element = element_re.search(board)
    if not element:
        parser.error("element %s not found" % args.element)

    library, package = element.group(1), element.group(2)
    attrs = element.group("attrs")
    old_x, old_y = float(attr(attrs, "x")), float(attr(attrs, "y"))
    rotation = attr(attrs, "rot") or "R0"
    new_x, new_y = old_x + args.dx, old_y + args.dy

    library_match = re.search(
        r'<library name="%s">(.*?)</library>' % re.escape(library),
        board,
        re.DOTALL,
    )
    package_match = re.search(
        r'<package name="%s"[^>]*>(.*?)</package>' % re.escape(package),
        library_match.group(1),
        re.DOTALL,
    )
    if not package_match:
        parser.error("package %s/%s not found" % (library, package))
    pads = {}
    for pad in re.finditer(r'<(?:smd|pad)\b([^>]*)>', package_match.group(1)):
        pad_attrs = pad.group(1)
        name = attr(pad_attrs, "name")
        px, py = float(attr(pad_attrs, "x")), float(attr(pad_attrs, "y"))
        rx, ry = rotate(px, py, rotation)
        pads[name] = ((old_x + rx, old_y + ry), (new_x + rx, new_y + ry))

    signal_pads = {}
    for signal in SIGNAL_RE.finditer(board):
        for contact in re.finditer(
            r'<contactref element="%s" pad="([^"]+)"/>' % re.escape(args.element),
            signal.group("body"),
        ):
            signal_pads.setdefault(signal.group("name"), []).append(
                pads[contact.group(1)]
            )

    moved_nodes = 0

    def replace_signal(signal):
        nonlocal moved_nodes
        mappings = signal_pads.get(signal.group("name"), ())
        if not mappings:
            return signal.group(0)

        def replace_route(route):
            nonlocal moved_nodes
            text = route.group(0)
            coordinate_pairs = (
                (("x1", "y1"), ("x2", "y2"))
                if text.startswith("<wire")
                else ((("x", "y"),))
            )
            for names in coordinate_pairs:
                x_text, y_text = attr(text, names[0]), attr(text, names[1])
                if x_text is None or y_text is None:
                    continue
                point = (float(x_text), float(y_text))
                for old, new in mappings:
                    if math.hypot(point[0] - old[0], point[1] - old[1]) <= 0.02:
                        text = replace_attr(text, names[0], new[0])
                        text = replace_attr(text, names[1], new[1])
                        moved_nodes += 1
                        break
            return text

        body = ROUTE_RE.sub(replace_route, signal.group("body"))
        return signal.group(1) + body + signal.group(4)

    updated = SIGNAL_RE.sub(replace_signal, board)

    def replace_element(match):
        text = match.group(0)
        text = replace_attr(text, "x", new_x)
        return replace_attr(text, "y", new_y)

    updated = element_re.sub(replace_element, updated, count=1)
    output = args.output or args.board
    output.write_text(updated, encoding="utf-8")
    print(
        "Moved %s from (%.4f, %.4f) to (%.4f, %.4f); retargeted %d copper nodes."
        % (args.element, old_x, old_y, new_x, new_y, moved_nodes)
    )


if __name__ == "__main__":
    main()
