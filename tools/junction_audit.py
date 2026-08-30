# -*- coding: utf-8 -*-
"""Junction audit with the pin term put back.

A junction is needed where E + 2T + (1 if a pin sits there) >= 3, with E the
wires ending at the point and T the wires passing through it. Drop the pin term
and every junction that legitimately sits on a pin -- which is most of them on
a supply rail -- reads as stray. That is what the quick check in the last run
was doing.

Pin positions need the instance transform: Eagle rotates first, then mirrors
about x=0.
"""
import re, io, sys, collections
# KEEP THE OLD WRAPPER ALIVE. Several of these modules rebind sys.stdout to a
# utf-8 TextIOWrapper over sys.stdout.buffer. Import two of them and the first
# wrapper loses its last reference, gets collected, and CLOSES THE SHARED
# BUFFER on the way out -- every subsequent print dies with 'I/O operation on
# closed file'. It only bit once check_board started importing geom.
_prev_stdout = sys.stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

t = open(r"C:\Users\tambe\Documents\Electronics\Zulu_A7\zulu_a7.sch", encoding="utf-8").read()
SYM = {m.group(1): m.group(2) for m in re.finditer(r'<symbol name="([^"]+)">(.*?)</symbol>', t, re.S)}
SYMPINS = {k: [(q.group(1), float(q.group(2)), float(q.group(3)))
               for q in re.finditer(r'<pin name="([^"]+)" x="([-\d.]+)" y="([-\d.]+)"', v)]
           for k, v in SYM.items()}
GATE = {}
for dm in re.finditer(r'<deviceset name="([^"]+)"[^>]*>(.*?)</deviceset>', t, re.S):
    for g, s in re.findall(r'<gate name="([^"]+)" symbol="([^"]+)"', dm.group(2)):
        GATE[(dm.group(1), g)] = s
DS = {m.group(1): m.group(2) for m in re.finditer(r'<part name="([^"]+)" library="[^"]+" deviceset="([^"]+)"', t)}


def rp(dx, dy, rot):
    r = re.sub(r"^M", "", rot or "R0")
    x, y = {"R0": (dx, dy), "R90": (-dy, dx), "R180": (-dx, -dy), "R270": (dy, -dx)}[r]
    return (-x, y) if (rot or "").startswith("M") else (x, y)


S = re.findall(r"<sheet name[^>]*>.*?</sheet>", t, re.S)
tot = 0
for si, sh in enumerate(S, 1):
    pins = set()
    for m in re.finditer(r'<instance part="([^"]+)" gate="([^"]+)" x="([-\d.]+)" y="([-\d.]+)"([^>]*)>', sh):
        ix, iy = float(m.group(3)), float(m.group(4))
        rot = (re.search(r'rot="(M?R\d+)"', m.group(5)) or [None, None])[1]
        for pn, px, py in SYMPINS.get(GATE.get((DS.get(m.group(1), ""), m.group(2)), ""), []):
            dx, dy = rp(px, py, rot)
            pins.add((round(ix + dx, 2), round(iy + dy, 2)))
    for nm in re.finditer(r'<net name="([^"]+)" class="[^"]*">(.*?)</net>', sh, re.S):
        W, J = [], set()
        for sg in re.finditer(r"<segment>(.*?)</segment>", nm.group(2), re.S):
            W += [tuple(map(float, q.groups())) for q in re.finditer(
                r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)"', sg.group(1))]
            J |= {(round(float(q.group(1)), 2), round(float(q.group(2)), 2))
                  for q in re.finditer(r'<junction x="([-\d.]+)" y="([-\d.]+)"/>', sg.group(1))}
        pts = collections.Counter()
        for a, b, c, d in W:
            pts[(round(a, 2), round(b, 2))] += 1
            pts[(round(c, 2), round(d, 2))] += 1
        # Candidates are wire ends, pins AND existing dots -- not just ends. A
        # decoupling pin landing straight on a rail has E=0, so enumerating
        # only endpoints never considers it and its dot reads as stray. That
        # was the whole of the "56 strays" this file used to report.
        need = set()
        for p in set(pts) | {q for q in pins} | set(J):
            cnt = pts[p]
            th = sum(1 for a, b, c, d in W
                     if (round(a, 2), round(b, 2)) != p and (round(c, 2), round(d, 2)) != p
                     and ((abs(b - d) < 1e-6 and abs(p[1] - b) < 1e-6 and min(a, c) < p[0] < max(a, c))
                          or (abs(a - c) < 1e-6 and abs(p[0] - a) < 1e-6 and min(b, d) < p[1] < max(b, d))))
            if cnt + 2 * th + (1 if p in pins else 0) >= 3:
                need.add(p)
        if need - J:
            print("   ! s%d %-12s MISSING %s" % (si, nm.group(1), sorted(need - J))); tot += 1
        if J - need:
            print("   ! s%d %-12s STRAY   %s" % (si, nm.group(1), sorted(J - need))); tot += 1
print("junction audit across all %d sheets: %s" % (len(S), "clean" if tot == 0 else "%d findings" % tot))
