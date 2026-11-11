# -*- coding: utf-8 -*-
"""Measure the fabrication facts of the Asar Feather board straight from the saved
PcbDoc, the exported NC drill files and the solder-mask Gerbers, for the PCBWay
fab notes.  Read-only.  Adapted from Zulu_A7_Fab_B/tools/fab_facts.py.

    python tools/fab_facts.py            # prints a report, writes tools/fab_facts.json

Record offsets (as Zulu_Altium_VS_Code/tools/route_inputs.py):
  Pads6   body: layer@0 net@3 comp@7 x@13 y@17 sx@21 sy@25 hole@45 shape@49..51 rot(double)@52
  Vias6   body: net@3 x@13 y@17 size@21 hole@25 start-layer@29 end-layer@30
  Tracks6 body: layer@0 net@3 polygon@5 comp@7 x1@13 y1@17 x2@21 y2@25 width@29
Units 1/10000 mil (2.54e-6 mm), board origin, y up.

What it does NOT measure: the solid plane pours (L2 GND, L5 VCC3V3) are
ShapeBasedRegions, not tracks, so plane-web widths and hole-to-plane distances
are left to Altium DRC (the clearance rules pass).
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
PROJECT = os.path.join(ROOT, "Asar_feather.PrjPcb")
PCB = os.path.join(PROJECT, "asar_feather.PcbDoc")
OUTPUTS = os.path.join(PROJECT, "Project Outputs for asar_feather")
BASE = "asar_feather"
U = 2.54e-6
LAYER = {1: "Top", 4: "L2-GND", 2: "L3-SIG", 3: "L4-SIG", 5: "L5-VCC3V3", 32: "Bottom", 74: "Multi"}
STACK = ["Top", "L2-GND", "L3-SIG", "L4-SIG", "L5-VCC3V3", "Bottom"]
COPPER_IDS = (1, 4, 2, 3, 5, 32)
THRU = ("Top", "Bottom")
T12, T23, T34, T45, T56 = (("Top", "L2-GND"), ("L2-GND", "L3-SIG"), ("L3-SIG", "L4-SIG"),
                           ("L4-SIG", "L5-VCC3V3"), ("L5-VCC3V3", "Bottom"))
SPAN_SHORT = {T12: "Top-L2", T23: "L2-L3", T34: "L3-L4", T45: "L4-L5", T56: "L5-Bot", THRU: "Top-Bot"}
DRILL_FILE_SPAN = {
    "RoundHoles-Plated.TX3": T34,
    "RoundHoles-Plated.TX6": T12,
    "RoundHoles-Plated.TX7": T23,
    "RoundHoles-Plated.TX9": T45,
    "RoundHoles-Plated.TX10": T56,
}
CENTRE_TOL = 0.005  # mm: a via this close to a ball centre is "centred"


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
        arcs.append(dict(layer=LAYER[b[0]], width=i32(b, 41) * U, poly=struct.unpack("<h", b[5:7])[0]))
    rules = kvs(f, "Rules6/Data", "RULEKIND=")
    board = f.openstream("Board6/Data").read().decode("latin-1")
    f.close()
    return dict(pads=pads, vias=vias, tracks=tracks, arcs=arcs, rules=rules, board=board)


# ---- geometry ---------------------------------------------------------------
def pad_frame(p, x, y):
    a = math.radians(-p["rot"])
    dx, dy = x - p["x"], y - p["y"]
    return dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a)


def pad_core(p):
    """(core half-x, core half-y, radius): round (1) -> obround/circle, others -> rect."""
    hx, hy = p["sx"] / 2, p["sy"] / 2
    if p["shape"] == 1:
        r = min(hx, hy)
        return hx - r, hy - r, r
    return hx, hy, 0.0


def point_rect_dist(px, py, hx, hy):
    return math.hypot(max(abs(px) - hx, 0.0), max(abs(py) - hy, 0.0))


def pad_point_dist(p, x, y):
    hx, hy, r = pad_core(p)
    px, py = pad_frame(p, x, y)
    return max(point_rect_dist(px, py, hx, hy) - r, 0.0)


def pad_inner_depth(p, x, y):
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
    hx, hy, r = pad_core(p)
    ax, ay = pad_frame(p, t["x1"], t["y1"])
    bx, by = pad_frame(p, t["x2"], t["y2"])
    corners = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
    edges = [(*corners[k], *corners[(k + 1) % 4]) for k in range(4)]
    if point_rect_dist(ax, ay, hx, hy) == 0 or point_rect_dist(bx, by, hx, hy) == 0:
        return 0.0
    d = min(seg_seg_dist((ax, ay, bx, by), e) for e in edges)
    return max(d - r, 0.0)


def pad_on_layer(p, layer):
    return p["layer"] == layer or p["layer"] == "Multi"


def pad_view(p, layer):
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


def span_has(span, layer):
    return STACK.index(span[0]) <= STACK.index(layer) <= STACK.index(span[1])


# ---- Excellon ---------------------------------------------------------------
def coord(s):
    neg = s.startswith("-")
    v = int(s.lstrip("+-").ljust(8, "0")) / 10000.0
    return -v if neg else v


def excellon(path):
    """({tool: diameter}, {tool: [(x, y) or (x1, y1, x2, y2) for G85 slots]})."""
    tools, hits = {}, defaultdict(list)
    tool = None
    x = y = None
    in_header = True
    with open(path, encoding="ascii") as handle:
        for raw in handle:
            line = raw.strip()
            if in_header:
                m = re.fullmatch(r"T(\d+)F\d+S\d+C(\d+\.\d+)", line)
                if m:
                    tools[m.group(1)] = float(m.group(2))
                if line == "%":
                    in_header = False
                continue
            m = re.fullmatch(r"T(\d+)", line)
            if m:
                tool = m.group(1)
                continue
            m = re.fullmatch(r"(?:X(-?\d+))?(?:Y(-?\d+))?(?:G85(?:X(-?\d+))?(?:Y(-?\d+))?)?", line)
            if m and (m.group(1) or m.group(2)):
                if m.group(1):
                    x = coord(m.group(1))
                if m.group(2):
                    y = coord(m.group(2))
                if "G85" in line:
                    x2 = coord(m.group(3)) if m.group(3) else x
                    y2 = coord(m.group(4)) if m.group(4) else y
                    hits[tool].append((x, y, x2, y2))
                else:
                    hits[tool].append((x, y))
    return tools, dict(hits)


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


# ---- Gerber mask flashes ----------------------------------------------------
def mask_openings(path):
    """Flashed openings of a mask Gerber as dicts (x, y, hx, hy, r, rot) in mm."""
    text = open(path, encoding="ascii").read()
    if "%MOMM*%" not in text or "%FSLAX44Y44*%" not in text:
        raise ValueError("%s is not metric 4.4" % path)
    if "G36" in text or "D01*" in text:
        raise ValueError("%s has regions or draws; only flashes are handled" % path)
    ap = {}
    for m in re.finditer(r"%ADD(\d+)([RCO]),([\d.]+)(?:X([\d.]+))?\*%", text):
        d, kind, a, b = int(m.group(1)), m.group(2), float(m.group(3)), float(m.group(4) or m.group(3))
        if kind == "C":
            ap[d] = (0.0, 0.0, a / 2)
        elif kind == "R":
            ap[d] = (a / 2, b / 2, 0.0)
        else:
            r = min(a, b) / 2
            ap[d] = (a / 2 - r, b / 2 - r, r)
    for m in re.finditer(r"AMPARAMS\|DCode=(\d+)\|XSize=([\d.]+)mm\|YSize=([\d.]+)mm\|CornerRadius=([\d.]+)mm"
                         r"\|.*?Rotation=([\d.]+)\|", text):
        d, sx, sy, cr, rot = int(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4)), float(m.group(5))
        if rot % 90:
            raise ValueError("macro D%d rotation %s not handled" % (d, rot))
        if rot % 180:
            sx, sy = sy, sx
        ap[d] = (sx / 2 - cr, sy / 2 - cr, cr)
    out = []
    cur = None
    x = y = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("%", "G04", "21,", "1,")) or line in ("G01*", "G75*", "G71*", "G02*", "M02*"):
            continue
        m = re.fullmatch(r"(?:G54)?D(\d+)\*", line)
        if m and int(m.group(1)) >= 10:
            cur = int(m.group(1))
            continue
        m = re.fullmatch(r"(?:X(-?\d+))?(?:Y(-?\d+))?D0([123])\*", line)
        if not m:
            raise ValueError("%s: unexpected statement %r" % (os.path.basename(path), line))
        if m.group(1):
            x = int(m.group(1))
        if m.group(2):
            y = int(m.group(2))
        if m.group(3) == "1":
            raise ValueError("%s: draw found" % os.path.basename(path))
        if m.group(3) == "3":
            hx, hy, r = ap[cur]
            out.append(dict(x=x / 10000, y=y / 10000, hx=hx, hy=hy, r=r, d=cur))
    return out


def opening_point_dist(o, x, y):
    return max(point_rect_dist(x - o["x"], y - o["y"], o["hx"], o["hy"]) - o["r"], 0.0)


def measure(pcb=PCB):
    B = read_board(pcb)
    pads, vias, tracks, arcs = B["pads"], B["vias"], B["tracks"], B["arcs"]
    rep = {"counts": dict(pads=len(pads), vias=len(vias), tracks=len(tracks), arcs=len(arcs))}

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
    rep["via_geometry"] = [dict(span=SPAN_SHORT[k[0]], land=k[1], hole=k[2], count=c)
                           for k, c in sorted(geo.items(), key=lambda kv: (STACK.index(kv[0][0][0]), -STACK.index(kv[0][0][1]), kv[0][2], kv[0][1]))]
    rep["via_total"] = len(vias)
    lasers = [v for v in vias if v["span"] in (T12, T23, T45, T56)]
    rep["laser_total"] = len(lasers)
    rep["laser_by_hole"] = {str(k): c for k, c in sorted(Counter(round(v["hole"], 4) for v in lasers).items())}
    rep["buried_total"] = sum(1 for v in vias if v["span"] == T34)
    rep["through_total"] = sum(1 for v in vias if v["span"] == THRU)

    # stacked sites
    def key(v):
        return (round(v["x"], 3), round(v["y"], 3))
    by_span = defaultdict(set)
    for v in vias:
        by_span[v["span"]].add(key(v))
    s12, s23, s34, s45, s56 = (by_span[s] for s in (T12, T23, T34, T45, T56))
    l2l5 = s23 & s34 & s45
    rep["stacked"] = dict(
        L2_L5_sites=len(l2l5),
        L2_L5_full_top_bottom=len(l2l5 & s12 & s56),
        L2_L5_plus_top=len((l2l5 & s12) - s56),
        L2_L5_plus_bottom=len((l2l5 & s56) - s12),
        top_l2_on_l2_l3=len(s12 & s23),
        l2_l3_on_buried=len(s23 & s34),
        l4_l5_on_buried=len(s45 & s34),
        l5_bot_on_l4_l5=len(s56 & s45),
        top_l3_on_buried=len(s12 & s23 & s34),
        hdi_sites=len(set().union(s12, s23, s34, s45, s56)),
        hdi_sites_on_through=len(set().union(s12, s23, s34, s45, s56) & by_span[THRU]))
    # columns that mix 0.10 and 0.15 lasers
    holes_at = defaultdict(set)
    for v in lasers:
        holes_at[key(v)].add(round(v["hole"], 3))
    hole_of = {(key(v), v["span"]): round(v["hole"], 2) for v in vias}
    rep["stacked"]["l2_l3_on_buried_by_laser_hole"] = dict(Counter(str(hole_of[(k, T23)]) for k in s23 & s34))
    rep["stacked"]["l4_l5_on_buried_by_laser_hole"] = dict(Counter(str(hole_of[(k, T45)]) for k in s45 & s34))
    rep["stacked"]["top_l2_on_l2_l3_by_holes"] = dict(Counter("%s/%s" % (hole_of[(k, T12)], hole_of[(k, T23)]) for k in s12 & s23))
    rep["stacked"]["l4_l5_on_l5_bot_by_holes"] = dict(Counter("%s/%s" % (hole_of[(k, T45)], hole_of[(k, T56)]) for k in s45 & s56))
    rep["stacked"]["max_stack_depth_sites"] = dict(Counter(sum(1 for s in (s12, s23, s34, s45, s56) if k in s) for k in set().union(s12, s23, s34, s45, s56)))
    rep["buried_non_027"] = [dict(net=v["net"], x=round(v["x"], 3), y=round(v["y"], 3), land=round(v["size"], 3), hole=round(v["hole"], 3))
                             for v in vias if v["span"] == T34 and abs(v["size"] - 0.27) > 0.002]
    rep["stacked"]["full_columns_mixed_laser_sizes"] = sum(1 for k in (l2l5 & s12 & s56) if len(holes_at[k]) > 1)

    # ---- drill files vs board, one-to-one per tool --------------------------
    def nearest_size(h, sizes):
        return min(sizes, key=lambda s: abs(s - h))
    dvb = {}
    hits_per_tool = {}
    for suffix, span in DRILL_FILE_SPAN.items():
        tools, hits = excellon(os.path.join(OUTPUTS, "%s-%s" % (BASE, suffix)))
        hits_per_tool[suffix] = {t: dict(size=tools[t], hits=len(h)) for t, h in hits.items()}
        rows = {}
        for t, h in hits.items():
            board_xy = [(v["x"], v["y"]) for v in vias if v["span"] == span and abs(v["hole"] - tools[t]) < 0.002]
            rows["T" + t] = dict(size=tools[t], file=len(h), board=len(board_xy),
                                 board_not_in_file=len(tol_diff(board_xy, h)), file_not_on_board=len(tol_diff(h, board_xy)))
        dvb[suffix] = rows
    # plated round Top-Bottom: through vias + 1.0 mm plated pad holes
    pl_tools, pl_hits = excellon(os.path.join(OUTPUTS, "%s-RoundHoles-Plated.TXT" % BASE))
    np_tools, np_hits = excellon(os.path.join(OUTPUTS, "%s-RoundHoles-NonPlated.TXT" % BASE))
    sl_tools, sl_hits = excellon(os.path.join(OUTPUTS, "%s-SlotHoles-Plated.TXT" % BASE))
    hits_per_tool["RoundHoles-Plated.TXT"] = {t: dict(size=pl_tools[t], hits=len(h)) for t, h in pl_hits.items()}
    hits_per_tool["RoundHoles-NonPlated.TXT"] = {t: dict(size=np_tools[t], hits=len(h)) for t, h in np_hits.items()}
    hits_per_tool["SlotHoles-Plated.TXT"] = {t: dict(size=sl_tools[t], hits=len(h)) for t, h in sl_hits.items()}
    hole_pads = [p for p in pads if p["hole"] > 0]
    np_sizes = sorted(set(np_tools.values()))
    sl_size = sorted(set(sl_tools.values()))
    npth_pads = [p for p in hole_pads if any(abs(p["hole"] - s) < 0.002 for s in np_sizes)]
    slot_pads = [p for p in hole_pads if p not in npth_pads and any(abs(p["hole"] - s) < 0.002 for s in sl_size)
                 and p["ref"] == "X1"]
    round_pads = [p for p in hole_pads if p not in npth_pads and p not in slot_pads]
    for t, h in pl_hits.items():
        size = pl_tools[t]
        bxy = [(v["x"], v["y"]) for v in vias if v["span"] == THRU and abs(v["hole"] - size) < 0.002]
        bxy += [(p["x"], p["y"]) for p in round_pads if abs(p["hole"] - size) < 0.002]
        dvb.setdefault("RoundHoles-Plated.TXT", {})["T" + t] = dict(size=size, file=len(h), board=len(bxy),
                                                                    board_not_in_file=len(tol_diff(bxy, h)), file_not_on_board=len(tol_diff(h, bxy)))
    for t, h in np_hits.items():
        size = np_tools[t]
        bxy = [(p["x"], p["y"]) for p in npth_pads if abs(p["hole"] - size) < 0.002]
        dvb.setdefault("RoundHoles-NonPlated.TXT", {})["T" + t] = dict(size=size, file=len(h), board=len(bxy),
                                                                       board_not_in_file=len(tol_diff(bxy, h)), file_not_on_board=len(tol_diff(h, bxy)))
    for t, h in sl_hits.items():
        centres = [((a + c) / 2, (b + d) / 2) for a, b, c, d in h]
        bxy = [(p["x"], p["y"]) for p in slot_pads]
        dvb.setdefault("SlotHoles-Plated.TXT", {})["T" + t] = dict(size=sl_tools[t], file=len(h), board=len(bxy),
                                                                   board_not_in_file=len(tol_diff(bxy, centres)), file_not_on_board=len(tol_diff(centres, bxy)))
    rep["drill_vs_board"] = dvb
    rep["drill_hits_per_tool"] = hits_per_tool
    slots = []
    for t, h in sl_hits.items():
        for a, b, c, d in h:
            route = math.hypot(c - a, d - b)
            cx, cy = (a + c) / 2, (b + d) / 2
            p = min(slot_pads, key=lambda q: math.hypot(q["x"] - cx, q["y"] - cy))
            slots.append(dict(ref=p["ref"], pad=p["pad"], net=p["net"], x=round(cx, 4), y=round(cy, 4), tool=sl_tools[t],
                              route=round(route, 4), length=round(route + sl_tools[t], 4),
                              orientation="horizontal" if abs(d - b) < 1e-4 else "vertical",
                              land_top="%.2f x %.2f" % tuple(sorted(pad_view(p, "Top")[k] for k in ("sx", "sy"))),
                              land_inner="%.2f x %.2f" % tuple(sorted(pad_view(p, "L3-SIG")[k] for k in ("sx", "sy")))))
    rep["plated_slots"] = sorted(slots, key=lambda s: s["pad"])
    rep["npth"] = [dict(ref=p["ref"], pad=p["pad"], hole=round(p["hole"], 4), x=round(p["x"], 4), y=round(p["y"], 4),
                        land_top=round(pad_view(p, "Top")["sx"], 4)) for p in sorted(npth_pads, key=lambda q: (q["hole"], q["x"], q["y"]))]
    rep["pad_holes"] = [dict(hole=k[0], ref=k[1], land=k[2], count=c) for k, c in
                        sorted(Counter((round(p["hole"], 4), p["ref"], round(pad_view(p, "Top")["sx"], 3)) for p in round_pads).items())]

    # ---- widths and spacing -------------------------------------------------
    routed = [t for t in tracks if t["poly"] == -1]
    rep["track_min_width_routed"] = round(min(t["width"] for t in routed), 4)
    rep["track_width_hist"] = {str(round(k, 4)): c for k, c in sorted(Counter(round(t["width"], 4) for t in routed).items())[:8]}
    rep["track_min_width_by_layer"] = {L: round(min((t["width"] for t in routed if t["layer"] == L), default=0), 4) for L in STACK}
    rep["polygon_tracks"] = sum(1 for t in tracks if t["poly"] != -1)
    rep["arcs_on_copper"] = len(arcs)

    grid = 1.0

    def cells(xa, ya, xb, yb, pad):
        for gx in range(int((min(xa, xb) - pad) // grid), int((max(xa, xb) + pad) // grid) + 1):
            for gy in range(int((min(ya, yb) - pad) // grid), int((max(ya, yb) + pad) // grid) + 1):
                yield gx, gy
    best = (9.0, None)
    best_by_layer = {}
    for L in STACK:
        objs = [("track", t) for t in routed if t["layer"] == L]
        objs += [("via", v) for v in vias if span_has(v["span"], L)]
        objs += [("pad", pad_view(p, L)) for p in pads if pad_on_layer(p, L) and pad_view(p, L)["sx"] > 0]
        idx = defaultdict(list)
        for n, (kind, o) in enumerate(objs):
            if kind == "track":
                bb = (o["x1"], o["y1"], o["x2"], o["y2"], o["width"] / 2 + 0.3)
            elif kind == "via":
                bb = (o["x"], o["y"], o["x"], o["y"], o["size"] / 2 + 0.3)
            else:
                bb = (o["x"], o["y"], o["x"], o["y"], max(o["sx"], o["sy"]) / 2 + 0.3)
            for c in cells(*bb):
                idx[c].append(n)
        lb = (9.0, None)
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
                    if d < lb[0]:
                        lb = (d, dict(layer=L, a=t["net"], b=o["net"], kind=k2, ref=o.get("ref"), pad=o.get("pad")))
        best_by_layer[L] = round(lb[0], 4)
        if lb[0] < best[0]:
            best = lb
    rep["min_spacing_track_to_other_copper"] = dict(gap=round(best[0], 4), where=best[1], by_layer=best_by_layer)
    # enquiry question 7: track to U1 ball land (Top) and track to laser land on L3/L4
    u1_top = [pad_view(p, "Top") for p in pads if p["ref"] == "U1"]
    g7a = 9.0
    n7a = Counter()
    for t in routed:
        if t["layer"] != "Top":
            continue
        for p in u1_top:
            if p["net"] == t["net"] or seg_point_dist(t["x1"], t["y1"], t["x2"], t["y2"], p["x"], p["y"]) > 0.6:
                continue
            d = seg_pad_dist(t, p) - t["width"] / 2
            g7a = min(g7a, d)
            if d < 0.1:
                n7a["%.3f" % d] += 1
    g7b = {}
    for L in ("L3-SIG", "L4-SIG"):
        lv = [v for v in lasers if L in v["span"]]
        idx = defaultdict(list)
        for v in lv:
            idx[(int(v["x"] // grid), int(v["y"] // grid))].append(v)
        best_b = 9.0
        for t in routed:
            if t["layer"] != L:
                continue
            for c in cells(t["x1"], t["y1"], t["x2"], t["y2"], 0.5):
                for v in idx.get(c, ()):
                    if v["net"] == t["net"]:
                        continue
                    best_b = min(best_b, seg_point_dist(t["x1"], t["y1"], t["x2"], t["y2"], v["x"], v["y"]) - t["width"] / 2 - v["size"] / 2)
        g7b[L] = round(best_b, 4)
    rep["track_to_u1_land_min"] = round(g7a, 4)
    rep["track_to_u1_land_under_0p1"] = sum(n7a.values())
    rep["track_to_laser_land_min"] = g7b
    rep["clearance_rules"] = [dict(name=r.get("NAME"), gap=r.get("GAP"), scope1=r.get("SCOPE1EXPRESSION"),
                                   scope2=r.get("SCOPE2EXPRESSION"), enabled=r.get("ENABLED"))
                              for r in B["rules"] if r.get("RULEKIND") == "Clearance"]

    # ---- hole spacing (holes that share a copper layer, coincident stacks excluded)
    holes = [dict(x=v["x"], y=v["y"], r=v["hole"] / 2, span=v["span"], kind=SPAN_SHORT[v["span"]], net=v["net"]) for v in vias]
    holes += [dict(x=p["x"], y=p["y"], r=p["hole"] / 2, span=THRU, kind="pad %s-%s" % (p["ref"], p["pad"]), net=p["net"])
              for p in hole_pads if p not in slot_pads]
    hidx = defaultdict(list)
    for n, h in enumerate(holes):
        hidx[(int(h["x"] // grid), int(h["y"] // grid))].append(n)
    hh = (9.0, None)
    hh_kind = {}
    for n, h in enumerate(holes):
        gx, gy = int(h["x"] // grid), int(h["y"] // grid)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for m in hidx[(gx + dx, gy + dy)]:
                    if m <= n:
                        continue
                    o = holes[m]
                    cd = math.hypot(h["x"] - o["x"], h["y"] - o["y"])
                    if cd < 0.001:
                        continue
                    if STACK.index(h["span"][1]) < STACK.index(o["span"][0]) or STACK.index(o["span"][1]) < STACK.index(h["span"][0]):
                        continue
                    d = cd - h["r"] - o["r"]
                    pair = " / ".join(sorted((h["kind"] if not h["kind"].startswith("pad") else "pad hole",
                                              o["kind"] if not o["kind"].startswith("pad") else "pad hole")))
                    hh_kind[pair] = min(hh_kind.get(pair, 9.0), round(d, 4))
                    if d < hh[0]:
                        hh = (d, dict(a=h["kind"], b=o["kind"], x=round(h["x"], 3), y=round(h["y"], 3)))
    # big pad holes (2.5 mm NPTH, 1.0 mm pins) are wider than the grid search reaches: brute-force every pad hole
    for n, h in enumerate(holes):
        if not h["kind"].startswith("pad"):
            continue
        for m, o in enumerate(holes):
            if m == n:
                continue
            cd = math.hypot(h["x"] - o["x"], h["y"] - o["y"])
            if cd < 0.001:
                continue
            if STACK.index(h["span"][1]) < STACK.index(o["span"][0]) or STACK.index(o["span"][1]) < STACK.index(h["span"][0]):
                continue
            d = cd - h["r"] - o["r"]
            pair = " / ".join(sorted(("pad hole", o["kind"] if not o["kind"].startswith("pad") else "pad hole")))
            hh_kind[pair] = min(hh_kind.get(pair, 9.0), round(d, 4))
            if d < hh[0]:
                hh = (d, dict(a=h["kind"], b=o["kind"], x=round(h["x"], 3), y=round(h["y"], 3)))
    rep["min_hole_to_hole"] = dict(gap=round(hh[0], 4), where=hh[1], by_pair=dict(sorted(hh_kind.items())))

    # hole wall (through / buried / laser) to other-net track or pad copper on a layer it passes (planes excluded)
    def hole_to_copper(sel, label):
        best_h = (9.0, None)
        for L in STACK:
            objs = [t for t in routed if t["layer"] == L]
            idx = defaultdict(list)
            for n, o in enumerate(objs):
                for c in cells(o["x1"], o["y1"], o["x2"], o["y2"], o["width"] / 2 + 0.4):
                    idx[c].append(n)
            for h in sel:
                if not span_has(h["span"], L):
                    continue
                seen = set()
                for m in idx[(int(h["x"] // grid), int(h["y"] // grid))]:
                    if m in seen:
                        continue
                    seen.add(m)
                    o = objs[m]
                    if o["net"] is not None and o["net"] == h["net"]:
                        continue
                    d = seg_point_dist(o["x1"], o["y1"], o["x2"], o["y2"], h["x"], h["y"]) - o["width"] / 2 - h["r"]
                    if d < best_h[0]:
                        best_h = (d, dict(layer=L, hole=h["kind"], net=o["net"], x=round(h["x"], 3), y=round(h["y"], 3)))
        return dict(gap=round(best_h[0], 4), where=best_h[1])
    rep["hole_wall_to_other_net_track"] = {
        "laser": hole_to_copper([h for h in holes if h["span"] in (T12, T23, T45, T56)], "laser"),
        "buried": hole_to_copper([h for h in holes if h["span"] == T34], "buried"),
        "through_via": hole_to_copper([h for h in holes if h["span"] == THRU and not h["kind"].startswith("pad")], "thru"),
    }
    np_holes = [dict(x=p["x"], y=p["y"], r=p["hole"] / 2, span=THRU, kind="NPTH %.2f" % p["hole"], net=None) for p in npth_pads]
    rep["npth_to_track"] = hole_to_copper(np_holes, "npth")
    npv = 9.0
    for h in np_holes:
        for v in vias:
            npv = min(npv, math.hypot(h["x"] - v["x"], h["y"] - v["y"]) - h["r"] - v["size"] / 2)
    rep["npth_to_via_land"] = round(npv, 4)

    # ---- USB pair -----------------------------------------------------------
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
                # overlap length along the direction
                ux, uy = va[0] / la, va[1] / la
                pa = sorted((a["x1"] * ux + a["y1"] * uy, a["x2"] * ux + a["y2"] * uy))
                pb = sorted((b["x1"] * ux + b["y1"] * uy, b["x2"] * ux + b["y2"] * uy))
                ov = min(pa[1], pb[1]) - max(pa[0], pb[0])
                if ov > 0:
                    gaps.append(dict(layer=a["layer"], gap=round(d - a["width"] / 2 - b["width"] / 2, 4), len=round(ov, 3)))
    cl = defaultdict(float)
    for g in gaps:
        cl["%s %.4f" % (g["layer"], g["gap"])] += g["len"]
    rep["usb_coupled_length_by_gap"] = {k: round(v, 3) for k, v in sorted(cl.items())}
    rep["usb_track_length"] = {n: round(sum(math.hypot(t["x2"] - t["x1"], t["y2"] - t["y1"]) for t in usb if t["net"] == n), 3) for n in ("USB_D_P", "USB_D_N")}
    rep["usb_track_length_by_layer"] = {n: {L: round(sum(math.hypot(t["x2"] - t["x1"], t["y2"] - t["y1"]) for t in usb if t["net"] == n and t["layer"] == L), 3)
                                            for L in STACK if any(t["net"] == n and t["layer"] == L for t in usb)} for n in ("USB_D_P", "USB_D_N")}
    rep["usb_vias"] = [dict(net=v["net"], span=SPAN_SHORT[v["span"]], hole=round(v["hole"], 3), x=round(v["x"], 3), y=round(v["y"], 3))
                       for v in vias if v["net"] in ("USB_D_P", "USB_D_N")]
    rep["usb_pads"] = sorted("%s-%s" % (p["ref"], p["pad"]) for p in pads if p["net"] in ("USB_D_P", "USB_D_N"))

    # ---- via-in-pad (every via whose land overlaps an SMD pad on Top or Bottom)
    vip = []
    for v in vias:
        r = v["size"] / 2
        for L in sorted({v["span"][0], v["span"][1]} & {"Top", "Bottom"}):
            for p in pads:
                if p["layer"] != L or p["hole"] > 0 or p["sx"] <= 0:
                    continue
                if abs(p["x"] - v["x"]) > 3 or abs(p["y"] - v["y"]) > 3:
                    continue
                p = pad_view(p, L)
                d = pad_point_dist(p, v["x"], v["y"])
                if d < r - 1e-4:
                    depth = pad_inner_depth(p, v["x"], v["y"])
                    centred = math.hypot(p["x"] - v["x"], p["y"] - v["y"]) <= CENTRE_TOL
                    vip.append(dict(ref=p["ref"], pad=p["pad"], pad_net=p["net"], via_net=v["net"], side=L,
                                    span=SPAN_SHORT[v["span"]], via_x=round(v["x"], 4), via_y=round(v["y"], 4),
                                    land=round(v["size"], 4), hole=round(v["hole"], 4),
                                    pad_shape={1: "round", 2: "rect", 3: "octagon"}.get(p["shape"], str(p["shape"])),
                                    pad_size="%.3f x %.3f" % (p["sx"], p["sy"]),
                                    centred=centred,
                                    position=("centred" if centred else "hole in pad" if depth >= v["hole"] / 2 - 1e-4
                                              else "hole on pad edge" if d < v["hole"] / 2 - 1e-4 else "land only"),
                                    overlap=round(r - d, 4)))
    vip.sort(key=lambda e: (e["ref"] != "U1", str(e["ref"]), e["pad"], e["side"], e["span"], e["via_x"], e["via_y"]))
    rep["via_in_pad"] = vip
    site = lambda e: (e["via_x"], e["via_y"], e["span"])
    rep["via_in_pad_summary"] = dict(
        entries=len(vip),
        vias=len({site(e) for e in vip}),
        vias_touching_two_pads=sum(1 for k, c in Counter(site(e) for e in vip).items() if c > 1),
        by_type={"%s %.2f/%.2f" % (k[0], k[1], k[2]): c for k, c in sorted(Counter((e["span"], e["hole"], e["land"]) for e in {site(e): e for e in vip}.values()).items())},
        by_position=dict(Counter(e["position"] for e in vip)),
        u1={"%s %.2f/%.2f" % k: c for k, c in sorted(Counter((e["span"], e["hole"], e["land"]) for e in vip if e["ref"] == "U1").items())},
        non_u1={"%s %.2f/%.2f" % k: c for k, c in sorted(Counter((e["span"], e["hole"], e["land"]) for e in {site(e): e for e in vip if e["ref"] != "U1"}.values()).items())},
        by_ref={str(k): c for k, c in sorted(Counter(e["ref"] for e in vip).items(), key=lambda kv: str(kv[0]))})
    thru_vip = [e for e in vip if e["span"] == "Top-Bot"]
    rep["through_vias_in_smd_pads"] = thru_vip
    rep["through_vias_in_smd_pads_count"] = dict(entries=len(thru_vip), vias=len({(e["via_x"], e["via_y"]) for e in thru_vip}),
                                                 by_position=dict(Counter(e["position"] for e in thru_vip)),
                                                 by_side=dict(Counter(e["side"] for e in thru_vip)))
    lasers_in_pads = {site(e): e for e in vip if e["span"] not in ("Top-Bot",)}
    rep["lasers_in_non_u1_smd_pads"] = dict(
        total=len({k for k, e in lasers_in_pads.items() if e["ref"] != "U1"}),
        by_hole=dict(Counter(str(e["hole"]) for k, e in lasers_in_pads.items() if e["ref"] != "U1")))

    # ---- U1 ball census ------------------------------------------------------
    u1 = [p for p in pads if p["ref"] == "U1"]
    rep["u1_lands"] = dict(count=len(u1), sizes=dict(Counter("%.3f %s %s" % (p["sx"], {1: "round"}.get(p["shape"], p["shape"]), p["layer"]) for p in u1)))
    at = defaultdict(list)
    for v in vias:
        at[key(v)].append(v)
    combos = Counter()
    combo_nets = defaultdict(Counter)
    centred_lasers = Counter()
    centred_buried = 0
    no_centre = []
    for p in u1:
        cv = [v for v in vias if abs(v["x"] - p["x"]) <= CENTRE_TOL and abs(v["y"] - p["y"]) <= CENTRE_TOL]
        spans = tuple(SPAN_SHORT[s] for s in sorted({v["span"] for v in cv}, key=lambda s: (STACK.index(s[0]), STACK.index(s[1]))))
        combos[" + ".join(spans) or "none"] += 1
        combo_nets[" + ".join(spans) or "none"][p["net"] if p["net"] in ("GND", "VCC3V3", "VCC1V0", "VCC1V8") else "signal"] += 1
        for v in cv:
            if v["span"] in (T12, T23, T45, T56):
                centred_lasers["%s %.2f/%.2f" % (SPAN_SHORT[v["span"]], v["hole"], v["size"])] += 1
            elif v["span"] == T34:
                centred_buried += 1
        if not cv:
            no_centre.append(p)
    rep["u1_centred_combos"] = dict(combos)
    rep["u1_centred_combo_nets"] = {k: dict(v) for k, v in combo_nets.items()}
    rep["u1_centred_lasers"] = dict(centred_lasers)
    rep["u1_centred_lasers_total"] = sum(centred_lasers.values())
    rep["u1_centred_buried"] = centred_buried
    rep["u1_centred_through"] = sum(1 for p in u1 for v in vias if v["span"] == THRU and math.hypot(v["x"] - p["x"], v["y"] - p["y"]) <= CENTRE_TOL)
    off = [e for e in vip if e["ref"] == "U1" and not e["centred"]]
    rep["u1_off_centre_overlaps"] = dict(balls=len({e["pad"] for e in off}),
                                         vias=len({site(e) for e in off}),
                                         by_type={"%s %.2f/%.2f" % k: c for k, c in sorted(Counter((e["span"], e["hole"], e["land"]) for e in {site(e): e for e in off}.values()).items())},
                                         list=["%s %s %s (%.3f, %.3f) %s" % (e["pad"], e["span"], e["via_net"], e["via_x"], e["via_y"], e["position"]) for e in off])
    rep["u1_balls_without_centred_via"] = len(no_centre)
    rep["u1_balls_without_centred_via_but_overlapped"] = len({e["pad"] for e in off} & {p["pad"] for p in no_centre})
    xs = [p["x"] for p in u1]
    ys = [p["y"] for p in u1]
    box = (min(xs) - 0.25, min(ys) - 0.25, max(xs) + 0.25, max(ys) + 0.25)
    rep["u1_box"] = [round(c, 3) for c in box]
    u1_ball_xy = [(p["x"], p["y"]) for p in u1]

    def on_ball(v):
        return any(abs(v["x"] - x) <= CENTRE_TOL and abs(v["y"] - y) <= CENTRE_TOL for x, y in u1_ball_xy)
    small = [v for v in lasers if abs(v["hole"] - 0.10) < 0.002]
    small_off = [v for v in small if not on_ball(v)]
    rep["lasers_010"] = dict(total=len(small), centred_on_u1_ball=len(small) - len(small_off), not_on_ball=len(small_off),
                             not_on_ball_under_u1=sum(1 for v in small_off if box[0] <= v["x"] <= box[2] and box[1] <= v["y"] <= box[3]),
                             not_on_ball_by_span=dict(Counter(SPAN_SHORT[v["span"]] for v in small_off)))
    rep["lasers_015"] = sum(1 for v in lasers if abs(v["hole"] - 0.15) < 0.002)
    rep["lasers_015_on_u1_ball"] = sum(1 for v in lasers if abs(v["hole"] - 0.15) < 0.002 and on_ball(v))
    rep["vias_under_u1_box"] = dict(Counter(SPAN_SHORT[v["span"]] for v in vias if box[0] <= v["x"] <= box[2] and box[1] <= v["y"] <= box[3]))
    # column variants ending at Bottom (full columns), with laser sizes
    rep["full_columns"] = []
    for k in sorted(l2l5 & s12 & s56):
        vs = at[k]
        ball = next((p["pad"] for p in u1 if abs(p["x"] - k[0]) <= CENTRE_TOL and abs(p["y"] - k[1]) <= CENTRE_TOL), None)
        rep["full_columns"].append(dict(x=k[0], y=k[1], net=vs[0]["net"], u1_ball=ball,
                                        holes={SPAN_SHORT[v["span"]]: round(v["hole"], 2) for v in vs}))

    # ---- solder mask: tenting ------------------------------------------------
    tent = {}
    for side, ext in (("Top", "GTS"), ("Bottom", "GBS")):
        ops = mask_openings(os.path.join(OUTPUTS, "%s.%s" % (BASE, ext)))
        side_pads = [p for p in pads if pad_on_layer(p, side) and pad_view(p, side)["sx"] > 0]
        matched = 0
        unmatched = []
        u1_open = Counter()
        for o in ops:
            hit = [p for p in side_pads if abs(p["x"] - o["x"]) < 0.002 and abs(p["y"] - o["y"]) < 0.002]
            if hit:
                matched += 1
                if hit[0]["ref"] == "U1":
                    u1_open["%.3f x %.3f r%.3f" % (2 * (o["hx"] + o["r"]), 2 * (o["hy"] + o["r"]), o["r"])] += 1
            else:
                unmatched.append(dict(x=o["x"], y=o["y"], size="%.3f x %.3f" % (2 * (o["hx"] + o["r"]), 2 * (o["hy"] + o["r"])),
                                      vias_here=[SPAN_SHORT[v["span"]] for v in vias if abs(v["x"] - o["x"]) < 0.002 and abs(v["y"] - o["y"]) < 0.002]))
        vip_sites = {(e["via_x"], e["via_y"]) for e in vip if e["side"] == side}
        exposed = []
        grid_ops = defaultdict(list)
        for n, o in enumerate(ops):
            ext_r = max(o["hx"], o["hy"]) + o["r"] + 0.3
            for c in cells(o["x"], o["y"], o["x"], o["y"], ext_r):
                grid_ops[c].append(n)
        for v in vias:
            if side not in v["span"]:
                continue
            r = v["size"] / 2
            seen = set()
            for n in grid_ops[(int(v["x"] // grid), int(v["y"] // grid))]:
                if n in seen:
                    continue
                seen.add(n)
                o = ops[n]
                d = opening_point_dist(o, v["x"], v["y"])
                if d < r - 1e-4:
                    pad = next((p for p in side_pads if abs(p["x"] - o["x"]) < 0.002 and abs(p["y"] - o["y"]) < 0.002), None)
                    in_vip = (round(v["x"], 4), round(v["y"], 4)) in vip_sites
                    exposed.append(dict(span=SPAN_SHORT[v["span"]], net=v["net"], x=round(v["x"], 4), y=round(v["y"], 4),
                                        opening="%s-%s" % (pad["ref"], pad["pad"]) if pad else "unmatched",
                                        opening_net=pad["net"] if pad else None,
                                        in_vip_list=in_vip,
                                        hole_reached=d < v["hole"] / 2 - 1e-4,
                                        hole_margin=round(d - v["hole"] / 2, 4),
                                        land_overlap=round(r - d, 4)))
        not_vip = [e for e in exposed if not e["in_vip_list"]]
        tent[side] = dict(openings=len(ops), openings_on_pads=matched, unmatched_openings=unmatched, u1_openings=dict(u1_open),
                          vias_with_land_in_opening=len({(e["x"], e["y"], e["span"]) for e in exposed}),
                          of_which_in_vip_list=len({(e["x"], e["y"], e["span"]) for e in exposed if e["in_vip_list"]}),
                          not_in_vip_list=sorted(not_vip, key=lambda e: (e["span"], e["x"], e["y"])),
                          exposed_by_span={sp: dict(vias=len({(e["x"], e["y"]) for e in exposed if e["span"] == sp}),
                                                    hole_reached=len({(e["x"], e["y"]) for e in exposed if e["span"] == sp and e["hole_reached"]}))
                                           for sp in sorted({e["span"] for e in exposed})},
                          vip_vias_not_exposed=len({(e["via_x"], e["via_y"]) for e in vip if e["side"] == side} - {(e["x"], e["y"]) for e in exposed}))
    rep["tenting"] = tent
    return rep


def main():
    pcb = sys.argv[sys.argv.index("--pcb") + 1] if "--pcb" in sys.argv else PCB
    rep = measure(pcb)
    out = os.path.join(HERE, "fab_facts.json") if pcb == PCB else os.devnull
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(rep, handle, indent=1, default=str)
    for k, v in rep.items():
        if k in ("via_in_pad", "through_vias_in_smd_pads", "full_columns"):
            print(k, "(%d)" % len(v))
            for e in v:
                print("  ", e)
        else:
            print(k, "=", json.dumps(v, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
