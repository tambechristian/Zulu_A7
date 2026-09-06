# -*- coding: utf-8 -*-
"""Does an inner plane pour actually reach every through object of its net?

    python tools/plane_islands.py [board.brd] [--layer 2] [--net GND]
    python tools/plane_islands.py zulu_a7.brd --layer 5 --net VCC3V3

WHY. check_connectivity treats a <polygonpour> on L2 or L5 as SOLID: every via
and plated pad of the net that crosses the layer is taken as one piece. That is
what a plane is for, but it is an assumption, and two things on this board can
break it. Seven signals were routed ON the plane layers with laser vias, and
every one of their traces is a slot cut through the copper. And the BGA moat
puts foreign vias at 0.39 mm centres, whose antipads overlap into a wall. A via
of the plane's own net standing inside such a slot or wall has copper around it
that is not the plane. Fusion's DRC reports exactly that as an "Air Wire" that
Ratsnest never showed, which is where the 63-against-41 gap came from.

HOW. Rasterise the pour outline. A pour centreline must keep `isolate` from
every foreign object and the copper it lays is `width` wide, so the region a
centreline may occupy is everything at least isolate + width/2 from foreign
copper. Flood that region into pieces. An own via or plated pad is reached by a
piece if a cell of that piece lies within its land radius + width/2 of it, so
the pour's copper edge touches the land. Report every own object that no piece
reaches (isolated) and every one reached only by a piece other than the main
plane (on an island).

Foreign plated pads are modelled at their full drawn diameter on the inner
layer, which is conservative: Eagle draws only the restring annulus there.
"""

import collections
import io
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import escape as E   # noqa: E402
import geom as G     # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RASTER = 0.05


def arg(name, default):
    if name in sys.argv:
        return sys.argv[sys.argv.index(name) + 1]
    return default


def via_span(attrs):
    first, last = (int(v) for v in attrs.get("extent", "1-16").split("-"))
    return min(first, last), max(first, last)


def analyse(board, layer, net, log=print, grid=None):
    """Raster the pour; report. With `grid` = (x0, y0, W, H) the raster is
    laid on the caller's grid (RASTER step) so its labels can be used as a
    routing layer. Returns a dict, or None if the net has no pour there:
        isolated, islanded   lists of (kind, x, y)
        reached              set of (x, y) rounded to 3 places, own objects
                             the main piece reaches
        label, main, W, H, x0, y0, S     the raster itself
    """
    sig = re.search(r"<signals>(.*)</signals>", board, re.S).group(1)
    signals = {}
    for m in re.finditer(r'<signal name="([^"]+)"[^>]*>(.*?)</signal>', sig, re.S):
        signals[m.group(1)] = m.group(2)
    own_body = signals.get(net, "")
    pm = re.search(r'<polygonpour layer="%d"([^>]*)>(.*?)</polygonpour>'
                   % layer, own_body, re.S)
    if not pm:
        log("  ****  %s has no pour on layer %d" % (net, layer))
        return None
    attrs = dict(re.findall(r'(\w+)="([^"]*)"', pm.group(1)))
    isolate = float(attrs.get("isolate", "0.25"))
    width = float(attrs.get("width", "0.1524"))
    verts = [(float(x), float(y)) for x, y in
             re.findall(r'<vertex x="([-\d.]+)" y="([-\d.]+)"', pm.group(2))]
    x0, x1 = min(v[0] for v in verts), max(v[0] for v in verts)
    y0, y1 = min(v[1] for v in verts), max(v[1] for v in verts)
    keep = isolate + width / 2.0

    # own entries: (kind, key x, key y, land radius, sample points). A pad or
    # via is one sample at its centre; an own wire on the layer is sampled
    # along its length, keyed by its first point, because Fusion pours the
    # copper straight over its own wires and they become part of the plane.
    circles, rects, own = [], [], []
    for onet, x, y, hx, hy, side in E.board_copper(board, skip=()):
        if side != 0 and side != layer:
            continue
        if onet == net:
            own.append(("pad", x, y, max(hx, hy), [(x, y)]))
        else:
            rects.append((x, y, hx, hy))
    segs = []
    for onet, body in signals.items():
        for vm in re.finditer(r"<via\s([^>]*)>", body):
            a = dict(re.findall(r'(\w+)="([^"]*)"', vm.group(1)))
            if "x" not in a:
                continue
            lo, hi = via_span(a)
            if not lo <= layer <= hi:
                continue
            drill = float(a.get("drill", "0.2"))
            if "diameter" in a:
                dia = float(a["diameter"])
            else:
                dia = drill + 2 * max(drill * 0.25, 0.05)
            x, y = float(a["x"]), float(a["y"])
            if onet == net:
                own.append(("via", x, y, dia / 2.0, [(x, y)]))
            else:
                circles.append((x, y, dia / 2.0))
        for w in re.finditer(
                r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)"'
                r' y2="([-\d.]+)" width="([\d.]+)" layer="(\d+)"', body):
            if int(w.group(6)) != layer:
                continue
            xa, ya, xb, yb, wd = (float(v) for v in w.groups()[:5])
            if onet == net:
                own.append(("wire", xa, ya, wd / 2.0,
                            [(sx, sy) for sx, sy, sr in G.sample((xa, ya), (xb, yb), wd / 2.0, step=RASTER)]))
            else:
                segs.append(((xa, ya), (xb, yb), wd / 2.0))

    S = RASTER
    if grid is None:
        W = int((x1 - x0) / S) + 1
        H = int((y1 - y0) / S) + 1
        N = W * H
        core = bytearray(b"\x01") * N
    else:
        gx0, gy0, W, H = grid
        N = W * H
        core = bytearray(N)
        for j in range(H):
            y = gy0 + j * S
            if not y0 - 1e-9 <= y <= y1 + 1e-9:
                continue
            i0 = max(0, int(math.ceil((x0 - gx0) / S - 1e-9)))
            i1 = min(W - 1, int(math.floor((x1 - gx0) / S + 1e-9)))
            if i1 >= i0:
                core[j * W + i0:j * W + i1 + 1] = b"\x01" * (i1 - i0 + 1)
        x0, y0 = gx0, gy0

    def ci(x):
        return int(round((x - x0) / S))

    def cj(y):
        return int(round((y - y0) / S))

    def block_circle(cx, cy, r):
        rad = r + keep
        rr = int(rad / S) + 2
        i0, j0 = ci(cx), cj(cy)
        for i in range(max(0, i0 - rr), min(W, i0 + rr + 1)):
            dx = x0 + i * S - cx
            for j in range(max(0, j0 - rr), min(H, j0 + rr + 1)):
                dy = y0 + j * S - cy
                if dx * dx + dy * dy < rad * rad:
                    core[j * W + i] = 0

    for cx, cy, r in circles:
        block_circle(cx, cy, r)
    for cx, cy, hx, hy in rects:
        rr = int((max(hx, hy) + keep) / S) + 2
        i0, j0 = ci(cx), cj(cy)
        for i in range(max(0, i0 - rr), min(W, i0 + rr + 1)):
            px = x0 + i * S
            for j in range(max(0, j0 - rr), min(H, j0 + rr + 1)):
                if G.rect_pt((cx, cy, hx, hy), px, y0 + j * S) < keep:
                    core[j * W + i] = 0
    for a, c, r in segs:
        for sx, sy, sr in G.sample(a, c, r, step=S):
            block_circle(sx, sy, sr)

    label = [0] * N
    sizes = {}
    nxt = 0
    for start in range(N):
        if not core[start] or label[start]:
            continue
        nxt += 1
        stack = [start]
        label[start] = nxt
        count = 0
        while stack:
            c = stack.pop()
            count += 1
            i, j = c % W, c // W
            for n in (c - 1 if i > 0 else -1, c + 1 if i < W - 1 else -1,
                      c - W if j > 0 else -1, c + W if j < H - 1 else -1):
                if n >= 0 and core[n] and not label[n]:
                    label[n] = nxt
                    stack.append(n)
        sizes[nxt] = count

    reach = collections.defaultdict(set)
    attached = {}
    for kind, x, y, r, samples in own:
        rad = r + width / 2.0
        rr = int(rad / S) + 2
        found = set()
        for sx, sy in samples:
            i0, j0 = ci(sx), cj(sy)
            for i in range(max(0, i0 - rr), min(W, i0 + rr + 1)):
                dx = x0 + i * S - sx
                for j in range(max(0, j0 - rr), min(H, j0 + rr + 1)):
                    dy = y0 + j * S - sy
                    c = j * W + i
                    if dx * dx + dy * dy <= rad * rad and label[c]:
                        found.add(label[c])
        attached[(kind, x, y)] = found
        for lab in found:
            reach[lab].add((kind, x, y))

    main_piece = None
    if sizes:
        main_piece = max(sizes, key=lambda k: (len(reach[k]), sizes[k]))
    total = sum(sizes.values()) or 1
    log("  L%d %s pour: %d piece(s); main piece %.1f %% of the pourable area,"
        " reaches %d of %d own through object(s)"
        % (layer, net, len(sizes),
           100.0 * sizes[main_piece] / total if main_piece else 0.0,
           len(reach[main_piece]) if main_piece else 0, len(own)))
    isolated = sorted(k for k, v in attached.items() if not v)
    islanded = sorted(k for k, v in attached.items()
                      if v and main_piece not in v)
    for kind, x, y in isolated:
        log("  ****  %s %s at (%.3f, %.3f) is not reached by any pour copper"
            % (net, kind, x, y))
    for kind, x, y in islanded:
        labs = attached[(kind, x, y)]
        log("  ****  %s %s at (%.3f, %.3f) sits on an island of %d cell(s),"
            " not the plane" % (net, kind, x, y, sum(sizes[l] for l in labs)))
    others = sorted(((sizes[k], len(reach[k])) for k in sizes
                     if k != main_piece and reach[k]), reverse=True)
    if others:
        log("  ----  %d island(s) carry own copper (cells, objects): %s"
            % (len(others), others[:8]))
    reached = set((round(x, 3), round(y, 3)) for kind, x, y in
                  (reach[main_piece] if main_piece else ()))
    # EVERY PIECE JOINS WHAT IT TOUCHES. An outer GND pour is cut into
    # hundreds of pieces by the traces, and Fusion keeps each piece that
    # touches an object of the net (orphans off); an SMD GND pad is then
    # connected exactly when some piece reaches both it and a via down to the
    # plane. "groups" is that: one key set per pour piece.
    groups = [set((round(x, 3), round(y, 3)) for kind, x, y in members)
              for members in reach.values() if len(members) > 1]
    return {"isolated": isolated, "islanded": islanded, "reached": reached, "groups": groups,
            "label": label, "main": main_piece, "W": W, "H": H,
            "x0": x0, "y0": y0, "S": S}


def main():
    brd = next((a for a in sys.argv[1:] if a.endswith(".brd")),
               os.path.join(ROOT, "zulu_a7.brd"))
    layer = int(arg("--layer", "2"))
    net = arg("--net", "GND" if layer == 2 else "VCC3V3")
    board = io.open(brd, encoding="utf-8", errors="replace").read()
    result = analyse(board, layer, net)
    if result is None:
        return 1
    return 1 if (result["isolated"] or result["islanded"]) else 0


if __name__ == "__main__":
    sys.exit(main())
