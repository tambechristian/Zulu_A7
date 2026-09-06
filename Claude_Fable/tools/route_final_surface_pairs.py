# -*- coding: utf-8 -*-
"""Connect the final Ratsnest islands with plane stubs and one signal route."""

import io
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geom as G
import pathfinder as PF
import power as P


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRD = os.path.join(ROOT, "zulu_a7.brd")
STEP = 0.05

PAIRS = (
    ("VCC3V3", 1, (29.819, 6.308), (29.7, 6.65), 0.10),
    ("VCC3V3", 1, (23.175, 4.65), (23.2, 4.65), 0.10),
    ("VCC3V3", 1, (25.023, 3.9975), (25.0, 3.0), 0.10),
    ("VCC3V3", 16, (41.384, 3.065), (41.4, 3.1), 0.15),
    ("VCC3V3", 16, (44.732, 3.065), (44.75, 3.1), 0.15),
    ("MODE_NET", 16, (13.9, 6.69), (14.15, 6.8), 0.0762),
    ("MODE_NET", 16, (3.823, 2.828), (3.8, 2.85), 0.0762),
    ("MODE_NET", 6, (14.15, 6.8), (3.8, 2.85), 0.0762),
)

# These pads are boxed in on their component surfaces. Blind vias terminate
# directly on the dedicated L5 VCC3V3 plane without disturbing the opposite
# surface, where several unrelated pads overlap their projected coordinates.
PLANE_VIAS = (
    ("VCC3V3", "1-5", (24.673, 2.758)),
    ("GND", "1-2", (24.075, 2.758)),
    ("VCC3V3", "1-5", (29.7, 6.65)),
    ("VCC3V3", "1-5", (23.2, 4.65)),
    ("VCC3V3", "1-5", (25.0, 3.0)),
    ("VCC3V3", "5-16", (41.4, 3.1)),
    ("VCC3V3", "5-16", (44.75, 3.1)),
    ("MODE_NET", "6-16", (14.15, 6.8)),
    ("MODE_NET", "6-16", (3.8, 2.85)),
)


def g(value):
    text = ("%.4f" % value).rstrip("0").rstrip(".")
    return text if text not in ("", "-0") else "0"


def collapse(points):
    if len(points) < 2:
        return []
    result = []
    start = points[0]
    previous = start
    direction = None
    for point in points[1:]:
        new_direction = (
            0 if abs(point[0] - previous[0]) < 1e-9 else
            1 if abs(point[1] - previous[1]) < 1e-9 else 2
        )
        if direction is not None and new_direction != direction:
            result.append((start, previous))
            start = previous
        direction = new_direction
        previous = point
    result.append((start, previous))
    return [segment for segment in result if segment[0] != segment[1]]


def bounds(board):
    outline = re.findall(
        r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" '
        r'y2="([-\d.]+)"[^>]*layer="20"', board)
    xs = [float(value) for row in outline for value in (row[0], row[2])]
    ys = [float(value) for row in outline for value in (row[1], row[3])]
    return min(xs), min(ys), max(xs), max(ys)


def route_pair(board, net, layer, start, finish, width):
    bx = bounds(board)
    clearance = G.rule_mm(board, "mdWireWire") + 0.005
    maze = P.Maze(
        G.obstacles(board, frozenset((net,)), layer, ()),
        bx, clearance, width, STEP)
    router = PF.Router({layer: maze}, bytearray(len(maze.free)), (layer,))
    source = router.cell(start)
    destination = router.cell(finish)
    router.free[0][source] = 1
    router.free[0][destination] = 1
    path = router.route(
        [(0, source)], [(0, destination)], 0.0,
        (0, 0, router.W - 1, router.H - 1))
    if not path:
        raise ValueError("%s has no legal L%d surface path" % (net, layer))
    points = [router.xy(node % router.NN) for node in path]
    points[0] = start
    points[-1] = finish
    return collapse(points)


def add_segments(board, net, layer, width, segments):
    additions = "".join(
        '<wire x1="%s" y1="%s" x2="%s" y2="%s" width="%s" layer="%d"/>'
        % (g(a[0]), g(a[1]), g(b[0]), g(b[1]), g(width), layer)
        for a, b in segments)
    match = re.search(r'(<signal name="%s"[^>]*>)' % re.escape(net), board)
    if not match:
        raise ValueError("signal not found: %s" % net)
    return board[:match.end()] + additions + board[match.end():]


def add_via(board, net, extent, point):
    addition = (
        '<via x="%s" y="%s" extent="%s" drill="0.2" diameter="0.3"/>'
        % (g(point[0]), g(point[1]), extent))
    match = re.search(r'(<signal name="%s"[^>]*>)' % re.escape(net), board)
    if not match:
        raise ValueError("signal not found: %s" % net)
    return board[:match.end()] + addition + board[match.end():]


def relocate_c135(board):
    board = re.sub(
        r'(<element name="C135"[^>]*\sx=")[^"]+(" y=")[^"]+(")',
        r'\g<1>24.373\g<2>2.758\g<3>', board, count=1)
    dead = (
        '<wire x1="27.8892" y1="6.3246" x2="27.923" y2="6.308" '
        'width="0.0762" layer="1"/>',
        '<wire x1="27.3558" y1="6.2865" x2="27.323" y2="6.308" '
        'width="0.0762" layer="1"/>',
        '<wire x1="26.5938" y1="5.5245" x2="27.3558" y2="6.2865" '
        'width="0.0762" layer="1"/>',
        '<wire x1="26.5938" y1="5.3721" x2="26.5938" y2="5.5245" '
        'width="0.0762" layer="1"/>',
        '<wire x1="26.5938" y1="5.3721" x2="26.608" y2="5.358" '
        'width="0.0762" layer="1"/>',
    )
    for wire in dead:
        if wire not in board:
            raise ValueError("C135 branch changed before relocation")
        board = board.replace(wire, "", 1)
    return board


def main():
    board = relocate_c135(
        io.open(BRD, encoding="utf-8", errors="replace").read())
    print("C135       moved to 24.3730, 2.7580")
    total = 0
    missed = []
    for net, layer, start, finish, width in PAIRS:
        try:
            segments = route_pair(board, net, layer, start, finish, width)
        except ValueError as error:
            print("MISS      %s" % error)
            missed.append(net)
            continue
        board = add_segments(board, net, layer, width, segments)
        total += len(segments)
        print("%-10s L%-2d %2d segment(s)" % (net, layer, len(segments)))
    if not total:
        raise ValueError("none of the final surface pairs has a legal path")
    for net, extent, point in PLANE_VIAS:
        board = add_via(board, net, extent, point)
        print("%-10s %-4s blind via at %.4f, %.4f"
              % (net, extent, point[0], point[1]))
    ET.fromstring(board)
    io.open(BRD, "w", encoding="utf-8", newline="").write(board)
    print("wrote %d final surface segment(s); missed %d pair(s)"
          % (total, len(missed)))


if __name__ == "__main__":
    main()
