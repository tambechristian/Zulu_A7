"""A fan-out ring for a peripheral-pad package -- U2, the FT2232HQ QFN-64.

WHY THIS EXISTS. escape.py builds a ring for U1 and for nothing else, because U1
is the only BGA. But U2 is where the board actually jams. Twenty signals converge
on a 0.5 mm-pitch QFN-64 -- the whole UART group, all six JTAG/config nets on
ADBUS, the EEPROM and the USB pair -- and with no escape structure each of them
invented its own via, during routing, in whatever order the router happened to
reach it. The first net to arrive took the best spot and every via it placed
narrowed the annulus for the next. Measured: JTAG routes 9 of 12 against a clear
board and 1 of 12 the moment the USB group is down. They were not competing for
copper, they were competing for the same few square millimetres of fan-out.

WHAT IT DOES. One via per signal pad, placed OUTWARD along the pad's own edge
normal, all twenty decided together and in perimeter order rather than in router
order, with the depth alternating between two rings so that neighbours do not
line up into a fence. Then a stub from pad to via on the pad's own surface. After
this a route reaches any U2 signal by starting at a via that is already there, on
whatever layer it likes, instead of having to invent one in a crowded annulus.

The geometry is not tight. Twenty signal pads (6 south, 5 east, 5 north, 4 west)
around a 9.6 mm package is about 2 mm of perimeter per via, against the 0.39 mm
that a 0.30 mm via at 0.09 mm clearance actually needs. The old arrangement was
not short of room; it was short of planning.

A DIFFERENTIAL PAIR IS NOT ESCAPED HERE. USB_D_P/USB_D_N leave U2 as one coupled
object with its own rules -- see route_pair in signals.py -- and two independent
vias placed on the pads it wants to start from would be an obstacle to it, not a
service. find_pairs decides which nets those are; they are left alone.
"""
import collections
import io
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import escape as E
import geom as G
import power as P
import signals as S

BRD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "zulu_a7.brd")
PART = os.environ.get("QFN_PART", "U2")
STUB_W = S.STUB_W
VIA_D, VIA_L = P.VIA_D, P.VIA_L
# Two rings, alternating. One ring at a single depth puts every via on one line,
# which is a fence: nothing can cross it to reach the pads behind. Staggering
# opens a gap between every pair of neighbours.
RINGS = (float(os.environ.get("QFN_R0", "1.00")),
         float(os.environ.get("QFN_R1", "1.55")))
# Anything matching this is left to ground.py and power.py, which pour and stitch
# it. A rail does not want a signal fan-out.
VIA_XY = re.compile(r'<via x="([-0-9.]+)" y="([-0-9.]+)"')
QFN_NEAR = float(os.environ.get("QFN_NEAR", "2.5"))
POWERNET = re.compile(r"^(GND|VCC|VDD|\+|USB5V0|VU|VEXT|FT-V|AGND|GNDADC)", re.I)


def signal_pads(b, part):
    """the part's pads that carry a signal, with net, half-extents and side"""
    own = set((round(x, 3), round(y, 3)) for x, y in G.element_pads(b).get(part, []))
    out = []
    for rec in E.board_copper(b, skip=()):
        net, x, y, hx, hy, side = rec[:6]
        if (round(x, 3), round(y, 3)) not in own:
            continue
        if net is None or POWERNET.match(net):
            continue
        out.append((x, y, net, hx, hy, side))
    return out


def outward(x, y, cx, cy):
    """unit normal of the package edge this pad sits on

    By edge, not by radius: on a square package the vector from the centre to a
    pad near a corner points diagonally, and a via pushed diagonally lands in the
    corner where two edges' worth of vias are already trying to fit.
    """
    dx, dy = x - cx, y - cy
    return (1.0, 0.0) if dx > abs(dy) else (-1.0, 0.0) if -dx > abs(dy) else \
           (0.0, 1.0) if dy > 0 else (0.0, -1.0)


def main():
    b = io.open(BRD, encoding="utf-8", errors="replace").read()
    clr = float(re.search(r'<param name="mdWireWire" value="([\d.]+)mm"/>',
                          b).group(1))
    w20 = re.findall(r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)"'
                     r' y2="([-\d.]+)" width="[\d.]+" layer="20"/>', b)
    xs = [float(q) for v in w20 for q in (v[0], v[2])]
    ys = [float(q) for v in w20 for q in (v[1], v[3])]
    bx = (min(xs), min(ys), max(xs), max(ys))

    pads = signal_pads(b, PART)
    if not pads:
        print("no signal pads found on %s" % PART)
        return 1
    px = [p[0] for p in pads]
    py = [p[1] for p in pads]
    cx, cy = (min(px) + max(px)) / 2.0, (min(py) + max(py)) / 2.0

    paired = G.find_pairs({p[2] for p in pads})
    skip = {n for n in paired}
    todo = [p for p in pads if p[2] not in skip]
    print("%s: %d signal pad(s), %d left to the pair router (%s)"
          % (PART, len(pads), len(pads) - len(todo),
             ", ".join(sorted(skip)) or "none"))

    # PERIMETER ORDER, not net order. Neighbours decided next to each other keep
    # their vias next to each other; decided far apart they interleave, and an
    # interleaved ring is what the router was producing on its own.
    todo.sort(key=lambda q: math.atan2(q[1] - cy, q[0] - cx))

    cache = {}

    def model(net, side):
        if (net, side) not in cache:
            cache[(net, side)] = G.copper_model(b, net, side)
        return cache[(net, side)]

    extra, placed, missed, already = [], [], [], []
    for i, (x, y, net, hx, hy, sd) in enumerate(todo):
        side = 16 if sd == 16 else 1
        want = RINGS[i % len(RINGS)]
        v = S.place_via(x, y, model(net, None), model(net, side), clr, bx,
                        extra, (outward(x, y, cx, cy), want))
        if v is None:
            missed.append(net)
            continue
        extra.append((v[0], v[1], VIA_L / 2.0))
        extra += G.sample((x, y), v, STUB_W / 2.0)
        placed.append((net, (x, y), v, str(side)))

    print("   %d via(s) placed, %d pad(s) could not take one" % (len(placed), len(missed)))
    if missed:
        print("   **** no room: %s" % ", ".join(sorted(missed)))
    depth = collections.Counter(
        round(math.hypot(v[0] - p[0], v[1] - p[1]), 2) for _n, p, v, _s in placed)
    print("   depths: %s" % ", ".join("%.2f mm x%d" % q for q in sorted(depth.items())))

    if "--apply" not in sys.argv:
        print("\nreport only -- re-run with --apply to write it into the board")
        return 0

    # A PAD THAT IS ALREADY ESCAPED IS SKIPPED, NOT AN ERROR. This tool now runs
    # AFTER the USB group, because the differential pair has to choose its
    # corridor before eighteen vias are dropped around it -- placed first, the
    # ring left USB_D_N a 40.6 mm detour against USB_D_P's 16.9, which is 23.7 mm
    # of skew on a 1.27 mm budget and no working USB at all. So some U2 pads
    # already carry a via by the time we get here. Those are done; leave them.
    keep = []
    for net, pd, v, sl in placed:
        m = re.search(r'<signal name="%s"[^>]*>(.*?)</signal>' % re.escape(net), b, re.S)
        near = [q for q in re.finditer(VIA_XY, m.group(1))
                if math.hypot(float(q.group(1)) - pd[0],
                              float(q.group(2)) - pd[1]) < QFN_NEAR]
        (keep if not near else already).append((net, pd, v, sl))
    if already:
        print('   %d pad(s) already escaped, left alone: %s'
              % (len(already), ', '.join(sorted(n for n, _p, _v, _s in already))))
    placed = keep

    g, out, nv, nw = E.g, b, 0, 0
    for net, p, v, slay in placed:
        add = ['<via x="%s" y="%s" extent="1-16" drill="%s" diameter="%s"/>'
               % (g(v[0]), g(v[1]), g(VIA_D), g(VIA_L))]
        nv += 1
        add.append('<wire x1="%s" y1="%s" x2="%s" y2="%s" width="%s" layer="%s"/>'
                   % (g(p[0]), g(p[1]), g(v[0]), g(v[1]), g(STUB_W), slay))
        nw += 1
        m = re.search(r'(<signal name="%s"[^>]*>)' % re.escape(net), out)
        out = out[:m.end()] + "".join(add) + out[m.end():]
    import xml.etree.ElementTree as ET
    ET.fromstring(out)
    io.open(BRD, "w", encoding="utf-8", newline="").write(out)
    print("\nwrote %d wires and %d vias into %s" % (nw, nv, BRD))
    return 0


if __name__ == "__main__":
    sys.exit(main())
