# -*- coding: utf-8 -*-
"""Finish untouched nets on a partially routed Fusion/EAGLE board.

    python tools/finish_routes.py
    python tools/finish_routes.py --apply

Unlike signals.py's normal fan-out model, this router may leave an SMD pad on
its own surface before changing layers. That is needed when existing copper
leaves room for a trace at the pad but not for an immediate through-via.
"""

import io
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import escape as E
import geom as G
import pathfinder as PF
import power as P
import check_connectivity as C


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRD = os.environ.get("FINISH_BOARD", os.path.join(ROOT, "zulu_a7.brd"))
APPLY = "--apply" in sys.argv
LAYERS = [int(layer) for layer in
          os.environ.get("FINISH_LAYERS", "1,3,4,6,7,16").split(",")]
WIDTH = float(os.environ.get("FINISH_WIDTH", "0.10"))
STEP = float(os.environ.get("FINISH_STEP", "0.05"))
VIA_D = float(os.environ.get("FINISH_VIA_DRILL", "0.20"))
VIA_L = float(os.environ.get("FINISH_VIA_LAND", "0.30"))
VIA_EXTENT = os.environ.get("FINISH_VIA_EXTENT", "1-16")
VIA_SCOPE = tuple(int(layer) for layer in
                  os.environ.get("FINISH_VIA_SCOPE", "").split(",") if layer)
PAD_VIA_KEEPOUT = float(os.environ.get("PAD_VIA_KEEPOUT", "0.45"))
ALLOW_MULTI = os.environ.get("FINISH_MULTI", "").lower() in ("1", "true", "yes")
ALLOW_VIA_IN_PAD = os.environ.get(
    "FINISH_VIA_IN_PAD", "").lower() in ("1", "true", "yes")
EXCLUDED = {q.strip() for q in
            os.environ.get("FINISH_EXCLUDE", "GND,VCC3V3").split(",")
            if q.strip()}


def g(v):
    s = ("%.4f" % v).rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


def incomplete_two_terminal(b):
    parsed = C.parse_signal_objects(b)
    selected = {q.strip() for q in os.environ.get("FINISH_NETS", "").split(",")
                if q.strip()}
    out = []
    for net, (objects, terminals, planes) in parsed.items():
        if selected and net not in selected:
            continue
        if net in EXCLUDED:
            continue
        if terminals < 2 or (terminals != 2 and not ALLOW_MULTI):
            continue
        if len(C.components(objects, terminals, planes)) > 1:
            out.append(net)
    return out


def collapse(nodes, router):
    """Convert graph nodes to maximal collinear wire segments and layer changes."""
    points = []
    for n in nodes:
        li, cell = divmod(n, router.NN)
        points.append((router.layers[li], router.xy(cell)))

    wires = []
    vias = []
    run = [points[0]]
    for point in points[1:]:
        if point[0] != run[-1][0]:
            if len(run) > 1:
                wires.extend(collapse_run(run))
            vias.append(run[-1][1])
            run = [point]
        else:
            run.append(point)
    if len(run) > 1:
        wires.extend(collapse_run(run))
    return wires, vias


def collapse_run(run):
    out = []
    start = run[0][1]
    prev = start
    direction = None
    layer = run[0][0]
    for _lay, point in run[1:]:
        new_direction = (
            0 if abs(point[0] - prev[0]) < 1e-9 else
            1 if abs(point[1] - prev[1]) < 1e-9 else 2
        )
        if direction is not None and new_direction != direction:
            out.append((start, prev, layer))
            start = prev
        direction = new_direction
        prev = point
    if math.hypot(prev[0] - start[0], prev[1] - start[1]) > 1e-9:
        out.append((start, prev, layer))
    return out


def terminal_nodes(router, terminals, obstacles=None, clearance=0.0,
                   width=WIDTH):
    out = []
    actual = {}
    for x, y, side in terminals:
        allowed = LAYERS if side == 0 else [16 if side == 16 else 1]
        cell = router.cell((x, y))
        for layer in allowed:
            li = LAYERS.index(layer)
            node = li * router.NN + cell
            out.append((li, cell))
            actual[node] = (x, y)
            if obstacles is None:
                continue
            seen = {cell}
            max_radius = float(os.environ.get("FINISH_ESCAPE_RADIUS", "2.0"))
            radii = [0.25 + 0.05 * index
                     for index in range(int((max_radius - 0.25) / 0.05) + 1)]
            for radius in radii:
                for sample in range(96):
                    angle = 2.0 * math.pi * sample / 96.0
                    point = (x + radius * math.cos(angle),
                             y + radius * math.sin(angle))
                    if not (router.bx[0] <= point[0] <= router.bx[2] and
                            router.bx[1] <= point[1] <= router.bx[3]):
                        continue
                    maze = router.mz[router.layers[0]]
                    ci, cj = maze.i(point[0]), maze.j(point[1])
                    if not (0 <= ci < router.W and 0 <= cj < router.H):
                        continue
                    candidate = cj * router.W + ci
                    if candidate in seen or not router.free[li][candidate]:
                        continue
                    seen.add(candidate)
                    snapped = router.xy(candidate)
                    if any(E.seg_pt((x, y), snapped, (ox, oy)) <
                           obstacle_radius + clearance + width / 2.0 - 1e-9
                           for ox, oy, obstacle_radius in obstacles[layer]):
                        continue
                    candidate_node = li * router.NN + candidate
                    out.append((li, candidate))
                    actual[candidate_node] = (x, y)
    return out, actual


def block_via_sites(router, vias, center_spacing):
    radius_cells = int(math.ceil(center_spacing / router.step))
    for x, y in vias:
        center = router.cell((x, y))
        ci, cj = center % router.W, center // router.W
        for dj in range(-radius_cells, radius_cells + 1):
            for di in range(-radius_cells, radius_cells + 1):
                i, j = ci + di, cj + dj
                if not (0 <= i < router.W and 0 <= j < router.H):
                    continue
                qx, qy = router.xy(j * router.W + i)
                if math.hypot(qx - x, qy - y) < center_spacing - 1e-6:
                    router.vfree[j * router.W + i] = 0
        # The existing hole itself is reusable as a layer change; collapse()
        # may emit it again, but final via de-duplication removes that duplicate.
        router.vfree[center] = 1


def main():
    b = io.open(BRD, encoding="utf-8", errors="replace").read()
    clr = G.rule_mm(b, "mdWireWire")
    plan_clr = clr + 0.005
    drill_clr = G.drill_clearance(b, VIA_DRILL)
    parsed = C.parse_signal_objects(b)
    outline = re.findall(
        r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)"'
        r' width="[\d.]+" layer="20"/>', b)
    xs = [float(v) for q in outline for v in (q[0], q[2])]
    ys = [float(v) for q in outline for v in (q[1], q[3])]
    bx = (min(xs), min(ys), max(xs), max(ys))

    plans = {}
    for net in incomplete_two_terminal(b):
        terminals = P.pads_of(b, net, skip=())
        if len(terminals) > 2:
            forced_order = os.environ.get("FINISH_TERMINAL_ORDER", "")
            if forced_order:
                order = [int(value) for value in forced_order.split(",")]
                if sorted(order) != list(range(len(terminals))):
                    raise ValueError(
                        "FINISH_TERMINAL_ORDER must contain every terminal index "
                        "exactly once")
                terminals = [terminals[index] for index in order]
            else:
                forced_pair = os.environ.get("FINISH_BASE_PAIR", "")
                if forced_pair:
                    first, second = (
                        int(value) for value in forced_pair.split(","))
                else:
                    first, second = max(
                        ((i, j) for i in range(len(terminals))
                         for j in range(i + 1, len(terminals))),
                        key=lambda pair: math.hypot(
                            terminals[pair[0]][0] - terminals[pair[1]][0],
                            terminals[pair[0]][1] - terminals[pair[1]][1]))
                terminals = ([terminals[first], terminals[second]] +
                             [terminal for i, terminal in enumerate(terminals)
                              if i not in (first, second)])
        mazes = dict((layer, P.Maze(
            G.obstacles(b, frozenset((net,)), layer, ()),
            bx, plan_clr, WIDTH, STEP)) for layer in LAYERS)
        via_clearance = max(plan_clr, drill_clr - (VIA_L - VIA_D))
        if VIA_SCOPE:
            via_obstacles = []
            for layer in VIA_SCOPE:
                via_obstacles.extend(
                    G.obstacles(b, frozenset((net,)), layer, ()))
        else:
            via_obstacles = G.obstacles(
                b, frozenset((net,)), None, ())
        via_maze = P.Maze(
            via_obstacles, bx, via_clearance, VIA_L, STEP)
        router = PF.Router(mazes, bytearray(via_maze.free), LAYERS)
        terminal_obstacles = {
            layer: G.obstacles(b, frozenset((net,)), layer, ())
            for layer in LAYERS
        }
        existing_vias = [obj["at"] for obj in parsed[net][0]
                         if obj["kind"] == "via"]
        block_via_sites(router, existing_vias, VIA_D + drill_clr)

        # Rasterization can mark a valid pad blocked by nearby foreign copper.
        # Open the cells physically inside this net's pad; the geometric
        # validator still checks every segment after it exits the pad.
        for pad in parsed[net][0][:parsed[net][1]]:
            px, py = pad["at"]
            maze = router.mz[LAYERS[0]]
            i0, i1 = sorted((maze.i(px - pad["hx"]),
                             maze.i(px + pad["hx"])))
            j0, j1 = sorted((maze.j(py - pad["hy"]),
                             maze.j(py + pad["hy"])))
            for j in range(j0, j1 + 1):
                for i in range(i0, i1 + 1):
                    qx, qy = router.xy(j * router.W + i)
                    if (abs(qx - px) <= pad["hx"] + 1e-6 and
                            abs(qy - py) <= pad["hy"] + 1e-6):
                        for layer in pad["layers"]:
                            if layer in LAYERS:
                                router.free[LAYERS.index(layer)][
                                    j * router.W + i] = 1

        # Do not create via-in-pad. Through-hole pads remain valid layer
        # changes, while SMD keepout follows the actual pad outline.
        for pad in parsed[net][0][:parsed[net][1]]:
            if pad["through"] or ALLOW_VIA_IN_PAD:
                continue
            px, py = pad["at"]
            margin = VIA_L / 2.0
            maze = router.mz[LAYERS[0]]
            i0, i1 = sorted((maze.i(px - pad["hx"] - margin),
                             maze.i(px + pad["hx"] + margin)))
            j0, j1 = sorted((maze.j(py - pad["hy"] - margin),
                             maze.j(py + pad["hy"] + margin)))
            for j in range(j0, j1 + 1):
                for i in range(i0, i1 + 1):
                    cell = j * router.W + i
                    qx, qy = router.xy(cell)
                    if G.rect_pt((px, py, pad["hx"], pad["hy"]),
                                 qx, qy) < margin:
                        router.vfree[cell] = 0

        first, first_actual = terminal_nodes(
            router, terminals[:1], terminal_obstacles, clr, WIDTH)
        second, second_actual = terminal_nodes(
            router, terminals[1:2], terminal_obstacles, clr, WIDTH)
        if os.environ.get("FINISH_DEBUG_TERMINALS", "0") == "1":
            print("  ---- %-16s source seeds=%d destination seeds=%d" %
                  (net, len(first), len(second)))
        full_box = (0, 0, router.W - 1, router.H - 1)
        path = router.route(first, second, 0.0, full_box)
        if not path:
            print("  **** %-16s no stacked-layer path" % net)
            continue

        wires, vias = collapse(path, router)
        block_via_sites(router, vias, VIA_D + drill_clr)
        actual = dict(first_actual)
        actual.update(second_actual)
        if path[0] in actual:
            layer_index, cell = divmod(path[0], router.NN)
            snapped = router.xy(cell)
            if math.hypot(
                    actual[path[0]][0] - snapped[0],
                    actual[path[0]][1] - snapped[1]) > 1e-9:
                wires.insert(
                    0, (actual[path[0]], snapped, LAYERS[layer_index]))
        if path[-1] in actual:
            layer_index, cell = divmod(path[-1], router.NN)
            snapped = router.xy(cell)
            if math.hypot(
                    actual[path[-1]][0] - snapped[0],
                    actual[path[-1]][1] - snapped[1]) > 1e-9:
                wires.append(
                    (snapped, actual[path[-1]], LAYERS[layer_index]))
        interior = path[1:-1]
        tree = [(n // router.NN, n % router.NN) for n in
                (interior if interior else path)]

        complete = True
        for terminal in terminals[2:]:
            src, src_actual = terminal_nodes(
                router, [terminal], terminal_obstacles, clr, WIDTH)
            path2 = router.route(src, tree, 0.0, full_box)
            if not path2:
                complete = False
                break
            w2, v2 = collapse(path2, router)
            if path2[0] in src_actual:
                layer_index, cell = divmod(path2[0], router.NN)
                snapped = router.xy(cell)
                if math.hypot(
                        src_actual[path2[0]][0] - snapped[0],
                        src_actual[path2[0]][1] - snapped[1]) > 1e-9:
                    w2.insert(
                        0, (src_actual[path2[0]], snapped,
                            LAYERS[layer_index]))
            wires.extend(w2)
            vias.extend(v2)
            block_via_sites(router, v2, VIA_D + drill_clr)
            tree.extend((n // router.NN, n % router.NN) for n in path2[1:])
        if not complete:
            print("  **** %-16s tree did not reach every terminal" % net)
            continue

        through = [(x, y) for x, y, side in terminals if side == 0]
        vias = [v for v in vias
                if not any(math.hypot(v[0] - q[0], v[1] - q[1]) < STEP
                           for q in through)
                and not any(math.hypot(v[0] - q[0], v[1] - q[1]) < STEP
                            for q in existing_vias)]
        plans[net] = (wires, sorted(set((round(x, 4), round(y, 4))
                                        for x, y in vias)))
        print("  PASS  %-16s %d wire(s), %d via(s)"
              % (net, len(wires), len(plans[net][1])))

    remaining = incomplete_two_terminal(b)
    print("\n%d of %d split two-terminal net(s) planned"
          % (len(plans), len(remaining)))
    if not APPLY:
        print("report only -- re-run with --apply to write the routes")
        return 0 if len(plans) == len(remaining) else 1

    out = b
    for net, (wires, vias) in plans.items():
        add = []
        for x, y in vias:
            add.append('<via x="%s" y="%s" extent="%s" drill="%s" diameter="%s"/>'
                       % (g(x), g(y), VIA_EXTENT, g(VIA_D), g(VIA_L)))
        for a, c, layer in wires:
            add.append('<wire x1="%s" y1="%s" x2="%s" y2="%s" width="%s" layer="%s"/>'
                       % (g(a[0]), g(a[1]), g(c[0]), g(c[1]), g(WIDTH), layer))
        m = re.search(r'(<signal name="%s"[^>]*>)' % re.escape(net), out)
        out = out[:m.end()] + "".join(add) + out[m.end():]

    import xml.etree.ElementTree as ET
    ET.fromstring(out)
    io.open(BRD, "w", encoding="utf-8", newline="").write(out)
    print("wrote %d completed net(s) into %s" % (len(plans), BRD))
    return 0 if len(plans) == len(remaining) else 1


if __name__ == "__main__":
    sys.exit(main())
