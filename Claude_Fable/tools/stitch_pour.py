# -*- coding: utf-8 -*-
"""Tie the orphaned islands of an outer pour back to the ground system.

WHY. A pour is not one piece. Every trace crossing it cuts it, and an island
with no via and no pad in it is copper connected to nothing: it carries no
return current, it shields nothing, and it sits at a floating potential. After
Fusion's autorouter put 1387 wires and its share of 868 vias on L16, that
layer's GND fill measured 220 pieces with only 76.6 % of the copper in a piece
that reaches GND, against a 95 % floor. Before the autoroute it was 92.1 %.

WHAT THIS IS NOT. ground.py's stitch() lays an even lattice over the whole
board, which is what you want for return path and for heat, and is the wrong
instrument here: it is blind to which pieces are already tied, so it spends most
of its vias on the one big piece that has fifty already. This finds the pieces
that are orphaned and puts ONE via in each, as deep inside it as the geometry
allows.

    python tools/stitch_pour.py            report
    python tools/stitch_pour.py --apply    write the vias into the board

The raster, the isolation and the anchor rule are check_planes' own, on purpose:
a fix measured by a different model than the check is not a fix.
"""
import io
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import escape as E
import geom as G
import power as P

_prev_stdout = sys.stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRD = os.environ.get("STITCH_BOARD", os.path.join(ROOT, "zulu_a7.brd"))
NET = os.environ.get("STITCH_NET", "GND")
LAYERS = [q for q in os.environ.get("STITCH_LAYERS", "16,1").split(",") if q]
RASTER = 0.15
ISO = 0.25
VIA_D, VIA_L = P.VIA_D, P.VIA_L
# An island smaller than this cannot take a via with clearance round it, and
# would not be worth one if it could: it is a sliver between two traces.
MIN_AREA = float(os.environ.get("STITCH_MIN_AREA", "0.60"))


def islands(brd, net, lay, X0, Y0, W, H):
    """(pieces, anchors, occupancy) on `lay` -- check_planes' raster and flood"""
    rects, circs, segs = G.copper_model(brd, net, int(lay))
    blk = G.as_circles([(x, y, hx + ISO, hy + ISO, 0.0)
                        for x, y, hx, hy, _c in rects])
    blk += [(x, y, r + ISO) for x, y, r in circs]
    for u, v, r in segs:
        blk += G.sample(u, v, r + ISO, 0.1)
    cop = bytearray(b"\x01" * (W * H))
    for ox, oy, r in blk:
        rr = int(r / RASTER) + 1
        ci, cj = int((ox - X0) / RASTER), int((oy - Y0) / RASTER)
        for i in range(max(0, ci - rr), min(W, ci + rr + 1)):
            for j in range(max(0, cj - rr), min(H, cj + rr + 1)):
                if (X0 + i * RASTER - ox) ** 2 + (Y0 + j * RASTER - oy) ** 2 <= r * r:
                    cop[j * W + i] = 0
    anchor = set()
    sig = re.search(r"<signals>(.*)</signals>", brd, re.S).group(1)
    gm = re.search(r'<signal name="%s"[^>]*>(.*?)</signal>' % re.escape(net),
                   sig, re.S)
    # ONLY WHAT ACTUALLY REACHES THE PLANES ANCHORS A PIECE. This used to count
    # every pad of the net, and that is circular: an SMD pad on L16 is copper on
    # L16 and nothing else, so an island whose only anchor is such a pad ties
    # the pad to the island and the island to the pad, with nothing going down
    # to the L2/L4 planes. The pair floats together.
    #
    # It is not an academic distinction. Under the old rule L16 read 89.7 % tied
    # with 23 orphans worth stitching; under this one it reads 81.0 % with 38.
    # And it is exactly why 44 GND pads still had airwires after stitch_pads
    # ran: every one of them sits on a piece this function was calling tied.
    # A via spans 1-16 and a plated hole is copper on every layer, so those two
    # anchor. Nothing else does.
    pts = [(x, y) for x, y, _d in G.vias(gm.group(1))] if gm else []
    pts += [(rec[1], rec[2]) for rec in E.board_copper(brd, skip=())
            if rec[0] == net and rec[5] == 0]
    for x, y in pts:
        i, j = int((x - X0) / RASTER), int((y - Y0) / RASTER)
        if 0 <= i < W and 0 <= j < H:
            anchor.add(j * W + i)
    seen = bytearray(W * H)
    pieces = []
    for st in range(W * H):
        if cop[st] and not seen[st]:
            cells, stack = [], [st]
            seen[st] = 1
            while stack:
                c = stack.pop()
                cells.append(c)
                for d in (-1, 1, -W, W):
                    q = c + d
                    if 0 <= q < W * H and cop[q] and not seen[q]:
                        if d in (-1, 1) and (q % W == 0 or c % W == 0):
                            continue
                        seen[q] = 1
                        stack.append(q)
            pieces.append(cells)
    return pieces, anchor, cop


def by_depth(cells, W, H):
    """every cell of `cells`, furthest from its own rim first.

    ONE CANDIDATE PER ISLAND IS NOT ENOUGH. A via is copper on all six layers,
    so a point sitting in the middle of an open L16 island can still be blocked
    by a trace crossing above it on L3 or L4 -- and with 6523 wires over four
    layers, it usually is: the deepest cell of all 33 orphaned islands was
    blocked, including one 43 mm2 island with 1.65 mm of depth. Offer the whole
    island instead, deepest first, and let the via grid pick.

    A via wants the middle of an island, not its rim: the rim is where the trace
    that cut the island runs, so a via there fails clearance even when the
    island is easily big enough. One breadth-first sweep inward from the
    boundary gives every cell its depth, and the deepest is the best on offer.
    """
    own = set(cells)
    dist = {}
    front = []
    for c in cells:
        edge = False
        for d in (-1, 1, -W, W):
            q = c + d
            if not (0 <= q < W * H) or q not in own:
                edge = True
                break
            if d in (-1, 1) and (q % W == 0 or c % W == 0):
                edge = True
                break
        if edge:
            dist[c] = 0
            front.append(c)
    step = 0
    while front:
        step += 1
        nxt = []
        for c in front:
            for d in (-1, 1, -W, W):
                q = c + d
                if q in own and q not in dist:
                    dist[q] = step
                    nxt.append(q)
        front = nxt
    if not dist:
        return [(c, 0) for c in cells]
    return sorted(dist.items(), key=lambda kv: -kv[1])


def main():
    b = io.open(BRD, encoding="utf-8", errors="replace").read()
    clr = G.rule_mm(b, "mdWireWire")
    w20 = re.findall(r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)"'
                     r' y2="([-\d.]+)" width="[\d.]+" layer="20"/>', b)
    xs = [float(q) for v in w20 for q in (v[0], v[2])]
    ys = [float(q) for v in w20 for q in (v[1], v[3])]
    X0, Y0 = min(xs), min(ys)
    W = int((max(xs) - X0) / RASTER) + 1
    H = int((max(ys) - Y0) / RASTER) + 1
    bx = (min(xs), min(ys), max(xs), max(ys))

    # a stitching via has to clear every OTHER net's copper, on every layer
    vmz = P.Maze(G.obstacles(b, frozenset((NET,)), None, ()), bx, clr, VIA_L, 0.05)
    drill_clearance = G.rule_mm(b, "mdDrill")
    existing_drills = []
    for match in re.finditer(r"<via\s([^>]*)>", b):
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', match.group(1)))
        existing_drills.append((
            float(attrs["x"]), float(attrs["y"]),
            float(attrs.get("drill", str(VIA_D)))))
    placed, out = [], []
    for lay in LAYERS:
        pieces, anchor, _cop = islands(b, NET, lay, X0, Y0, W, H)
        area = sum(len(p) for p in pieces) * RASTER * RASTER
        tied = sum(len(p) for p in pieces
                   if any(c in anchor for c in p)) * RASTER * RASTER
        orph = [p for p in pieces if not any(c in anchor for c in p)]
        big = [p for p in orph if len(p) * RASTER * RASTER >= MIN_AREA]
        print("L%-3s %3d piece(s), %.1f%% tied; %d orphaned, %d of them >= %.2f mm2"
              % (lay, len(pieces), 100 * tied / area if area else 100.0,
                 len(orph), len(big), MIN_AREA))
        got = 0
        for cells in sorted(big, key=lambda p: -len(p)):
            for c, _depth in by_depth(cells, W, H):
                # NO DEPTH FILTER. `vmz` already holds a via to clr + VIA_L/2
                # from every foreign object on every layer, which is the actual
                # rule; a depth test on top of it only throws away cells the
                # grid would have accepted. Depth still orders the search --
                # the middle of an island is the best place to start looking.
                x, y = X0 + (c % W) * RASTER, Y0 + (c // W) * RASTER
                if not vmz.free[vmz.j(y) * vmz.W + vmz.i(x)]:
                    continue
                if any(math.hypot(x - vx, y - vy) <
                       VIA_D / 2.0 + drill / 2.0 + drill_clearance - 1e-9
                       for vx, vy, drill in existing_drills):
                    continue
                if any((x - a) ** 2 + (y - d) ** 2 < (VIA_L + clr) ** 2
                       for a, d in placed):
                    continue
                placed.append((x, y))
                out.append((round(x, 4), round(y, 4)))
                got += 1
                break
        print("      %d via(s) placed into orphaned islands" % got)
    if not out:
        print("\nnothing to stitch")
        return 0
    if "--apply" not in sys.argv:
        print("\nreport only -- re-run with --apply to write %d via(s)" % len(out))
        return 0
    g = E.g
    add = "".join('<via x="%s" y="%s" extent="1-16" drill="%s" diameter="%s"/>'
                  % (g(x), g(y), g(VIA_D), g(VIA_L)) for x, y in out)
    m = re.search(r'(<signal name="%s"[^>]*>)' % re.escape(NET), b)
    b = b[:m.end()] + add + b[m.end():]
    import xml.etree.ElementTree as ET
    ET.fromstring(b)
    io.open(BRD, "w", encoding="utf-8", newline="").write(b)
    print("\nwrote %d stitching via(s) into %s" % (len(out), BRD))
    return 0


if __name__ == "__main__":
    sys.exit(main())
