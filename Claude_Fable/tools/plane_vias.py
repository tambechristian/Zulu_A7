# -*- coding: utf-8 -*-
"""Give every plane-net ball cluster of U1, and every plane pad of U3, a
through via BEFORE routing, so the router routes around them instead of
burying the spots under traces.

    python tools/plane_vias.py in.brd out.brd [--nets GND,VCC3V3,...]

WHY. U1's 112 plane balls (68 GND, 28 VCC3V3, 12 supply) have no via in
the ball; they hang off L1 links to a handful of shared dogbone vias. The
core re-placement (2026-09-06) removed the dogbones that stood where U3's
pads now are, and after routing there was no spot left for a new one:
gnd_stitch found the six stranded pads walled in on every layer by the
routes laid meanwhile (run c4p). Reserving the via first costs the router
a few cells; finding it afterwards costs the pad.

WHAT IT DOES. For each listed net: groups U1's balls that are joined by
L1 wires; for every group without a through via, tries the diagonal spots
(x +/- 0.25, y +/- 0.25) beside each ball of the group, nearest the group's
centre first, for a 0.20/0.30 via whose land clears foreign copper on
every layer and whose drill keeps DRILL_CC from every other drill, and
writes the via plus the 0.354 mm L1 link from the ball. For U3, a via in
each plane pad that has none (same checks). Reports what it could not do.
"""

import io
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_connectivity as C   # noqa: E402
import escape as E   # noqa: E402
import pad_microvias as PM   # noqa: E402

SIG_RE = re.compile(r'(<signal name="([^"]+)"[^>]*>)(.*?)(</signal>)', re.S)
VIA_D, VIA_L = 0.2, 0.3
W = 0.0762
DEFAULT_NETS = "GND,VCC3V3,VCC1V0,VCC1V8,VCCADC,GNDADC"


def g(v):
    t = ("%.4f" % v).rstrip("0").rstrip(".")
    return t if t not in ("", "-0") else "0"


def via_ok(local, x, y):
    for o in local:
        if o["kind"] == "via" and math.hypot(o["at"][0] - x, o["at"][1] - y) < max(PM.DRILL_CC, o["radius"] + VIA_L / 2 + PM.CLR):
            return False
        if o["kind"] == "wire" and E.seg_pt(o["a"], o["b"], (x, y)) < o["radius"] + VIA_L / 2 + PM.CLR:
            return False
        if o["kind"] == "pad":
            if o["through"]:
                if math.hypot(o["at"][0] - x, o["at"][1] - y) < o["hx"] + VIA_L / 2 + PM.CLR:
                    return False
            elif max(abs(x - o["at"][0]) - o["hx"], abs(y - o["at"][1]) - o["hy"]) < VIA_L / 2 + PM.CLR:
                return False
    return True


def main():
    args = sys.argv[1:]
    nets = DEFAULT_NETS.split(",")
    if "--nets" in args:
        i = args.index("--nets")
        nets = args[i + 1].split(",")
        del args[i:i + 2]
    src, dst = args[0], args[1]
    board = io.open(src, encoding="utf-8", errors="replace").read()
    parsed = C.parse_signal_objects(board)
    sm = re.search(r"<signals>(.*)</signals>", board, re.S).group(1)
    u3nets = set(m.group(1) for m in re.finditer(r'<signal name="([^"]+)"[^>]*>(.*?)</signal>', sm, re.S) if 'element="U3"' in m.group(2))
    em = re.search(r'<element name="U3" library="([^"]+)" package="([^"]+)"[^>]*x="([-\d.]+)" y="([-\d.]+)"(?:[^>]*rot="([^"]+)")?', board)
    pm = re.search(r'<library name="%s">.*?<package name="%s"[^>]*>(.*?)</package>' % (re.escape(em.group(1)), re.escape(em.group(2))), board, re.S)
    rot = em.group(5) or "R0"

    def rp(x, y):
        r = rot[1:] if rot.startswith("M") else rot
        ang = int(r[1:]) % 360 if len(r) > 1 else 0
        x, y = {0: (x, y), 90: (-y, x), 180: (-x, -y), 270: (y, -x)}[ang]
        return (-x, y) if rot.startswith("M") else (x, y)
    u3centres = [(float(em.group(3)) + rp(float(s.group(2)), float(s.group(3)))[0], float(em.group(4)) + rp(float(s.group(2)), float(s.group(3)))[1])
                 for s in re.finditer(r'<smd name="([^"]+)" x="([-\d.]+)" y="([-\d.]+)"', pm.group(1))]
    adds, placed = {}, []
    for net in nets:
        if net not in parsed:
            continue
        objs = parsed[net][0]
        balls = [o for o in objs if o["kind"] == "pad" and not o["through"] and 1 in o["layers"] and abs(o["hx"] - 0.1125) < 0.01 and 41 < o["at"][0] < 52 and 7 < o["at"][1] < 17]
        vias = [o for o in objs if o["kind"] == "via" and len(o["layers"]) > 2]
        l1 = [o for o in objs if o["kind"] == "wire" and 1 in o["layers"]]
        # union-find over balls joined by L1 wires (end on the pad) and vias they touch
        parent = {}

        def find(k):
            while parent.get(k, k) != k:
                k = parent[k]
            return k

        def union(a, b):
            parent[find(a)] = find(b)
        keys = {}
        for o in balls + vias:
            keys[id(o)] = ("b" if o["kind"] == "pad" else "v", round(o["at"][0], 3), round(o["at"][1], 3))
        for o in balls + vias:
            parent.setdefault(keys[id(o)], keys[id(o)])
        # each L1 wire joins whatever it ends on (pad box or via land)
        def ends_on(pt):
            out = []
            for o in balls:
                if abs(pt[0] - o["at"][0]) <= o["hx"] + 1e-6 and abs(pt[1] - o["at"][1]) <= o["hy"] + 1e-6:
                    out.append(keys[id(o)])
            for o in vias:
                if math.hypot(pt[0] - o["at"][0], pt[1] - o["at"][1]) <= o["radius"] + 1e-6:
                    out.append(keys[id(o)])
            return out
        wires_seen = set()
        changed = True
        # chase wire chains: a wire may end on another wire's end rather than on a pad
        endpoints = {}
        for o in l1:
            for pt in (o["a"], o["b"]):
                endpoints.setdefault((round(pt[0], 4), round(pt[1], 4)), []).append(o)
        for o in l1:
            ka = ends_on(o["a"]) or [("w",) + (round(o["a"][0], 4), round(o["a"][1], 4))]
            kb = ends_on(o["b"]) or [("w",) + (round(o["b"][0], 4), round(o["b"][1], 4))]
            for k in ka + kb:
                parent.setdefault(k, k)
            for k in ka[1:] + kb:
                union(ka[0], k)
        groups = {}
        for o in balls:
            groups.setdefault(find(keys[id(o)]), []).append(o)
        has_via = set(find(keys[id(o)]) for o in vias)
        foreign = PM.foreign_copper(board, parsed, net)
        for root, members in groups.items():
            if root in has_via:
                continue
            cx = sum(o["at"][0] for o in members) / len(members)
            cy = sum(o["at"][1] for o in members) / len(members)
            cands = []
            for o in members:
                x, y = o["at"]
                for dx in (0.25, -0.25):
                    for dy in (0.25, -0.25):
                        cands.append((math.hypot(x + dx - cx, y + dy - cy), x + dx, y + dy, o))
            cands.sort(key=lambda c: c[0])
            done = False
            for _, vx, vy, o in cands:
                vx, vy = round(vx, 4), round(vy, 4)
                local = [q for q in foreign if abs((q.get("at") or q.get("a"))[0] - vx) < 2 and abs((q.get("at") or q.get("a"))[1] - vy) < 2] + placed
                own_near = [q for q in objs if q["kind"] == "via" and math.hypot(q["at"][0] - vx, q["at"][1] - vy) < PM.DRILL_CC]
                if own_near or not via_ok(local, vx, vy):
                    continue
                # the L1 link must clear foreign copper on L1 too
                ok = True
                for q in local:
                    if 1 not in q["layers"]:
                        continue
                    if q["kind"] == "wire" and E.seg_seg(q["a"], q["b"], o["at"], (vx, vy)) < q["radius"] + W / 2 + PM.CLR:
                        ok = False
                    elif q["kind"] == "pad" and not q["through"]:
                        import geom as G
                        if G.rect_seg((q["at"][0], q["at"][1], q["hx"], q["hy"], 0.0), o["at"], (vx, vy)) < W / 2 + PM.CLR:
                            ok = False
                    if not ok:
                        break
                if not ok:
                    continue
                adds[net] = adds.get(net, "") + '<via x="%s" y="%s" extent="1-16" drill="%s" diameter="%s"/>' % (g(vx), g(vy), g(VIA_D), g(VIA_L))
                adds[net] += '<wire x1="%s" y1="%s" x2="%s" y2="%s" width="%s" layer="1"/>' % (g(o["at"][0]), g(o["at"][1]), g(vx), g(vy), g(W))
                placed.append({"kind": "via", "at": (vx, vy), "radius": VIA_L / 2, "layers": C.COPPER_LAYERS})
                placed.append({"kind": "wire", "a": o["at"], "b": (vx, vy), "radius": W / 2, "layers": frozenset((1,))})
                print("  %-8s U1 group of %2d ball(s): via at (%.2f,%.2f) from ball (%.2f,%.2f)" % (net, len(members), vx, vy, o["at"][0], o["at"][1]))
                done = True
                break
            if not done:
                print("  ****  %-8s U1 group of %d ball(s) around (%.2f,%.2f): no via spot" % (net, len(members), cx, cy))
        # U3's plane pads: a via in the pad
        if net in u3nets:
            side = 16 if rot.startswith("M") else 1
            for o in objs:
                if o["kind"] != "pad" or o["through"] or side not in o["layers"]:
                    continue
                if not any(abs(o["at"][0] - cx_) < 0.05 and abs(o["at"][1] - cy_) < 0.05 for cx_, cy_ in u3centres):
                    continue
                x, y = o["at"]
                if any(q["kind"] == "via" and abs(q["at"][0] - x) <= o["hx"] and abs(q["at"][1] - y) <= o["hy"] for q in objs):
                    continue
                local = [q for q in foreign if abs((q.get("at") or q.get("a"))[0] - x) < 2 and abs((q.get("at") or q.get("a"))[1] - y) < 2] + placed
                if via_ok(local, x, y) and not any(q["kind"] == "via" and math.hypot(q["at"][0] - x, q["at"][1] - y) < PM.DRILL_CC for q in objs):
                    adds[net] = adds.get(net, "") + '<via x="%s" y="%s" extent="1-16" drill="%s" diameter="%s"/>' % (g(x), g(y), g(VIA_D), g(VIA_L))
                    placed.append({"kind": "via", "at": (x, y), "radius": VIA_L / 2, "layers": C.COPPER_LAYERS})
                    print("  %-8s U3 pad (%.2f,%.2f): via in the pad" % (net, x, y))
                else:
                    print("  ****  %-8s U3 pad (%.2f,%.2f): no room for a via in the pad" % (net, x, y))

    def sub(m):
        return m.group(1) + m.group(3) + adds.get(m.group(2), "") + m.group(4)
    out = SIG_RE.sub(sub, board)
    import xml.etree.ElementTree as ET
    ET.fromstring(out)
    io.open(dst, "w", encoding="utf-8", newline="").write(out)
    print("wrote %s (%d via(s) added)" % (dst, sum(a.count("<via") for a in adds.values())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
