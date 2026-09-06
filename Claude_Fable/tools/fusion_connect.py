# -*- coding: utf-8 -*-
"""Make every joint one that Fusion recognises, and drop copper that joins
nothing.

    python tools/fusion_connect.py in.brd out.brd

WHY. Fusion (like EAGLE) decides connectivity from END POINTS, not from
copper overlap: two wires of a signal are joined only where an end point of
one coincides EXACTLY with an end point of the other (its coordinates are
integers of 1/320000 mm; ends 0.0011 mm apart are two points), and a wire
reaches a via only when it ends on the via's centre. A wire that ends on the
body of another wire (a T), or 0.05 mm short of it with the copper plainly
overlapping, or 0.05 mm off a via's centre inside its land, is an open
circuit to Ratsnest -- and this board had 14 nets of those, all written by
tools that reasoned about copper rather than end points. And every piece
counts: a leftover via, or a stump of an old route, earns an airwire of its
own (TDI carried four such pieces, 59 objects, on 2026-09-05). Read from
Fusion's own airwire list with tools/airwires.ulp.

WHAT IT DOES, per signal, until nothing changes:
  - drops duplicate and zero-length wires (a duplicate stub anchored itself
    and hid the very T it should have fixed -- VU, 2026-09-05);
  - splits the signal into pieces by Fusion's rules (check_connectivity);
  - for a wire end of one piece that lies within SNAP of another piece's
    wire end or via centre, moves the end onto it; inside a via land of
    another piece, adds a wire to the via centre; on the body of another
    piece's wire, splits that wire there (with a bridge if the end sits a
    hair off the centreline); within BRIDGE of another piece's wire end,
    bridges;
  - finally deletes every piece that holds no pad, unless the net has a
    pour (a lone GND via is a stitching via, not litter).
Everything added lies inside the signal's own copper, so no clearance changes.
"""

import collections
import io
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_connectivity as C   # noqa: E402
import escape as E   # noqa: E402

EPS = C.EPS
SNAP = 0.01
BRIDGE = 0.16
SIG_RE = re.compile(r'(<signal name="([^"]+)"[^>]*>)(.*?)(</signal>)', re.S)
WIRE_RE = re.compile(r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)" width="([\d.]+)" layer="(\d+)"[^>]*/>')
VIA_RE = re.compile(r"<via\s[^>]*?(?:/>|>\s*</via>)", re.S)   # Fusion writes some vias as <via ...></via>
COPPER = C.COPPER_LAYERS


def g(v):
    t = ("%.5f" % v).rstrip("0").rstrip(".")
    return t if t not in ("", "-0") else "0"


def same(a, b):
    return abs(a[0] - b[0]) <= EPS and abs(a[1] - b[1]) <= EPS


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def pads_by_net(board):
    """{net: [pad dict]} in check_connectivity's object form."""
    out = collections.defaultdict(list)
    for net, x, y, hx, hy, side in E.board_copper(board, skip=()):
        if net is None:
            continue
        out[net].append({"kind": "pad", "at": (x, y), "hx": hx, "hy": hy,
                         "through": side == 0,
                         "layers": COPPER if side == 0 else frozenset((side,))})
    return out


def parse(body):
    wires, vias = [], []
    for m in WIRE_RE.finditer(body):
        x1, y1, x2, y2, w = (float(v) for v in m.groups()[:5])
        L = int(m.group(6))
        if L not in COPPER:
            continue
        wires.append({"kind": "wire", "a": (x1, y1), "b": (x2, y2), "radius": w / 2, "w": w,
                      "L": L, "layers": frozenset((L,)), "text": m.group(0)})
    for m in VIA_RE.finditer(body):
        at = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0)))
        if "x" not in at:
            continue
        dr = float(at.get("drill", "0.2"))
        dia = float(at["diameter"]) if "diameter" in at else dr + 2 * max(dr * 0.25, 0.05)
        lo, hi = sorted(int(v) for v in at.get("extent", "1-16").split("-"))
        vias.append({"kind": "via", "at": (float(at["x"]), float(at["y"])), "radius": dia / 2,
                     "layers": frozenset(L for L in COPPER if lo <= L <= hi), "text": m.group(0)})
    return wires, vias


def dedupe(wires):
    seen = set()
    out = []
    for w in wires:
        if dist(w["a"], w["b"]) < 1e-6:
            continue   # truly zero length only: a 0.002 mm hop into a pad centre is a joint check_board needs
        key = (w["L"], round(w["w"], 5)) + tuple(sorted((tuple(round(v, 5) for v in w["a"]), tuple(round(v, 5) for v in w["b"]))))
        if key in seen:
            continue
        seen.add(key)
        out.append(w)
    return out, len(wires) - len(out)


def piece_ids(objects):
    union = C.connectivity_union(objects, set())
    return [union.find(i) for i in range(len(objects))]


def find_fix(pads, vias, wires, pid):
    """first joint between two pieces that a local edit can make, or None"""
    nv = len(pads)
    base = nv + len(vias)
    for wi, w in enumerate(wires):
        me = pid[base + wi]
        L = w["L"]
        for end_key in ("a", "b"):
            e = w[end_key]
            # 0. a hair from another piece's wire end or via centre: snap
            for vi, v in enumerate(vias):
                if pid[nv + vi] != me and L in v["layers"] and dist(v["at"], e) <= SNAP:
                    return ("snap", wi, end_key, v["at"])
            for oi, o in enumerate(wires):
                if pid[base + oi] != me and o["L"] == L:
                    for f in (o["a"], o["b"]):
                        if dist(f, e) <= SNAP:
                            return ("snap", wi, end_key, f)
            # 1. inside a via land of another piece
            for vi, v in enumerate(vias):
                if pid[nv + vi] != me and L in v["layers"] and dist(v["at"], e) <= v["radius"] + EPS:
                    return ("via", wi, end_key, v["at"])
            # 2. on the body of another piece's wire
            for hi_, h in enumerate(wires):
                if pid[base + hi_] != me and h["L"] == L and E.seg_pt(h["a"], h["b"], e) <= h["radius"] + EPS:
                    return ("split", wi, end_key, hi_)
            # 3. near a loose end of another piece's wire
            best = None
            for oi, o in enumerate(wires):
                if pid[base + oi] != me and o["L"] == L:
                    for f in (o["a"], o["b"]):
                        d = dist(f, e)
                        if d <= BRIDGE and (best is None or d < best[0]):
                            best = (d, f)
            if best:
                return ("bridge", wi, end_key, best[1])
    return None


def snap_all(wires, e, target, L):
    """move EVERY end at e on layer L to target -- moving one wire alone
    leaves its neighbours a hair short, and each of those is a stub"""
    out = []
    for o in wires:
        if o["L"] == L:
            moved = dict(o)
            for k in ("a", "b"):
                if same(o[k], e):
                    moved[k] = target
                    moved["text"] = None
            out.append(moved)
        else:
            out.append(o)
    return [o for o in out if dist(o["a"], o["b"]) > 1e-6]


def anchored(e, L, w, pads, vias, wires):
    for o in wires:
        if o is not w and o["L"] == L and (same(o["a"], e) or same(o["b"], e)):
            return True
    for v in vias:
        if L in v["layers"] and same(v["at"], e):
            return True
    for p in pads:
        if L in p["layers"] and C.inside_pad(p, e):
            return True
    return False


def find_stub(pads, vias, wires):
    """first wire end that meets nothing, with the repair for it"""
    for wi, w in enumerate(wires):
        L = w["L"]
        for end_key in ("a", "b"):
            e = w[end_key]
            if anchored(e, L, w, pads, vias, wires):
                continue
            for o in wires:
                if o is not w and o["L"] == L:
                    for f in (o["a"], o["b"]):
                        if EPS < dist(f, e) <= SNAP:
                            return ("snap", wi, end_key, f)
            for v in vias:
                if L in v["layers"] and dist(v["at"], e) <= v["radius"] + EPS:
                    return ("via", wi, end_key, v["at"])
            for hi_, h in enumerate(wires):
                if h is not w and h["L"] == L and E.seg_pt(h["a"], h["b"], e) <= h["radius"] + EPS:
                    return ("split", wi, end_key, hi_)
            best = None
            for o in wires:
                if o is not w and o["L"] == L:
                    for f in (o["a"], o["b"]):
                        d = dist(f, e)
                        if d <= BRIDGE and (best is None or d < best[0]):
                            best = (d, f)
            if best:
                return ("bridge", wi, end_key, best[1])
            other = w["b"] if end_key == "a" else w["a"]
            if dist(w["a"], w["b"]) <= 1.5 and anchored(other, L, w, pads, vias, wires):
                return ("delete", wi, end_key, None)
    return None


def repair(name, body, pads, has_pour=None):
    """-> (new body, list of fix descriptions)"""
    if has_pour is None:
        has_pour = bool(re.search(r'<polygon(?:pour)?\b', body))
    wires, vias = parse(body)
    wires, dropped = dedupe(wires)
    fixes = ["%s: %d duplicate/zero-length wire(s) dropped" % (name, dropped)] if dropped else []
    changed_any = dropped > 0
    # a layer-19 wire inside a signal is a stored airwire; Ratsnest recomputes
    # them and the rewrite below drops it anyway, so drop it deliberately
    stale = [m.group(0) for m in WIRE_RE.finditer(body) if int(m.group(6)) not in COPPER]
    if stale:
        fixes.append("%s: %d non-copper wire(s) (layer %s) dropped" % (name, len(stale), ",".join(sorted(set(re.search(r'layer="(\d+)"', s).group(1) for s in stale)))))
        changed_any = True
    for _ in range(80):
        pid = piece_ids(list(pads) + vias + wires)
        if len(set(pid)) < 2:
            break
        fix = find_fix(pads, vias, wires, pid)
        if not fix:
            break
        changed_any = True
        kind, wi, end_key, target = fix
        w = wires[wi]
        e = w[end_key]
        if kind == "snap":
            wires = snap_all(wires, e, target, w["L"])
            fixes.append("%s L%d end (%s,%s) snapped to (%s,%s)" % (name, w["L"], g(e[0]), g(e[1]), g(target[0]), g(target[1])))
        elif kind == "via":
            wires.append(dict(w, a=e, b=target, text=None))
            fixes.append("%s L%d end (%s,%s) -> via centre (%s,%s)" % (name, w["L"], g(e[0]), g(e[1]), g(target[0]), g(target[1])))
        elif kind == "split":
            h = wires[target]
            a, b = h["a"], h["b"]
            dx, dy = b[0] - a[0], b[1] - a[1]
            L2 = dx * dx + dy * dy
            t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((e[0] - a[0]) * dx + (e[1] - a[1]) * dy) / L2))
            p = (round(a[0] + dx * t, 5), round(a[1] + dy * t, 5))
            wires.remove(h)
            for q, r in ((a, p), (p, b)):
                if dist(q, r) > 1e-6:
                    wires.append(dict(h, a=q, b=r, text=None))
            if dist(p, e) > 1e-6:
                wires.append(dict(w, a=e, b=p, text=None))
            fixes.append("%s L%d end (%s,%s) splits a wire at (%s,%s)" % (name, w["L"], g(e[0]), g(e[1]), g(p[0]), g(p[1])))
        else:
            wires.append(dict(w, a=e, b=target, text=None))
            fixes.append("%s L%d bridge (%s,%s)-(%s,%s) %.3f mm" % (
                name, w["L"], g(e[0]), g(e[1]), g(target[0]), g(target[1]), dist(target, e)))
    # STUBS. Fusion's DRC warns on every wire end that meets nothing, joined
    # piece or not: a T inside one piece, a hop that stops inside a via land,
    # the neighbours of an end that was moved. Same repairs, any piece; a
    # short stump with nothing near its free end is deleted.
    for _ in range(200):
        stub = find_stub(pads, vias, wires)
        if not stub:
            break
        changed_any = True
        kind, wi, end_key, target = stub
        w = wires[wi]
        e = w[end_key]
        if kind == "snap":
            wires = snap_all(wires, e, target, w["L"])
            fixes.append("%s L%d stub (%s,%s) snapped to (%s,%s)" % (name, w["L"], g(e[0]), g(e[1]), g(target[0]), g(target[1])))
        elif kind == "via":
            wires.append(dict(w, a=e, b=target, text=None))
            fixes.append("%s L%d stub (%s,%s) -> via centre" % (name, w["L"], g(e[0]), g(e[1])))
        elif kind == "split":
            h = wires[target]
            a, b = h["a"], h["b"]
            dx, dy = b[0] - a[0], b[1] - a[1]
            L2 = dx * dx + dy * dy
            t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((e[0] - a[0]) * dx + (e[1] - a[1]) * dy) / L2))
            p = (round(a[0] + dx * t, 5), round(a[1] + dy * t, 5))
            wires.remove(h)
            for q, r in ((a, p), (p, b)):
                if dist(q, r) > 1e-6:
                    wires.append(dict(h, a=q, b=r, text=None))
            if dist(p, e) > 1e-6:
                wires.append(dict(w, a=e, b=p, text=None))
            fixes.append("%s L%d stub (%s,%s) splits a wire" % (name, w["L"], g(e[0]), g(e[1])))
        elif kind == "bridge":
            wires.append(dict(w, a=e, b=target, text=None))
            fixes.append("%s L%d stub (%s,%s) bridged %.3f mm" % (name, w["L"], g(e[0]), g(e[1]), dist(target, e)))
        else:
            wires.pop(wi)
            fixes.append("%s L%d stump (%s,%s) %.3f mm deleted" % (name, w["L"], g(e[0]), g(e[1]), dist(w["a"], w["b"])))
    # ENDS INSIDE A PAD, OFF ITS CENTRE, WITH NOTHING ELSE THERE. Connected,
    # but Fusion's DRC still lists them as Wire Stubs (13 of the 15 left on
    # 2026-09-05 were exactly this); a hop to the pad centre, inside the
    # pad's own copper, ends the wire where Fusion wants it.
    for w in list(wires):
        L = w["L"]
        for e in (w["a"], w["b"]):
            if any(o is not w and o["L"] == L and (same(o["a"], e) or same(o["b"], e)) for o in wires):
                continue
            if any(L in v["layers"] and same(v["at"], e) for v in vias):
                continue
            pad = next((p for p in pads if L in p["layers"] and C.inside_pad(p, e)), None)
            if pad is None or dist(pad["at"], e) <= EPS:
                continue
            wires.append(dict(w, a=e, b=pad["at"], text=None))
            fixes.append("%s L%d end (%s,%s) -> pad centre (%s,%s)" % (name, L, g(e[0]), g(e[1]), g(pad["at"][0]), g(pad["at"][1])))
            changed_any = True
    # floating pieces. A pour net keeps its lone stitching vias (they tie
    # the pour to the plane), but a padless piece of wires only -- the stub
    # a moved part left behind (VCC3V3, 2026-09-06) -- is litter there too.
    pid = piece_ids(list(pads) + vias + wires)
    with_pad = set(pid[i] for i in range(len(pads)))
    if has_pour:
        with_pad |= set(pid[len(pads) + i] for i, v in enumerate(vias) if len(v["layers"]) > 2)
    if True:
        drop_v = [v for i, v in enumerate(vias) if pid[len(pads) + i] not in with_pad]
        drop_w = [w for i, w in enumerate(wires) if pid[len(pads) + len(vias) + i] not in with_pad]
        if drop_v or drop_w:
            vias = [v for v in vias if v not in drop_v]
            wires = [w for w in wires if w not in drop_w]
            fixes.append("%s: floating copper dropped, %d wire(s) %d via(s)" % (name, len(drop_w), len(drop_v)))
            changed_any = True
    if not changed_any:
        return body, fixes
    nb = WIRE_RE.sub("", body)
    for v in re.findall(VIA_RE, body):
        if not any(v == kept["text"] for kept in vias):
            nb = nb.replace(v, "", 1)
    for w in wires:
        if w["text"] is not None:
            nb += w["text"]
        else:
            nb += '<wire x1="%s" y1="%s" x2="%s" y2="%s" width="%s" layer="%d"/>' % (
                g(w["a"][0]), g(w["a"][1]), g(w["b"][0]), g(w["b"][1]), g(w["w"]), w["L"])
    return nb, fixes


def main():
    src, dst = sys.argv[1], sys.argv[2]
    board = io.open(src, encoding="utf-8", errors="replace").read()
    pads = pads_by_net(board)
    total = []

    def sub(m):
        name = m.group(2)
        nb, fixes = repair(name, m.group(3), pads.get(name, []))
        total.extend(fixes)
        return m.group(1) + nb + m.group(4)

    out = SIG_RE.sub(sub, board)
    for f in total:
        print("  " + f)
    print("%d change(s)" % len(total))
    import xml.etree.ElementTree as ET
    ET.fromstring(out)
    io.open(dst, "w", encoding="utf-8", newline="").write(out)
    print("wrote", dst)


if __name__ == "__main__":
    main()
