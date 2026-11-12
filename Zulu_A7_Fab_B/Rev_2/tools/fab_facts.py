# -*- coding: utf-8 -*-
"""Measure the fabrication facts of the Fab B board straight from the saved PcbDoc
and the exported NC drill files, for the PCBWay fab notes.  Read-only.

    python tools/fab_facts.py            # prints a report, writes tools/fab_facts.json
    python tools/fab_facts.py --pcb OTHER.PcbDoc --outputs "OTHER/Project Outputs for zulu_a7_fab_b"
                                         # cross-check another board; prints only, writes nothing

Rev 2 (2026-11-11) added, so that every board-derived number in the fab notes comes
from this report: via_stacks (microvias stacked on buried vias), via_in_pad_columns
(spans present at each via-in-pad XY), x1_hole_pads (X1 hole/slot lands per layer),
mask_rules, and mask_over_through_vias (solder-mask openings from the exported
GTS/GBS flashes measured against every through-via land and hole).  The keys Rev 1
wrote are unchanged, so tools/fab_facts_rev1.json diffs against this file directly.

Record offsets (as tools/route_inputs.py in Zulu_Altium_VS_Code):
  Pads6   body: layer@0 net@3 comp@7 x@13 y@17 sx@21 sy@25 hole@45 shape@49..51 rot(double)@52
  Vias6   body: net@3 x@13 y@17 size@21 hole@25 start-layer@29 end-layer@30
  Tracks6 body: layer@0 net@3 polygon@5 comp@7 x1@13 y1@17 x2@21 y2@25 width@29
  Arcs6   body: layer@0 net@3 polygon@5 x@13 y@17 r@21 a0(double)@25 a1@33 width@41
Units 1/10000 mil (2.54e-6 mm), board origin, y up.
"""
import json
import math
import os
import re
import struct
import sys
from collections import Counter, defaultdict

import olefile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROJECT = os.path.join(ROOT, "Imported zulu_a7.PrjPcb")
PCB = os.path.join(PROJECT, "zulu_a7_fab_b.PcbDoc")
OUTPUTS = os.path.join(PROJECT, "Project Outputs for zulu_a7_fab_b")
BASE = "zulu_a7_fab_b"
U = 2.54e-6
LAYER = {1: "Top", 4: "L2-GND", 2: "L3-SIG", 3: "L4-SIG", 5: "L5-VCC3V3", 32: "Bottom", 74: "Multi"}
STACK = ["Top", "L2-GND", "L3-SIG", "L4-SIG", "L5-VCC3V3", "Bottom"]
COPPER_IDS = (1, 4, 2, 3, 5, 32)
DRILL_FILE_SPAN = {
    "TX3": ("L3-SIG", "L4-SIG"),
    "TX6": ("Top", "L2-GND"),
    "TX7": ("L2-GND", "L3-SIG"),
    "TX9": ("L4-SIG", "L5-VCC3V3"),
    "TX10": ("L5-VCC3V3", "Bottom"),
}


def i32(b, o):
    return struct.unpack("<i", b[o:o + 4])[0]


def kvs(f, stream, key):
    d = f.openstream(stream).read().decode("latin-1", "replace")
    out = []
    for r in (x for x in d.split(chr(0)) if key in x):
        kv = {}
        for item in r.strip("|").split("|"):
            if "=" in item:
                k, v = item.split("=", 1)
                kv[k] = v
        out.append(kv)
    return out


def simple_records(data, kind):
    i = 0
    while i + 5 <= len(data):
        t = data[i]
        ln = struct.unpack("<I", data[i + 1:i + 5])[0]
        b = data[i + 5:i + 5 + ln]
        i += 5 + ln
        if t == kind:
            yield b


def read_board(path=PCB):
    f = olefile.OleFileIO(path)
    nets = {i: kv.get("NAME") for i, kv in enumerate(kvs(f, "Nets6/Data", "NAME="))}
    comps = {i: kv.get("SOURCEDESIGNATOR") for i, kv in enumerate(kvs(f, "Components6/Data", "SOURCEDESIGNATOR="))}

    d = f.openstream("Pads6/Data").read()
    pads = []
    i = 0
    while i + 5 <= len(d):
        if d[i] != 2:
            break
        ln = struct.unpack("<I", d[i + 1:i + 5])[0]
        name = d[i + 6:i + 6 + d[i + 5]].decode("latin-1")
        i += 5 + ln
        for _ in range(3):
            i += 4 + struct.unpack("<I", d[i:i + 4])[0]
        l2 = struct.unpack("<I", d[i:i + 4])[0]
        b = d[i + 4:i + 4 + l2]
        i += 4 + l2
        i += 4 + struct.unpack("<I", d[i:i + 4])[0]
        if len(b) < 60:
            continue
        net = struct.unpack("<h", b[3:5])[0]
        comp = struct.unpack("<h", b[7:9])[0]
        pads.append(dict(
            ref=comps.get(comp) if comp >= 0 else None, pad=name, layer=LAYER.get(b[0], str(b[0])),
            net=nets.get(net) if net >= 0 else None,
            x=i32(b, 13) * U, y=i32(b, 17) * U, sx=i32(b, 21) * U, sy=i32(b, 25) * U,
            size={"Top": (i32(b, 21) * U, i32(b, 25) * U, b[49]), "Mid": (i32(b, 29) * U, i32(b, 33) * U, b[50]),
                  "Bottom": (i32(b, 37) * U, i32(b, 41) * U, b[51])},
            hole=i32(b, 45) * U, shape=b[49], rot=struct.unpack("<d", b[52:60])[0]))

    vias = []
    for b in simple_records(f.openstream("Vias6/Data").read(), 3):
        net = struct.unpack("<h", b[3:5])[0]
        lo, hi = sorted((STACK.index(LAYER[b[29]]), STACK.index(LAYER[b[30]])))
        vias.append(dict(net=nets.get(net) if net >= 0 else None, x=i32(b, 13) * U, y=i32(b, 17) * U,
                         size=i32(b, 21) * U, hole=i32(b, 25) * U, span=(STACK[lo], STACK[hi])))

    tracks = []
    for b in simple_records(f.openstream("Tracks6/Data").read(), 4):
        if b[0] not in COPPER_IDS:
            continue
        net = struct.unpack("<h", b[3:5])[0]
        poly = struct.unpack("<h", b[5:7])[0]
        tracks.append(dict(layer=LAYER[b[0]], net=nets.get(net) if net >= 0 else None, poly=poly,
                           x1=i32(b, 13) * U, y1=i32(b, 17) * U, x2=i32(b, 21) * U, y2=i32(b, 25) * U,
                           width=i32(b, 29) * U))
    arcs = []
    for b in simple_records(f.openstream("Arcs6/Data").read(), 1):
        if b[0] not in COPPER_IDS:
            continue
        net = struct.unpack("<h", b[3:5])[0]
        poly = struct.unpack("<h", b[5:7])[0]
        arcs.append(dict(layer=LAYER[b[0]], net=nets.get(net) if net >= 0 else None, poly=poly,
                         width=i32(b, 41) * U))
    rules = kvs(f, "Rules6/Data", "RULEKIND=")
    board = f.openstream("Board6/Data").read().decode("latin-1")
    f.close()
    return dict(pads=pads, vias=vias, tracks=tracks, arcs=arcs, rules=rules, board=board)


# ---- geometry ---------------------------------------------------------------
def pad_frame(p, x, y):
    """Point (x, y) in the pad's own frame (pad centred, unrotated)."""
    a = math.radians(-p["rot"])
    dx, dy = x - p["x"], y - p["y"]
    return dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a)


def pad_core(p):
    """Pad as (core half-x, core half-y, radius): a rect inflated by radius.
    Round (1) -> obround/circle; rect (2), octagon (3), others -> rect (conservative)."""
    hx, hy = p["sx"] / 2, p["sy"] / 2
    if p["shape"] == 1:
        r = min(hx, hy)
        return hx - r, hy - r, r
    return hx, hy, 0.0


def point_rect_dist(px, py, hx, hy):
    dx = max(abs(px) - hx, 0.0)
    dy = max(abs(py) - hy, 0.0)
    return math.hypot(dx, dy)


def pad_point_dist(p, x, y):
    """Signed-ish distance from a point to the pad copper (0 inside)."""
    hx, hy, r = pad_core(p)
    px, py = pad_frame(p, x, y)
    return max(point_rect_dist(px, py, hx, hy) - r, 0.0)


def pad_inner_depth(p, x, y):
    """How far inside the pad edge the point lies (<= 0 when outside)."""
    hx, hy, r = pad_core(p)
    px, py = pad_frame(p, x, y)
    if r == 0:
        return min(hx - abs(px), hy - abs(py))
    return r - point_rect_dist(px, py, hx, hy)


def seg_point_dist(ax, ay, bx, by, px, py):
    vx, vy = bx - ax, by - ay
    L2 = vx * vx + vy * vy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / L2))
    return math.hypot(ax + t * vx - px, ay + t * vy - py)


def seg_seg_dist(a, b):
    def ccw(p, q, r):
        return (r[1] - p[1]) * (q[0] - p[0]) - (q[1] - p[1]) * (r[0] - p[0])
    p1, p2, p3, p4 = (a[0], a[1]), (a[2], a[3]), (b[0], b[1]), (b[2], b[3])
    d1, d2, d3, d4 = ccw(p3, p4, p1), ccw(p3, p4, p2), ccw(p1, p2, p3), ccw(p1, p2, p4)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)) and d1 and d2 and d3 and d4:
        return 0.0
    return min(seg_point_dist(*b, *p1), seg_point_dist(*b, *p2),
               seg_point_dist(*a, *p3), seg_point_dist(*a, *p4))


def seg_pad_dist(t, p):
    """Distance between a track centreline and the pad copper (convex)."""
    hx, hy, r = pad_core(p)
    ax, ay = pad_frame(p, t["x1"], t["y1"])
    bx, by = pad_frame(p, t["x2"], t["y2"])
    corners = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
    edges = [(*corners[k], *corners[(k + 1) % 4]) for k in range(4)]
    inside = point_rect_dist(ax, ay, hx, hy) == 0 or point_rect_dist(bx, by, hx, hy) == 0
    if inside:
        return 0.0
    d = min(seg_seg_dist((ax, ay, bx, by), e) for e in edges)
    return max(d - r, 0.0)


def pad_on_layer(p, layer):
    return p["layer"] == layer or p["layer"] == "Multi"


def pad_view(p, layer):
    """The pad as it is on one copper layer (per-layer size and shape of a Multi pad)."""
    if p["layer"] != "Multi":
        if p["layer"] == "Bottom":
            sx, sy, sh = p["size"]["Bottom"] if p["size"]["Bottom"][0] > 0 else p["size"]["Top"]
        else:
            sx, sy, sh = p["size"]["Top"]
    else:
        sx, sy, sh = p["size"][layer if layer in ("Top", "Bottom") else "Mid"]
    q = dict(p)
    q.update(sx=sx, sy=sy, shape=sh)
    return q


# ---- Excellon ---------------------------------------------------------------
def excellon_hits(path):
    """{tool: [(x, y), ...]} for a METRIC,LZ 4:4 file; modal X/Y kept."""
    hits = defaultdict(list)
    tool = None
    x = y = None
    in_header = True
    with open(path, encoding="ascii") as handle:
        for raw in handle:
            line = raw.strip()
            if line == "%":
                in_header = False
                continue
            if in_header:
                continue
            m = re.fullmatch(r"T(\d+)", line)
            if m:
                tool = m.group(1)
                continue
            m = re.fullmatch(r"(?:X(-?\d+))?(?:Y(-?\d+))?(G85.*)?", line)
            if m and (m.group(1) or m.group(2)):
                if m.group(1):
                    x = coord(m.group(1))
                if m.group(2):
                    y = coord(m.group(2))
                hits[tool].append((x, y))
    return dict(hits)


def coord(s):
    neg = s.startswith("-")
    s = s.lstrip("-")
    v = int(s.ljust(8, "0")) / 10000.0
    return -v if neg else v


# ---- Gerber solder-mask openings ----------------------------------------------
def gerber_flashes(path):
    """[(x, y, (hx, hy, r), exact)] for every D03 flash of a metric 4.4 RS-274X file.

    Each opening is modelled as a rectangle of half-sizes hx, hy inflated by r
    (circle: 0, 0, r; obround and rounded rectangle: core + corner radius).  An
    octagon, or a macro at a rotation other than 0/90/180/270, is taken as its
    bounding box (exact=False), which can only over-state the opening.  The
    file must hold flashes only: a draw (D01) or a region (G36) would be an
    opening this model cannot see, so it is refused rather than ignored."""
    with open(path, encoding="ascii") as handle:
        text = handle.read()
    if "%MOMM*%" not in text or "%FSLAX44Y44*%" not in text:
        raise ValueError("%s is not metric 4.4 RS-274X" % os.path.basename(path))
    if "G36" in text or re.search(r"D0?1\*", text) or "%LP" in text:
        raise ValueError("%s has draws, regions or polarity changes" % os.path.basename(path))
    macro = {}
    for m in re.finditer(r"G04:AMPARAMS\|DCode=(\d+)\|XSize=([\d.]+)mm\|YSize=([\d.]+)mm\|"
                         r"CornerRadius=([\d.]+)mm\|.*?Rotation=([\d.]+)\|.*?Shape=(\w+)\|", text):
        macro[int(m.group(1))] = (float(m.group(2)), float(m.group(3)), float(m.group(4)),
                                  float(m.group(5)), m.group(6))
    shapes = {}
    for m in re.finditer(r"%ADD(\d+)([A-Z][A-Z0-9_]*?)(?:,([\d.X]+))?\*%", text):
        code, kind = int(m.group(1)), m.group(2)
        par = [float(v) for v in (m.group(3) or "").split("X") if v]
        if kind == "C":
            shapes[code] = ((0.0, 0.0, par[0] / 2), True)
        elif kind == "R":
            shapes[code] = ((par[0] / 2, par[1] / 2, 0.0), True)
        elif kind == "O":
            r = min(par[0], par[1]) / 2
            shapes[code] = ((par[0] / 2 - r, par[1] / 2 - r, r), True)
        elif code in macro:
            xs, ys, cr, rot, shape = macro[code]
            square = abs(rot % 90) < 1e-6
            if square and round(rot) % 180 == 90:
                xs, ys = ys, xs
            if shape == "RoundedRectangle" and square:
                shapes[code] = ((xs / 2 - cr, ys / 2 - cr, cr), True)
            else:
                h = max(xs, ys) / 2 if not square else None
                shapes[code] = (((h, h, 0.0) if h else (xs / 2, ys / 2, 0.0)), False)
        else:
            raise ValueError("%s: aperture D%d (%s) is not modelled" % (os.path.basename(path), code, kind))
    flashes = []
    x = y = 0
    cur = None
    for line in text.splitlines():
        line = line.strip()
        sel = re.fullmatch(r"(?:G54)?D(\d+)\*", line)
        if sel and int(sel.group(1)) >= 10:
            cur = int(sel.group(1))
            continue
        op = re.fullmatch(r"(?:X(-?\d+))?(?:Y(-?\d+))?D0?([23])\*", line)
        if op:
            if op.group(1):
                x = int(op.group(1)) / 10000.0
            if op.group(2):
                y = int(op.group(2)) / 10000.0
            if op.group(3) == "3":
                if cur not in shapes:
                    raise ValueError("%s: flash with undefined aperture D%s" % (os.path.basename(path), cur))
                flashes.append((x, y) + shapes[cur])
    return flashes


def opening_dist(flash, x, y):
    """Distance from (x, y) to the opening's edge, 0 when the point is inside it."""
    fx, fy, (hx, hy, r), _ = flash
    return max(point_rect_dist(x - fx, y - fy, hx, hy) - r, 0.0)


def tol_diff(a, b, tol=0.002):
    """Points of list a with no partner in list b within tol (one-to-one)."""
    left = list(b)
    miss = []
    for p in a:
        for k, q in enumerate(left):
            if abs(p[0] - q[0]) <= tol and abs(p[1] - q[1]) <= tol:
                del left[k]
                break
        else:
            miss.append(p)
    return miss


def main():
    pcb = sys.argv[sys.argv.index("--pcb") + 1] if "--pcb" in sys.argv else PCB
    outputs = sys.argv[sys.argv.index("--outputs") + 1] if "--outputs" in sys.argv else OUTPUTS
    B = read_board(pcb)
    pads, vias, tracks, arcs = B["pads"], B["vias"], B["tracks"], B["arcs"]
    rep = {}

    # layer names in stack order
    names = {}
    for lid in COPPER_IDS:
        m = re.search(r"\|LAYER%dNAME=([^|]*)" % lid, B["board"])
        names[LAYER[lid]] = m.group(1) if m else None
    order = []
    lid = 1
    while lid:
        order.append(names[LAYER[lid]])
        m = re.search(r"\|LAYER%dNEXT=(\d+)" % lid, B["board"])
        lid = int(m.group(1)) if m else 0
    rep["layer_order"] = order

    # vias by span/geometry
    geo = Counter((v["span"], round(v["size"], 4), round(v["hole"], 4)) for v in vias)
    rep["via_geometry"] = [dict(span="%s-%s" % k[0], size=k[1], hole=k[2], count=c) for k, c in sorted(geo.items(), key=lambda kv: STACK.index(kv[0][0][0]))]
    rep["via_total"] = len(vias)

    # stacked sites
    def key(v):
        return (round(v["x"], 3), round(v["y"], 3))
    by_span = defaultdict(set)
    for v in vias:
        by_span[v["span"]].add(key(v))
    s23 = by_span[("L2-GND", "L3-SIG")]
    s34 = by_span[("L3-SIG", "L4-SIG")]
    s45 = by_span[("L4-SIG", "L5-VCC3V3")]
    s12 = by_span[("Top", "L2-GND")]
    s56 = by_span[("L5-VCC3V3", "Bottom")]
    l2l5 = s23 & s34 & s45
    rep["stacked_L2_L5_sites"] = len(l2l5)
    rep["stacked_L2_L5_full_top_bottom"] = len(l2l5 & s12 & s56)
    hdi_sites = set()
    for v in vias:
        if v["span"] != ("Top", "Bottom"):
            hdi_sites.add(key(v))
    rep["physical_hdi_sites"] = len(hdi_sites)
    # any exact coincidence with a through via?
    rep["hdi_sites_on_through_vias"] = len(hdi_sites & by_span[("Top", "Bottom")])

    # drill files vs board
    drills = {}
    for ext in ["TXT", "TX3", "TX6", "TX7", "TX9", "TX10"]:
        hits = excellon_hits(os.path.join(outputs, "%s-RoundHoles.%s" % (BASE, ext)))
        drills[ext] = {t: len(h) for t, h in hits.items()}
        if ext in DRILL_FILE_SPAN:
            span = DRILL_FILE_SPAN[ext]
            board_xy = [(v["x"], v["y"]) for v in vias if v["span"] == span]
            file_xy = [xy for h in hits.values() for xy in h]
            rep.setdefault("drill_vs_board", {})[ext] = dict(file=len(file_xy), board=len(board_xy),
                                                             board_not_in_file=len(tol_diff(board_xy, file_xy)),
                                                             file_not_on_board=len(tol_diff(file_xy, board_xy)))
        else:
            thru = [(v["x"], v["y"]) for v in vias if v["span"] == ("Top", "Bottom")]
            slot_xy = [(p["x"], p["y"]) for p in pads if p["hole"] > 0 and p["ref"] == "X1" and p["pad"].startswith("MS")]
            ph = [(p["x"], p["y"]) for p in pads if p["hole"] > 0 and (p["x"], p["y"]) not in slot_xy]
            file_xy = [xy for h in hits.values() for xy in h]
            rep.setdefault("drill_vs_board", {})[ext] = dict(file=len(file_xy), board_vias=len(thru), board_round_pad_holes=len(ph),
                                                             board_not_in_file=len(tol_diff(thru + ph, file_xy)),
                                                             file_not_on_board=len(tol_diff(file_xy, thru + ph)))
    rep["drill_hits_per_tool"] = drills

    # plated pad holes
    holes = Counter((round(p["hole"], 4), p["ref"]) for p in pads if p["hole"] > 0)
    rep["pad_holes"] = [dict(hole=k[0], ref=k[1], count=c) for k, c in sorted(holes.items(), key=lambda kv: (kv[0][0], str(kv[0][1])))]

    # widths
    routed = [t for t in tracks if t["poly"] == -1]
    rep["track_min_width_routed"] = round(min(t["width"] for t in routed), 4)
    rep["track_width_hist"] = {str(round(k, 4)): c for k, c in sorted(Counter(round(t["width"], 4) for t in routed).items())[:8]}
    rep["track_min_width_by_layer"] = {L: round(min((t["width"] for t in routed if t["layer"] == L), default=0), 4) for L in STACK}
    rep["polygon_tracks"] = sum(1 for t in tracks if t["poly"] != -1)
    rep["arc_min_width"] = round(min((a["width"] for a in arcs if a["poly"] == -1), default=0), 4)

    # spacing: routed tracks vs other-net tracks / vias / pads on the same layer
    grid = 1.0
    def cells(xa, ya, xb, yb, pad):
        for gx in range(int((min(xa, xb) - pad) // grid), int((max(xa, xb) + pad) // grid) + 1):
            for gy in range(int((min(ya, yb) - pad) // grid), int((max(ya, yb) + pad) // grid) + 1):
                yield gx, gy
    best = (9.0, None)
    for L in STACK:
        objs = []
        for t in routed:
            if t["layer"] == L:
                objs.append(("track", t))
        for v in vias:
            i0, i1 = STACK.index(v["span"][0]), STACK.index(v["span"][1])
            if i0 <= STACK.index(L) <= i1:
                objs.append(("via", v))
        for p in pads:
            if pad_on_layer(p, L):
                q = pad_view(p, L)
                if q["sx"] > 0:
                    objs.append(("pad", q))
        idx = defaultdict(list)
        for n, (kind, o) in enumerate(objs):
            if kind == "track":
                bb = (o["x1"], o["y1"], o["x2"], o["y2"], o["width"] / 2 + 0.3)
            elif kind == "via":
                bb = (o["x"], o["y"], o["x"], o["y"], o["size"] / 2 + 0.3)
            else:
                rr = max(o["sx"], o["sy"]) / 2 + 0.3
                bb = (o["x"], o["y"], o["x"], o["y"], rr)
            for c in cells(*bb):
                idx[c].append(n)
        for n, (kind, t) in enumerate(objs):
            if kind != "track":
                continue
            seen = set()
            for c in cells(t["x1"], t["y1"], t["x2"], t["y2"], t["width"] / 2 + 0.3):
                for m in idx[c]:
                    if m == n or m in seen:
                        continue
                    seen.add(m)
                    k2, o = objs[m]
                    if o["net"] is not None and o["net"] == t["net"]:
                        continue
                    if k2 == "track":
                        if m < n:
                            continue
                        d = seg_seg_dist((t["x1"], t["y1"], t["x2"], t["y2"]), (o["x1"], o["y1"], o["x2"], o["y2"])) - t["width"] / 2 - o["width"] / 2
                    elif k2 == "via":
                        d = seg_point_dist(t["x1"], t["y1"], t["x2"], t["y2"], o["x"], o["y"]) - t["width"] / 2 - o["size"] / 2
                    else:
                        d = seg_pad_dist(t, o) - t["width"] / 2
                    if d < best[0]:
                        best = (d, dict(layer=L, a=t["net"], b=o["net"], kind=k2, ref=o.get("ref"), pad=o.get("pad")))
    rep["min_spacing_track_to_other_copper"] = dict(gap=round(best[0], 4), where=best[1])
    clear = [dict(name=r.get("NAME"), gap=r.get("GAP"), scope1=r.get("SCOPE1EXPRESSION"), scope2=r.get("SCOPE2EXPRESSION"), enabled=r.get("ENABLED"))
             for r in B["rules"] if r.get("RULEKIND") == "Clearance"]
    rep["clearance_rules"] = clear

    # USB pair
    usb = [t for t in routed if t["net"] in ("USB_D_P", "USB_D_N")]
    rep["usb_widths"] = {L: sorted({round(t["width"], 4) for t in usb if t["layer"] == L}) for L in STACK if any(t["layer"] == L for t in usb)}
    gaps = []
    for a in usb:
        if a["net"] != "USB_D_P":
            continue
        for b in usb:
            if b["net"] != "USB_D_N" or b["layer"] != a["layer"]:
                continue
            va = (a["x2"] - a["x1"], a["y2"] - a["y1"])
            vb = (b["x2"] - b["x1"], b["y2"] - b["y1"])
            la, lb = math.hypot(*va), math.hypot(*vb)
            if la < 0.2 or lb < 0.2:
                continue
            if abs(va[0] * vb[1] - va[1] * vb[0]) / (la * lb) > 0.01:
                continue
            d = seg_seg_dist((a["x1"], a["y1"], a["x2"], a["y2"]), (b["x1"], b["y1"], b["x2"], b["y2"]))
            if d < 1.0:
                gaps.append(dict(layer=a["layer"], gap=round(d - a["width"] / 2 - b["width"] / 2, 4), len=round(min(la, lb), 3)))
    rep["usb_parallel_gaps"] = sorted({(g["layer"], g["gap"]) for g in gaps})
    rep["usb_coupled_length_by_gap"] = {"%s %.4f" % k: round(sum(g["len"] for g in gaps if (g["layer"], g["gap"]) == k), 3) for k in {(g["layer"], g["gap"]) for g in gaps}}
    rep["usb_track_length"] = {n: round(sum(math.hypot(t["x2"] - t["x1"], t["y2"] - t["y1"]) for t in usb if t["net"] == n), 3) for n in ("USB_D_P", "USB_D_N")}
    rep["usb_vias"] = [dict(net=v["net"], span="%s-%s" % v["span"]) for v in vias if v["net"] in ("USB_D_P", "USB_D_N")]

    # via-in-pad
    vip = []
    vip_vias = {}       # id(via) -> via, for every via whose land overlaps an SMD pad
    vip_site_of = {}    # (side, ref, pad, x, y) -> stacking key of that via
    for v in vias:
        r = v["size"] / 2
        for L in (v["span"][0], v["span"][1]):
            if L not in ("Top", "Bottom"):
                continue
            for p in pads:
                if p["layer"] != L or p["hole"] > 0 or p["sx"] <= 0:
                    continue
                p = pad_view(p, L)
                if abs(p["x"] - v["x"]) > 3 or abs(p["y"] - v["y"]) > 3:
                    continue
                d = pad_point_dist(p, v["x"], v["y"])
                if d < r - 1e-4:
                    depth = pad_inner_depth(p, v["x"], v["y"])
                    vip_vias[id(v)] = v
                    vip_site_of[(L, p["ref"], p["pad"], round(v["x"], 4), round(v["y"], 4))] = key(v)
                    vip.append(dict(ref=p["ref"], pad=p["pad"], pad_net=p["net"], via_net=v["net"], layer=L,
                                    span="%s-%s" % v["span"], via_x=round(v["x"], 4), via_y=round(v["y"], 4),
                                    via_land=round(v["size"], 4), hole=round(v["hole"], 4),
                                    pad_shape={1: "round", 2: "rect", 3: "octagon"}.get(p["shape"], str(p["shape"])),
                                    pad_size="%.3f x %.3f" % (p["sx"], p["sy"]),
                                    hole_centre_in_pad=depth > 0,
                                    land_inside_pad=depth >= r - 1e-4,
                                    hole_inside_pad=depth >= v["hole"] / 2 - 1e-4,
                                    hole_touches_pad=d < v["hole"] / 2 - 1e-4,
                                    overlap=round(r - d, 4)))
    rep["via_in_pad"] = sorted(vip, key=lambda e: (str(e["ref"]), e["pad"], e["span"]))

    # pad shape census for SMD pads that carry vias (non rect/round would be measured as rect)
    rep["smd_pad_shapes"] = dict(Counter(p["shape"] for p in pads if p["hole"] == 0))

    rep["via_in_pad_summary"] = dict(
        entries=len(vip),
        via_sites=len({(e["via_x"], e["via_y"]) for e in vip}),
        hole_touches_pad=len({(e["via_x"], e["via_y"]) for e in vip if e["hole_touches_pad"]}),
        land_only=len({(e["via_x"], e["via_y"]) for e in vip} - {(e["via_x"], e["via_y"]) for e in vip if e["hole_touches_pad"]}),
        by_span=dict(Counter(e["span"] for e in {(e["via_x"], e["via_y"]): e for e in vip}.values())),
        by_side=dict(Counter(e["layer"] for e in vip)))
    # ---- Rev 2 additions (see the module docstring) ------------------------------
    # adjacent spans sharing an XY: a microvia sitting on (or carrying) the next drill
    rep["via_stacks"] = dict(
        top_l2_on_l2_l3=len(s12 & s23),
        l2_l3_on_l3_l4_buried=len(s23 & s34),
        l3_l4_buried_with_l4_l5=len(s34 & s45),
        l4_l5_under_l5_bottom=len(s45 & s56))

    # every span present at each via-in-pad XY: a stacked column under the in-pad microvia
    span_order = [("Top", "L2-GND"), ("L2-GND", "L3-SIG"), ("L3-SIG", "L4-SIG"),
                  ("L4-SIG", "L5-VCC3V3"), ("L5-VCC3V3", "Bottom"), ("Top", "Bottom")]
    full = l2l5 & s12 & s56
    columns = []
    for e in rep["via_in_pad"]:
        k = vip_site_of[(e["layer"], e["ref"], e["pad"], e["via_x"], e["via_y"])]
        columns.append(dict(ref=e["ref"], pad=e["pad"], via_net=e["via_net"], layer=e["layer"], span=e["span"],
                            via_x=e["via_x"], via_y=e["via_y"],
                            spans_at_xy=["%s-%s" % s for s in span_order if k in by_span[s]],
                            l2_l5_column=k in l2l5, full_top_bottom=k in full))
    rep["via_in_pad_columns"] = columns
    rep["via_in_pad_columns_summary"] = dict(
        l2_l5_column_sites=sum(1 for c in columns if c["l2_l5_column"]),
        full_top_bottom_sites=sum(1 for c in columns if c["full_top_bottom"]),
        through_vias_in_pads=sum(1 for c in columns if c["span"] == "Top-Bottom"))

    # X1's plated holes and slots: lands per layer, straight from the pad records
    shape_name = {1: "round", 2: "rect", 3: "octagon"}
    rep["x1_hole_pads"] = [
        dict(pad=p["pad"], x=round(p["x"], 4), y=round(p["y"], 4), hole=round(p["hole"], 4),
             **{L.lower(): "%.3f x %.3f %s" % (p["size"][L][0], p["size"][L][1], shape_name.get(p["size"][L][2], p["size"][L][2]))
                for L in ("Top", "Mid", "Bottom")})
        for p in sorted(pads, key=lambda p: p["pad"]) if p["ref"] == "X1" and p["hole"] > 0]

    # drill and mask rules the notes quote
    rep["drill_mask_rules"] = [
        {k.lower(): r.get(k) for k in ("NAME", "RULEKIND", "SCOPE1EXPRESSION", "GAP", "EXPANSION", "MINIMUMRING",
                                       "ISTENTINGTOP", "ISTENTINGBOTTOM", "ALLOWSTACKEDMICROVIAS", "ENABLED") if r.get(k) is not None}
        for r in B["rules"]
        if r.get("RULEKIND") in ("SolderMaskExpansion", "MinimumSolderMaskSliver", "HoleToHoleClearance", "MinimumAnnularRing")]

    # solder-mask openings (exported GTS/GBS) against vias.  A through via whose land an
    # opening overlaps or touches (tangent within 0.1 um) is listed with the opening's owner
    # pad, the hole margin (opening edge to drilled hole edge) and the copper gap from the
    # land to the nearest SMD pad.
    tent = {}
    smd = [p for p in pads if p["hole"] == 0 and p["sx"] > 0 and p["layer"] in ("Top", "Bottom")]
    for side, ext in (("Top", "GTS"), ("Bottom", "GBS")):
        fl = gerber_flashes(os.path.join(outputs, "%s.%s" % (BASE, ext)))
        centred = Counter()
        for v in vias:
            if side not in v["span"] or id(v) in vip_vias:
                continue
            if any(abs(f[0] - v["x"]) < 0.005 and abs(f[1] - v["y"]) < 0.005 for f in fl):
                centred["%s-%s" % v["span"]] += 1
        over, hole_reached = [], 0
        for v in vias:
            if v["span"] != ("Top", "Bottom"):
                continue
            near = [f for f in fl if abs(f[0] - v["x"]) < 3 and abs(f[1] - v["y"]) < 3]
            if not near:
                continue
            f = min(near, key=lambda f: opening_dist(f, v["x"], v["y"]))
            d = opening_dist(f, v["x"], v["y"])
            if d < v["hole"] / 2 - 1e-4:
                hole_reached += 1
            if d > v["size"] / 2 + 1e-4:
                continue
            owner = [p for p in pads if pad_on_layer(p, side) and abs(p["x"] - f[0]) < 0.005 and abs(p["y"] - f[1]) < 0.005]
            gap, cp = min(((pad_point_dist(pad_view(p, side), v["x"], v["y"]) - v["size"] / 2, p)
                           for p in smd if p["layer"] == side and abs(p["x"] - v["x"]) < 3 and abs(p["y"] - v["y"]) < 3),
                          key=lambda t: t[0])
            over.append(dict(x=round(v["x"], 4), y=round(v["y"], 4), via_net=v["net"],
                             opening_pad="%s-%s" % (owner[0]["ref"], owner[0]["pad"]) if owner else None,
                             opening_pad_net=owner[0]["net"] if owner else None,
                             contact="tangent" if abs(d - v["size"] / 2) <= 1e-4 else "overlap",
                             opening_edge_to_centre=round(d, 4), hole_margin=round(d - v["hole"] / 2, 4),
                             nearest_smd_pad="%s-%s" % (cp["ref"], cp["pad"]), copper_gap=round(max(gap, 0.0), 4),
                             opening_modelled_exactly=f[3]))
        tent[side] = dict(openings=len(fl), openings_not_exact=sum(1 for f in fl if not f[3]),
                          openings_centred_on_non_vip_vias=dict(centred),
                          through_via_holes_reached=hole_reached,
                          through_via_lands_reached=sorted(over, key=lambda e: (e["hole_margin"], e["x"], e["y"])))
    reached = [e for s in ("Top", "Bottom") for e in tent[s]["through_via_lands_reached"]]
    tent["through_vias_with_land_reached"] = len({(e["x"], e["y"]) for e in reached})
    tent["through_vias_with_land_overlapped"] = len({(e["x"], e["y"]) for e in reached if e["contact"] == "overlap"})
    tent["all_same_net"] = all(e["opening_pad_net"] == e["via_net"] for s in ("Top", "Bottom")
                               for e in tent[s]["through_via_lands_reached"])
    rep["mask_over_through_vias"] = tent

    write = pcb == PCB and outputs == OUTPUTS
    out = os.path.join(HERE, "fab_facts.json") if write else os.devnull
    json.dump(rep, open(out, "w", encoding="utf-8"), indent=1, default=str)
    for k, v in rep.items():
        if k in ("via_in_pad",):
            print(k)
            for e in v:
                print("  ", e)
        else:
            print(k, "=", json.dumps(v, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
