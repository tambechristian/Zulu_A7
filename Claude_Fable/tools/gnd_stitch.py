# -*- coding: utf-8 -*-
"""Tie every plane-net SMD pad that no pour reaches to the plane with one
through via and one short wire.

    python tools/gnd_stitch.py in.brd out.brd [--net GND] [--width 0.15]

WHY. Fusion's outer GND pours are cut into hundreds of pieces by the traces,
and a GND pad of a small capacitor can end up in a piece that touches no via
down to the L3 plane. Ratsnest then draws an airwire from the pad to the
nearest GND copper (four of them on 2026-09-05). The router treats GND as a
plane and never routes to such a pad; this does the one thing needed.

HOW. For every piece of the net (check_connectivity, Fusion's rules with the
pour raster) that holds no through object, take its first SMD pad and search
a 0.05 mm grid within REACH of the pad centre for a via spot where
  - the via land clears every foreign wire, via and pad on every layer it
    crosses by the 3 mil rule, and every foreign drill by MIN_DRILL_CC;
  - a straight wire from the pad centre to the via on the pad's layer clears
    foreign copper there the same way.
The nearest legal spot wins; the wire is `--width` wide, falling back to the
3 mil minimum if the wide one finds no spot. Whether the plane actually
reaches the new via is then the pour raster's verdict: run
tools/fusion_model.py on the output.
"""

import io
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_connectivity as C   # noqa: E402
import escape as E   # noqa: E402
import geom as G     # noqa: E402

CLR = 0.0762
VIA_D, VIA_L = 0.2, 0.3
MIN_DRILL_CC = 0.4
REACH = 1.6
STEP = 0.05
SIG_RE = re.compile(r'(<signal name="([^"]+)"[^>]*>)(.*?)(</signal>)', re.S)


def g(v):
    t = ("%.4f" % v).rstrip("0").rstrip(".")
    return t if t not in ("", "-0") else "0"


def foreign_copper(board, parsed, net):
    """everything that is not `net`, as check_connectivity objects, plus the
    pads that belong to no net at all"""
    out = []
    for other, (objects, terminals, planes) in parsed.items():
        if other == net:
            continue
        out.extend(objects)
    for n, x, y, hx, hy, side in E.board_copper(board, skip=()):
        if n is None:
            out.append({"kind": "pad", "at": (x, y), "hx": hx, "hy": hy, "through": side == 0,
                        "layers": C.COPPER_LAYERS if side == 0 else frozenset((side,))})
    return out


def near(objects, x, y, r):
    box = []
    for o in objects:
        if o["kind"] == "wire":
            if min(o["a"][0], o["b"][0]) - r <= x <= max(o["a"][0], o["b"][0]) + r and \
                    min(o["a"][1], o["b"][1]) - r <= y <= max(o["a"][1], o["b"][1]) + r:
                box.append(o)
        else:
            if abs(o["at"][0] - x) <= r + 1.0 and abs(o["at"][1] - y) <= r + 1.0:
                box.append(o)
    return box


def via_ok(local, x, y):
    for o in local:
        if o["kind"] == "wire":
            if E.seg_pt(o["a"], o["b"], (x, y)) < o["radius"] + VIA_L / 2 + CLR:
                return False
        elif o["kind"] == "via":
            d = math.hypot(o["at"][0] - x, o["at"][1] - y)
            if d < o["radius"] + VIA_L / 2 + CLR or d < MIN_DRILL_CC:
                return False
        else:
            if o["through"]:
                d = math.hypot(o["at"][0] - x, o["at"][1] - y)
                if d < o["hx"] + VIA_L / 2 + CLR or d < o["hx"] + 0.25:
                    return False
            elif G.rect_pt((o["at"][0], o["at"][1], o["hx"], o["hy"]), x, y) < VIA_L / 2 + CLR:
                return False
    return True


def wire_ok(local, a, b, w, layer):
    for o in local:
        if layer not in o["layers"]:
            continue
        if o["kind"] == "wire":
            if E.seg_seg(o["a"], o["b"], a, b) < o["radius"] + w / 2 + CLR:
                return False
        elif o["kind"] == "via":
            if E.seg_pt(a, b, o["at"]) < o["radius"] + w / 2 + CLR:
                return False
        else:
            if o["through"]:
                if E.seg_pt(a, b, o["at"]) < o["hx"] + w / 2 + CLR:
                    return False
            elif G.rect_seg((o["at"][0], o["at"][1], o["hx"], o["hy"], 0.0), a, b) < w / 2 + CLR:
                return False
    return True


MAZE_WINDOW = 3.5


def maze_wire(local, pad, anchors, w, layer):
    """Shortest 4-connected path on a STEP grid from the pad to the land of
    any anchor (own via or plated pad on `layer`), each cell a legal wire
    end; returns the corner points from the pad centre to the anchor centre,
    every leg re-checked exactly, or None."""
    px, py = pad["at"]
    n = int(MAZE_WINDOW / STEP)
    W = 2 * n + 1

    def cell_xy(i, j):
        return round(px + (i - n) * STEP, 4), round(py + (j - n) * STEP, 4)

    goals = {}
    for o in anchors:
        r = o["radius"] if o["kind"] == "via" else o["hx"]
        for i in range(W):
            for j in range(W):
                x, y = cell_xy(i, j)
                if math.hypot(x - o["at"][0], y - o["at"][1]) <= max(r - w / 2, 0.0) + 1e-9:
                    goals[(i, j)] = o["at"]
    if not goals:
        return None
    free = {}

    def is_free(i, j):
        if (i, j) not in free:
            x, y = cell_xy(i, j)
            inside = abs(x - px) <= pad["hx"] - w / 2 + 1e-9 and abs(y - py) <= pad["hy"] - w / 2 + 1e-9
            free[(i, j)] = inside or (i, j) in goals or wire_ok(local, (x, y), (x, y), w, layer)
        return free[(i, j)]

    start = (n, n)
    prev = {start: None}
    queue = [start]
    hit = None
    while queue and hit is None:
        nxt = []
        for c in queue:
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                m = (c[0] + d[0], c[1] + d[1])
                if not (0 <= m[0] < W and 0 <= m[1] < W) or m in prev or not is_free(*m):
                    continue
                prev[m] = c
                if m in goals:
                    hit = m
                    break
                nxt.append(m)
            if hit:
                break
        queue = nxt
    if hit is None:
        return None
    cells = []
    c = hit
    while c is not None:
        cells.append(c)
        c = prev[c]
    cells.reverse()
    pts = [(px, py)] + [cell_xy(*c) for c in cells[1:]] + [goals[hit]]
    # merge collinear runs
    corners = [pts[0]]
    for a, b, c in zip(pts, pts[1:], pts[2:]):
        if abs((b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])) > 1e-9:
            corners.append(b)
    corners.append(pts[-1])
    legs = [(a, b) for a, b in zip(corners, corners[1:]) if math.hypot(b[0] - a[0], b[1] - a[1]) > 1e-6]
    for a, b in legs:
        # the first leg starts inside the pad and the last ends inside the
        # anchor; both are the net's own copper, so only foreign copper matters
        if not wire_ok(local, a, b, w, layer):
            return None
    return [legs[0][0]] + [b for a, b in legs]


def main():
    args = sys.argv[1:]
    net = "GND"
    width = 0.15
    if "--net" in args:
        i = args.index("--net")
        net = args[i + 1]
        del args[i:i + 2]
    if "--width" in args:
        i = args.index("--width")
        width = float(args[i + 1])
        del args[i:i + 2]
    forced = []
    if "--pads" in args:
        i = args.index("--pads")
        forced = [tuple(float(v) for v in item.split(",")) for item in args[i + 1].split(";") if item]
        del args[i:i + 2]
    src, dst = args[0], args[1]
    board = io.open(src, encoding="utf-8", errors="replace").read()
    parsed = C.parse_signal_objects(board)
    objects, terminals, planes = parsed[net]
    groups = C.components(objects, terminals, planes)
    stranded = []
    for grp in groups:
        if any(objects[i]["kind"] == "via" or (objects[i]["kind"] == "pad" and objects[i]["through"]) for i in grp):
            continue
        pads = [objects[i] for i in grp if objects[i]["kind"] == "pad"]
        if pads:
            stranded.append(pads[0])
    # FUSION'S LIST OUTRANKS THE RASTER. The pour raster is an approximation
    # of Fusion's pour; when tools/airwires.ulp says a pad is stranded, it is.
    for fx, fy in forced:
        if not any(math.hypot(p["at"][0] - fx, p["at"][1] - fy) < 0.01 for p in stranded):
            pad = next((o for o in objects[:terminals] if math.hypot(o["at"][0] - fx, o["at"][1] - fy) < 0.01), None)
            if pad is None:
                print("  ****  no %s pad at (%.3f,%.3f)" % (net, fx, fy))
            else:
                stranded.append(pad)
    print("%s: %d piece(s), %d pad(s) to stitch" % (net, len(groups), len(stranded)))
    foreign = foreign_copper(board, parsed, net)
    own = [o for o in objects if o["kind"] != "pad"]
    adds = ""
    for pad in stranded:
        px, py = pad["at"]
        layer = min(pad["layers"])
        local = near(foreign, px, py, MAZE_WINDOW + 0.5)
        own_local = near(own, px, py, MAZE_WINDOW + 0.5)
        # A VIA OF ITS OWN FIRST. Seven VCC3V3 decoupling pads hung off one
        # via by 4 mm of L16 wire (2026-09-06) is not decoupling; when a spot
        # within 0.8 mm of the pad is free, the pad gets its own via.
        quick = None
        for w in (width, CLR):
            for i in range(-16, 17):
                for j in range(-16, 17):
                    x, y = round(px + i * STEP, 4), round(py + j * STEP, 4)
                    d = math.hypot(x - px, y - py)
                    if not (min(pad["hx"], pad["hy"]) < d <= 0.8) or (quick and d >= quick[0]):
                        continue
                    if via_ok(local, x, y) and wire_ok(local, (px, py), (x, y), w, layer) and not any(
                            o["kind"] == "via" and math.hypot(o["at"][0] - x, o["at"][1] - y) < MIN_DRILL_CC for o in own_local):
                        quick = (d, x, y, w)
            if quick:
                break
        if quick:
            d, x, y, w = quick
            adds += '<via x="%s" y="%s" extent="1-16" drill="%s" diameter="%s"/>' % (g(x), g(y), g(VIA_D), g(VIA_L))
            adds += '<wire x1="%s" y1="%s" x2="%s" y2="%s" width="%s" layer="%d"/>' % (g(px), g(py), g(x), g(y), g(w), layer)
            own.append({"kind": "via", "at": (x, y), "radius": VIA_L / 2, "layers": C.COPPER_LAYERS})
            print("  %s pad (%.3f,%.3f) L%d -> own via (%.3f,%.3f), %.2f mm wire %.4f wide" % (net, px, py, layer, x, y, d, w))
            continue
        # FIRST CHOICE: A WIRE TO OWN COPPER ALREADY ON THE PLANE. A through
        # via or plated pad of the net within reach, on the pad's layer, with
        # a clear straight (or one-corner) wire to it, adds no drill at all.
        anchors = sorted(
            ((math.hypot(o["at"][0] - px, o["at"][1] - py), o) for o in own_local
             if (o["kind"] == "via" or o.get("through")) and layer in o["layers"]
             and math.hypot(o["at"][0] - px, o["at"][1] - py) <= MAZE_WINDOW),
            key=lambda t: t[0])
        done = False
        for w in (width, CLR):
            for d, o in anchors:
                tx, ty = o["at"]
                routes = [[(px, py), (tx, ty)], [(px, py), (tx, py), (tx, ty)], [(px, py), (px, ty), (tx, ty)]]
                for pts in routes:
                    legs = [(a, b) for a, b in zip(pts, pts[1:]) if math.hypot(b[0] - a[0], b[1] - a[1]) > 1e-6]
                    if all(wire_ok(local, a, b, w, layer) for a, b in legs):
                        for a, b in legs:
                            adds += '<wire x1="%s" y1="%s" x2="%s" y2="%s" width="%s" layer="%d"/>' % (
                                g(a[0]), g(a[1]), g(b[0]), g(b[1]), g(w), layer)
                        print("  %s pad (%.3f,%.3f) L%d -> wire to own %s at (%.3f,%.3f), %d leg(s) %.4f wide"
                              % (net, px, py, layer, o["kind"], tx, ty, len(legs), w))
                        done = True
                        break
                if done:
                    break
            if done:
                break
        if done:
            continue
        # SECOND CHOICE: A MAZE PATH ON THE PAD'S LAYER to the same anchors,
        # for the pad whose straight lines are all blocked but whose corner
        # of the board still has a lane through it.
        for w in (width, CLR):
            path = maze_wire(local, pad, [o for d, o in anchors], w, layer)
            if path:
                for a, b in zip(path, path[1:]):
                    adds += '<wire x1="%s" y1="%s" x2="%s" y2="%s" width="%s" layer="%d"/>' % (
                        g(a[0]), g(a[1]), g(b[0]), g(b[1]), g(w), layer)
                print("  %s pad (%.3f,%.3f) L%d -> maze wire to own copper at (%.3f,%.3f), %d leg(s) %.4f wide"
                      % (net, px, py, layer, path[-1][0], path[-1][1], len(path) - 1, w))
                done = True
                break
        if done:
            continue
        # candidates: beside the pad first, nearest first; INSIDE the pad as
        # the last resort. A via in a capacitor pad is filled and capped
        # (IPC-4761 Type VII) like the ones in U2's paddle -- an approved
        # practice on this board -- and it needs no wire at all, which is what
        # saves a 0.3 mm pad boxed in by 3 mil traces on three sides.
        inside_r = min(pad["hx"], pad["hy"])
        cands = []
        n = int(REACH / STEP)
        for i in range(-n, n + 1):
            for j in range(-n, n + 1):
                x, y = round(px + i * STEP, 4), round(py + j * STEP, 4)
                d = math.hypot(x - px, y - py)
                if inside_r < d <= REACH:
                    cands.append((0, d, x, y, False))
        # inside the pad on a 0.01 mm grid: the legal band between two 3 mil
        # traces on an inner layer can be 0.04 mm wide, and 0.05 steps miss it
        m = int(inside_r / 0.01)
        for i in range(-m, m + 1):
            for j in range(-m, m + 1):
                x, y = round(px + i * 0.01, 4), round(py + j * 0.01, 4)
                d = math.hypot(x - px, y - py)
                if d <= inside_r + 1e-9:
                    cands.append((1, d, x, y, True))
        cands.sort()
        placed = None
        for w in (width, CLR):
            for _, _, x, y, inside in cands:
                if not via_ok(local, x, y):
                    continue
                # own vias too close in drill terms
                if any(o["kind"] == "via" and math.hypot(o["at"][0] - x, o["at"][1] - y) < MIN_DRILL_CC for o in own_local):
                    continue
                if not inside and not wire_ok(local, (px, py), (x, y), w, layer):
                    continue
                placed = (x, y, w, inside)
                break
            if placed:
                break
        if not placed:
            print("  ****  %s pad at (%.3f,%.3f) L%d: no via spot within %.1f mm" % (net, px, py, layer, REACH))
            continue
        x, y, w, inside = placed
        adds += '<via x="%s" y="%s" extent="1-16" drill="%s" diameter="%s"/>' % (g(x), g(y), g(VIA_D), g(VIA_L))
        own.append({"kind": "via", "at": (x, y), "radius": VIA_L / 2, "layers": C.COPPER_LAYERS})
        if inside:
            print("  %s pad (%.3f,%.3f) L%d -> VIA-IN-PAD at (%.3f,%.3f): fill and cap, add to the fab note"
                  % (net, px, py, layer, x, y))
            continue
        adds += '<wire x1="%s" y1="%s" x2="%s" y2="%s" width="%s" layer="%d"/>' % (g(px), g(py), g(x), g(y), g(w), layer)
        print("  %s pad (%.3f,%.3f) L%d -> via (%.3f,%.3f), %.2f mm wire %.4f wide" % (net, px, py, layer, x, y, math.hypot(x - px, y - py), w))
    if not adds:
        print("nothing to do")
        return 1

    def sub(m):
        if m.group(2) != net:
            return m.group(0)
        return m.group(1) + m.group(3) + adds + m.group(4)

    out = SIG_RE.sub(sub, board)
    import xml.etree.ElementTree as ET
    ET.fromstring(out)
    io.open(dst, "w", encoding="utf-8", newline="").write(out)
    print("wrote", dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
