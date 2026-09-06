# -*- coding: utf-8 -*-
"""Route selected top/through two-terminal nets on L2 with L1-L2 microvias."""

import io
import math
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_connectivity as C
import escape as E
import finish_routes as F
import geom as G
import pathfinder as PF
import power as P


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRD = os.environ.get("MICROVIA_BOARD", os.path.join(ROOT, "zulu_a7.brd"))
APPLY = "--apply" in sys.argv
WIDTH = float(os.environ.get("MICROVIA_WIDTH", "0.0762"))
STEP = float(os.environ.get("MICROVIA_STEP", "0.05"))
VIA_DRILL = float(os.environ.get("MICROVIA_DRILL", "0.10"))
VIA_LAND = float(os.environ.get("MICROVIA_LAND", "0.20"))
TARGET_LAYER = int(os.environ.get("MICROVIA_LAYER", "2"))
KEEPOUT = tuple(float(value) for value in
                os.environ.get("MICROVIA_KEEPOUT", "").split(",") if value)


def g(value):
    text = ("%.4f" % value).rstrip("0").rstrip(".")
    return text if text not in ("", "-0") else "0"


def main():
    board = io.open(BRD, encoding="utf-8", errors="replace").read()
    parsed = C.parse_signal_objects(board)
    selected = {q.strip() for q in
                os.environ.get("MICROVIA_NETS", "").split(",") if q.strip()}
    clearance = G.rule_mm(board, "mdWireWire") + 0.005
    drill_clearance = G.drill_clearance(board, VIA_DRILL)
    keepout = []
    if KEEPOUT:
        if len(KEEPOUT) != 4:
            raise ValueError("MICROVIA_KEEPOUT must be x1,y1,x2,y2")
        x1, y1, x2, y2 = KEEPOUT
        keepout = G.as_circles([
            ((x1 + x2) / 2.0, (y1 + y2) / 2.0,
             abs(x2 - x1) / 2.0, abs(y2 - y1) / 2.0, 0.0)
        ], step=STEP)
    outline = re.findall(
        r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)"'
        r' y2="([-\d.]+)"[^>]*layer="20"', board)
    xs = [float(value) for item in outline for value in (item[0], item[2])]
    ys = [float(value) for item in outline for value in (item[1], item[3])]
    bounds = (min(xs), min(ys), max(xs), max(ys))
    existing_drills = []
    for match in re.finditer(r"<via\s([^>]*)>", board):
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', match.group(1)))
        existing_drills.append((
            float(attrs["x"]), float(attrs["y"]),
            float(attrs.get("drill", "0.2"))))

    plans = {}
    for net, (objects, terminal_count, planes) in parsed.items():
        if selected and net not in selected:
            continue
        if terminal_count < 2 or len(C.components(
                objects, terminal_count, planes)) == 1:
            continue
        terminals = P.pads_of(board, net, skip=())
        if len(terminals) < 2:
            continue
        maze = P.Maze(
            G.obstacles(board, frozenset((net,)), TARGET_LAYER, ())
            + keepout,
            bounds, clearance, WIDTH, STEP)
        router = PF.Router(
            {TARGET_LAYER: maze}, bytearray(len(maze.free)), (TARGET_LAYER,))

        def terminal_anchors(terminal):
            x, y, side = terminal
            direct = side == 0 or side == TARGET_LAYER
            first, last = sorted((side, TARGET_LAYER))
            extent = "" if direct else "%d-%d" % (first, last)
            layers = [] if direct else [
                layer for layer in (1, 2, 3, 4, 5, 6, 7, 16)
                if first <= layer <= last
            ]
            via_obstacles = [] if direct else [
                obstacle for layer in layers
                for obstacle in G.obstacles(
                    board, frozenset((net,)), layer, ())
            ]
            if TARGET_LAYER in layers:
                via_obstacles.extend(keepout)
            surface_obstacles = (
                [] if direct else
                G.obstacles(board, frozenset((net,)), side, ()))
            radius_limit = float(os.environ.get(
                "MICROVIA_ESCAPE_RADIUS", "2.0"))
            radii = [0.0] if direct else [0.0] + [
                0.20 + 0.05 * index
                for index in range(int((radius_limit - 0.20) / 0.05) + 1)
            ]
            anchors = []
            metadata = {}
            seen = set()
            for radius in radii:
                samples = 1 if radius == 0 else 96
                for sample in range(samples):
                    angle = 2.0 * math.pi * sample / samples
                    point = (
                        x + radius * math.cos(angle),
                        y + radius * math.sin(angle))
                    if not (bounds[0] <= point[0] <= bounds[2]
                            and bounds[1] <= point[1] <= bounds[3]):
                        continue
                    cell = router.cell(point)
                    if cell in seen or not maze.free[cell]:
                        continue
                    seen.add(cell)
                    snapped = router.xy(cell)
                    if direct:
                        anchors.append((0, cell))
                        metadata[cell] = (snapped, "", terminal, TARGET_LAYER)
                        continue
                    if any(E.seg_pt((x, y), snapped, (ox, oy)) <
                           obstacle_radius + clearance + WIDTH / 2.0 - 1e-9
                           for ox, oy, obstacle_radius in surface_obstacles):
                        continue
                    if any(math.hypot(snapped[0] - ox, snapped[1] - oy) <
                           VIA_LAND / 2.0 + obstacle_radius + clearance - 1e-6
                           for ox, oy, obstacle_radius in via_obstacles):
                        continue
                    if any(math.hypot(snapped[0] - ox, snapped[1] - oy) <
                           VIA_DRILL / 2.0 + drill / 2.0
                           + drill_clearance - 1e-6
                           for ox, oy, drill in existing_drills):
                        continue
                    anchors.append((0, cell))
                    metadata[cell] = (snapped, extent, terminal, side)
            return anchors, metadata

        forced_order = os.environ.get("MICROVIA_TERMINAL_ORDER", "")
        if forced_order:
            order = [int(value) for value in forced_order.split(",")]
            if sorted(order) != list(range(len(terminals))):
                raise ValueError(
                    "MICROVIA_TERMINAL_ORDER must contain every terminal index "
                    "exactly once")
            ordered = [terminals[index] for index in order]
        else:
            first, second = max(
                ((i, j) for i in range(len(terminals))
                 for j in range(i + 1, len(terminals))),
                key=lambda pair: math.hypot(
                    terminals[pair[0]][0] - terminals[pair[1]][0],
                    terminals[pair[0]][1] - terminals[pair[1]][1]))
            ordered = ([terminals[first], terminals[second]] +
                       [terminal for index, terminal in enumerate(terminals)
                        if index not in (first, second)])
        source, source_meta = terminal_anchors(ordered[0])
        destination, destination_meta = terminal_anchors(ordered[1])
        if not source or not destination:
            print("  **** %-16s no legal L%d blind-via escape"
                  % (net, TARGET_LAYER))
            continue
        path = router.route(source, destination, 0.0,
                            (0, 0, router.W - 1, router.H - 1))
        if not path:
            print("  **** %-16s no L%d path" % (net, TARGET_LAYER))
            continue
        wires, _vias = F.collapse(path, router)
        microvias = []

        def connect_terminal(node, metadata):
            point, extent, terminal, side = metadata[node % router.NN]
            if extent:
                microvias.append((point[0], point[1], extent, ()))
                if math.hypot(
                        point[0] - terminal[0],
                        point[1] - terminal[1]) > 1e-9:
                    wires.append((terminal[:2], point, side))
            elif math.hypot(
                    point[0] - terminal[0],
                    point[1] - terminal[1]) > 1e-9:
                wires.append((terminal[:2], point, TARGET_LAYER))
        connect_terminal(path[0], source_meta)
        connect_terminal(path[-1], destination_meta)

        tree = [(0, node % router.NN) for node in path]
        complete = True
        for branch_index, terminal in enumerate(ordered[2:], start=2):
            anchors, metadata = terminal_anchors(terminal)
            if not anchors:
                print("  ---- %-16s terminal %d %r has no legal L%d anchor"
                      % (net, branch_index, terminal, TARGET_LAYER))
                complete = False
                break
            branch = router.route(
                anchors, tree, 0.0,
                (0, 0, router.W - 1, router.H - 1))
            if not branch:
                print("  ---- %-16s terminal %d %r cannot reach L%d tree"
                      % (net, branch_index, terminal, TARGET_LAYER))
                complete = False
                break
            branch_wires, _branch_vias = F.collapse(branch, router)
            wires.extend(branch_wires)
            connect_terminal(branch[0], metadata)
            tree.extend((0, node % router.NN) for node in branch[1:])
        if not complete:
            print("  **** %-16s L%d tree did not reach every terminal"
                  % (net, TARGET_LAYER))
            continue
        plans[net] = (wires, microvias)
        print("  PASS  %-16s %d wire(s), %d blind via(s)"
              % (net, len(wires), len(microvias)))

    if not APPLY:
        print("%d microvia route(s) planned" % len(plans))
        return 0 if plans else 1

    updated = board
    for net, (wires, microvias) in plans.items():
        additions = [
            '<via x="%s" y="%s" extent="%s" drill="%s" diameter="%s"/>'
            % (g(x), g(y), extent, g(VIA_DRILL), g(VIA_LAND))
            for x, y, extent, _layers in microvias
        ]
        additions.extend(
            '<wire x1="%s" y1="%s" x2="%s" y2="%s" width="%s" layer="%s"/>'
            % (g(a[0]), g(a[1]), g(end[0]), g(end[1]), g(WIDTH),
               layer)
            for a, end, layer in wires)
        match = re.search(r'(<signal name="%s"[^>]*>)' % re.escape(net), updated)
        updated = updated[:match.end()] + "".join(additions) + updated[match.end():]
    updated = re.sub(
        r'(<param name="msDrill" value=")[^"]+(")',
        r'\g<1>%smm\2' % g(VIA_DRILL), updated, count=1)
    ET.fromstring(updated)
    io.open(BRD, "w", encoding="utf-8", newline="").write(updated)
    print("wrote %d microvia route(s)" % len(plans))
    return 0


if __name__ == "__main__":
    sys.exit(main())
