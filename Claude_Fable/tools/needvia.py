# -*- coding: utf-8 -*-
"""Which of the 103 outward escapes actually have to leave L1?

    python tools/needvia.py

WHY. The fan-out router in escape.py assumes every outward escape drops to an
inner layer, and on that assumption it runs short of via room. But a ball only
needs a via if it cannot reach its destination on the top layer, and many of
these go to X2's header, whose pins are PLATED HOLES and reachable from any
layer, or to parts that sit on the front.

Three verdicts, and the middle one is honest rather than lazy:

    must      some destination is a back-side pad, so the net has to change layer
    depends   a destination is a part that is not placed yet
    no        every destination is a plated hole or top-side copper

"must" is a floor, not an answer. Two things push the real number up: the
"depends" resolve once the loose resistors are placed, and traces that cross on
L1 need a via whether or not their endpoints did. What it does settle is the
LOWER bound, and that is what decides whether the fan-out has any chance.

Power and ground escapes are counted as "must" by definition -- a plane net
leaves L1 at the first opportunity, that is the whole point of it.
"""

import re, os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import escape as E

b, pos, land, net, clr = E.load(E.BRD)
cell, at, ring, n = E.grid(pos)
brd = open(E.BRD, encoding="utf-8").read()

PKG = {}
for lm in re.finditer(r'<library name="([^"]+)">(.*?)</library>', brd, re.S):
    for pm in re.finditer(r'<package name="([^"]+)">(.*?)</package>', lm.group(2), re.S):
        PKG[(lm.group(1), pm.group(1))] = pm.group(2)

side, plated, ypos = {}, set(), {}
for m in re.finditer(r'<element name="([^"]+)" library="([^"]+)" package="([^"]+)"([^>]*)>', brd):
    nm, lib, pk, attrs = m.group(1), m.group(2), m.group(3), m.group(4)
    rot = (re.search(r'rot="(M?R\d+)"', attrs) or [None, "R0"])[1]
    side[nm] = "back" if rot.startswith("M") else "top"
    ypos[nm] = float(re.search(r'y="([-\d.]+)"', attrs).group(1))
    for s in re.finditer(r'<pad name="([^"]+)"', PKG.get((lib, pk), "")):
        plated.add((nm, s.group(1)))

conn = collections.defaultdict(list)
for sm in re.finditer(r'<signal name="([^"]+)"[^>]*>(.*?)</signal>', brd, re.S):
    for c in re.finditer(r'<contactref element="([^"]+)" pad="([^"]+)"/>', sm.group(2)):
        conn[sm.group(1)].append((c.group(1), c.group(2)))

xs = sorted({round(p[0], 3) for p in pos.values()})
ys = sorted({round(p[1], 3) for p in pos.values()})
cx, cy = (xs[0] + xs[-1]) / 2, (ys[0] + ys[-1]) / 2
h0 = (xs[-1] - xs[0]) / 2


def which(p):
    """which side of the package a ball escapes through.

    By the larger offset from the centre, not by sitting exactly on the ring-0
    square: ring-1 balls are half a millimetre inboard and an equality test sent
    every one of them to the default.
    """
    u, w = p[0] - cx, p[1] - cy
    if abs(u) >= abs(w):
        return "right" if u > 0 else "left"
    return "top" if w > 0 else "bottom"


pwr, edges, comp = E.gang(pos, net, cell, at)
strand = [k for r, v in comp.items()
          if not any(ring[x] in (0, 2, 6) for x in v) for k in v]
slots, need_, match, miss = E.lanes(pos, net, cell, at, ring, n, edges, set(strand))

esc = []                                       # (ball, kind) -- all 103 outward
for k in pos:
    if ring[k] == 0 and k in net and not E.POWER.match(net[k]):
        esc.append((k, "r0 signal"))
for gi, k in match.items():
    if slots[gi]["tag"] == "out":
        esc.append((k, "r1 signal" if not E.POWER.match(net[k]) else "r1 power"))
for r, v in comp.items():
    a0 = sorted(x for x in v if ring[x] == 0)
    if a0:
        esc.append((a0[0], "r0 power"))

rows = []
for k, kind in esc:
    nm = net[k]
    others = [(e, pd) for e, pd in conn[nm] if e != "U1"]
    dest, need, unknown = [], False, False
    for e, pd in others:
        hole = (e, pd) in plated
        parked = ypos.get(e, 0) < 0
        dest.append("%s(%s%s)" % (e, "hole" if hole else side.get(e, "?"),
                                  ",unplaced" if parked else ""))
        if not hole and side.get(e) == "back":
            need = True
        if not hole and parked:
            unknown = True
    if kind.endswith("power"):
        need, unknown = True, False            # a plane net leaves L1 by definition
    rows.append((which(pos[k]), k, nm, need, unknown, sorted(set(dest)), kind))

rows.sort()
print("%-7s %-5s %-14s %-9s %s" % ("side", "ball", "net", "via?", "has to reach"))
for sd, k, nm, need, unk, dest, kind in rows:
    tag = "YES" if need else ("depends" if unk else "no")
    print("%-7s %-5s %-14s %-10s %-9s %s" % (sd, k, nm, kind, tag, ", ".join(dest)[:44]))

print("")
per = collections.Counter()
for sd, k, nm, need, unk, dest, kind in rows:
    per[(sd, "yes" if need else "depends" if unk else "no")] += 1
# how many vias each side can actually hold, measured, not remembered
cop = E.board_copper(b)
HOLD = {}
for sd, f in (("bottom", lambda o: cy - o[2] - o[4]), ("top", lambda o: o[2] - o[4] - cy),
              ("left", lambda o: cx - o[1] - o[3]), ("right", lambda o: o[1] - o[3] - cx)):
    band = [o for o in cop
            if (abs(o[1] - cx) < h0 + 2 if sd in ("bottom", "top")
                else abs(o[2] - cy) < h0 + 2)]
    d = [f(o) for o in band if f(o) > h0]
    HOLD[sd] = int(2 * ((min(d) - 0.24) if d else h0 + 2) / (E.VIA_L + clr))
print("%-7s %5s %8s %5s %5s %6s" % ("side", "must", "depends", "no", "of", "holds"))
for sd in ("bottom", "right", "top", "left"):
    y, d, nn = per[(sd, "yes")], per[(sd, "depends")], per[(sd, "no")]
    print("%-7s %5d %8d %5d %5d %6d   %s" % (sd, y, d, nn, y+d+nn, HOLD[sd],
          "OK if the maybes stay on L1" if y <= HOLD[sd] else "STILL SHORT by %d" % (y-HOLD[sd])))
tot = [sum(per[(s, t)] for s in ("bottom", "right", "top", "left"))
       for t in ("yes", "depends", "no")]
print("%-7s %5d %8d %5d %5d %6d" % ("total", tot[0], tot[1], tot[2], sum(tot), sum(HOLD.values())))
