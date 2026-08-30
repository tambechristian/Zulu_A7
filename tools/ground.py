# -*- coding: utf-8 -*-
"""Pour ground on L1 and L6 and stitch it to the L2 and L4 planes.

    python tools/ground.py            report only, writes nothing
    python tools/ground.py --apply    write the pour and the stitching vias

RUN IT LAST, after everything that routes:

    make_board.py --fab jlcpcb        regenerates <signals> EMPTY
        -> escape.py --apply          the BGA fan-out, U1
        -> escape_qfn.py --apply      the QFN fan-out, U2
        -> power.py --apply           the five rails
        -> signals.py GRP --apply     sdram, x2, usb, microsd, jtag, in that
                                      order -- see the note below
        -> ground.py --apply          the pour and the stitching, LAST

WHY GROUND GOES LAST, which is a change. It used to run straight after
escape.py, on the reasoning that the pour should be down before anything routed
through it. That is backwards. The pour itself does not care -- a <polygon> is
an outline plus rules and Eagle fills it at ratsnest time, so it follows the
routing whenever it is written. The STITCHING is the problem: it is a grid of
through holes, and a through hole blocks every layer. Run before power.py, 85
stitching vias at 2.60 mm pitch sealed the corridors VCC1V0 needed across the
regulator corner and the rail did not close -- two edges with no path on any of
L16/L1/L3. Run afterwards it placed 78 and simply worked around the traces.
Stitching is opportunistic and takes whatever grid positions are left; a rail
has to go where it has to go. The one that yields goes last.

Worth being exact about the size of this: it was decisive for power.py and it
was NOT what held the signal groups back. Moving ground after signals.py too
changed the SDRAM bus from 29 of 39 nets to 28, which is noise.

WHAT A POUR IS IN AN EAGLE FILE. Not copper. A <polygon> inside a <signal> is an
OUTLINE plus a set of rules -- isolate, rank, thermals, orphans -- and Eagle
computes the filled shape itself, at ratsnest time, against whatever else is on
the board at that moment. So this file draws two rectangles and gets out of the
way; the fill follows the routing rather than freezing it. Nothing here has to
be redone when the remaining signals are routed.

WHY L1 AND L6 AT ALL, when L2 and L4 are already solid ground. Three reasons,
and only the first is about current:

  1. The escape drops 157 vias through the board. Every one of them is a stub
     into the planes, and the return current for a signal changing layers has to
     get from one reference to the other. A stitching via beside it is that path.
  2. Copper balance. A board that is bare on the outside and solid inside warps
     in reflow, and 0.5 mm pitch BGA assembly is the last place to want that.
  3. The outer layers are where the parts are, and a pour under a part is a
     shorter return path than one two dielectrics away.

WHAT THIS DOES NOT DO. It does not decide the L5 split. L5 is the power layer,
split three ways between VCC1V0, VCC1V8 and VCC3V3, and that split is a
different question -- a planelet only has to reach its own vias, not stay
continuous. tools/check_planes.py says so in its own header and still declines
to check L5 for the same reason.
"""

import re, io, os, sys, math, collections

# Import escape FIRST and take its stdout wrapper rather than making a second
# one. Both files reach for sys.stdout.buffer, and two TextIOWrappers over the
# same buffer means the first one closes it when it is collected -- every print
# after that raises "I/O operation on closed file" from a line that has nothing
# to do with the cause.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import escape as E                                          # noqa: E402
import geom as G   # noqa: E402

ROOT = E.ROOT
BRD = E.BRD
APPLY = "--apply" in sys.argv

# What gets poured where. L1 and L16 are signal layers and the pour fills the
# gaps between traces; L5 is a plane layer and the pour IS the layer.
# L2 IS POURED HERE NOW, AND IT NEVER WAS. Nothing in this toolchain had ever
# written copper to L2 or L4 -- no wires, no polygons -- while the whole stackup
# rested on "L2 and L4 are solid ground" and check_planes tested them
# ANALYTICALLY, modelling them rather than reading them. Gerbers would have gone
# out with two bare inner layers. Christian asked whether L3 and L4 were being
# used, which is how it surfaced.
#
# L4 IS NOT HERE, deliberately: it becomes a SIGNAL layer. The board has three
# signal layers on paper (L1, L3, L6) but L1 is spent entirely on the escape --
# 1314 wires, all short stubs from ball to fan-out ring -- so everything else
# was competing for two. sig/GND/sig/sig/PWR/sig is a standard six-layer stack
# and it makes that three. L3 keeps L2 above it; L4 gets L5 below it; the two
# middle layers route orthogonally.
POURS = (("GND", "1"), ("GND", "2"), ("GND", "16"), ("VCC3V3", "5"))
NET = "GND"                 # the net the stitching vias belong to
EDGE = 0.40                 # pour inset from the board outline, see below
ISOLATE = 0.25              # gap the pour keeps from foreign copper
PW = 0.1524                 # polygon outline width, Eagle's default
VIA_D, VIA_L = 0.2, 0.3     # stitching via, same as the escape's
# Minimum spacing between stitching vias. lambda/20 in FR-4 is 7.2 mm at 1 GHz
# and 3.6 at 2, so 2.60 is already 1.4x tighter than the fastest edge on this
# board needs. Going below it buys nothing electrical and costs real routing
# room: a GND via ties L1/L2/L4/L6 together but it is a HOLE through L3, the
# signal layer, and L5, the split power layer.
PITCH = 2.60
KEEPOUT = 0.20              # extra room around a part body before drilling


def outline(b):
    w = re.findall(r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)"'
                   r' width="[\d.]+" layer="20"/>', b)
    xs = [float(v) for q in w for v in (q[0], q[2])]
    ys = [float(v) for q in w for v in (q[1], q[3])]
    return min(xs), min(ys), max(xs), max(ys)


def obstacles(b, clr):
    """everything a stitching via has to keep away from, as circles and boxes.

    A via is a through hole, so it clears copper on BOTH sides -- side is not a
    filter here the way it is for a surface trace.
    """
    boxes, circles = [], []
    need = VIA_L / 2 + clr
    for onet, ox, oy, ohx, ohy, side in E.board_copper(b, skip=()):
        boxes.append((ox - ohx - need, oy - ohy - need, ox + ohx + need, oy + ohy + need))
    sig = re.search(r"<signals>.*</signals>", b, re.S).group(0)
    for m in re.finditer(r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)"'
                         r' width="([\d.]+)"', sig):
        x1, y1, x2, y2, w = map(float, m.groups())
        circles.append(((x1, y1), (x2, y2), w / 2 + need))
    for x, y, dia in G.vias(b):
        circles.append(((x, y), (x, y), dia / 2 + need))
    # part bodies, so a via is never drilled through a component
    pkg = {}
    for lm in re.finditer(r'<library name="([^"]+)">(.*?)</library>', b, re.S):
        for pm in re.finditer(r'<package name="([^"]+)">(.*?)</package>', lm.group(2), re.S):
            pkg[(lm.group(1), pm.group(1))] = pm.group(2)
    for m in re.finditer(r'<element name="([^"]+)" library="([^"]+)" package="([^"]+)"'
                         r'[^>]*?\sx="([-\d.]+)" y="([-\d.]+)"([^>]*)', b):
        nm, lib, pk = m.group(1), m.group(2), m.group(3)
        ex, ey = float(m.group(4)), float(m.group(5))
        rot = (re.search(r'rot="(M?R\d+)"', m.group(6)) or [None, "R0"])[1]
        if nm == "X2":                      # X2 IS the outline, not an obstacle
            continue
        xs, ys = [], []
        for q in re.finditer(r'<(?:wire|rectangle) ([^>]*)/>', pkg.get((lib, pk), "")):
            if re.search(r'layer="(?:21|39|51)"', q.group(1)):
                xs += [float(v) for v in re.findall(r'\b[xX][12]="([-\d.]+)"', q.group(1))]
                ys += [float(v) for v in re.findall(r'\b[yY][12]="([-\d.]+)"', q.group(1))]
        if not xs:
            continue
        pts = [E.rp_(x, y, rot) if hasattr(E, "rp_") else _rp(x, y, rot)
               for x in (min(xs), max(xs)) for y in (min(ys), max(ys))]
        boxes.append((ex + min(p[0] for p in pts) - KEEPOUT,
                      ey + min(p[1] for p in pts) - KEEPOUT,
                      ex + max(p[0] for p in pts) + KEEPOUT,
                      ey + max(p[1] for p in pts) + KEEPOUT))
    return boxes, circles


def _rp(x, y, rot):
    r = re.sub(r"^M", "", rot)
    x, y = {"R0": (x, y), "R90": (-y, x), "R180": (-x, -y), "R270": (y, -x)}[r]
    return (-x, y) if rot.startswith("M") else (x, y)


def stitch(b, clr, bx0, by0, bx1, by1, step=0.25):
    """via positions: fine scan, greedy, keeping PITCH between any two.

    NOT a rigid grid. A grid at the target pitch throws away every position that
    is blocked by a hair and cannot shuffle sideways to recover it, and on this
    board that is most of them -- it found 36 where this finds 92 at the same
    spacing, and put 21 of the 36 in the right-hand third because that is where
    the empty space happened to line up. Stitching wants to be even; a via in the
    middle of a plane does nothing that a via next to a signal via does.
    """
    boxes, circles = obstacles(b, clr)
    out = []
    lo_x, lo_y = bx0 + EDGE + VIA_L / 2, by0 + EDGE + VIA_L / 2
    hi_x, hi_y = bx1 - EDGE - VIA_L / 2, by1 - EDGE - VIA_L / 2
    tried = 0
    y = lo_y
    while y <= hi_y + 1e-9:
        x = lo_x
        while x <= hi_x + 1e-9:
            tried += 1
            if not any(a[0] <= x <= a[2] and a[1] <= y <= a[3] for a in boxes) \
               and not any(E.seg_pt(p, q, (x, y)) < r for p, q, r in circles) \
               and all((x - c[0]) ** 2 + (y - c[1]) ** 2 >= PITCH * PITCH for c in out):
                out.append((round(x, 4), round(y, 4)))
            x += step
        y += step
    return out, tried


def main():
    b = open(BRD, encoding="utf-8").read()
    clr = float(re.search(r'<param name="mdWireWire" value="([\d.]+)mm"/>', b).group(1))
    bx0, by0, bx1, by1 = outline(b)
    print("board %.2f x %.2f mm, clearance %.3f" % (bx1 - bx0, by1 - by0, clr))
    if not re.search(r'<signal name="%s"[^>]*>' % NET, b):
        print("no %s signal in this board" % NET)
        return 1

    px0, py0 = bx0 + EDGE, by0 + EDGE
    px1, py1 = bx1 - EDGE, by1 - EDGE
    print("")
    print("POURS")
    for net, lay in POURS:
        print("   %-7s on L%-3s %s" % (net, lay,
              "fills between traces" if lay in ("1", "16") else "IS the layer -- solid plane"))
    print("   outline  %.2f, %.2f .. %.2f, %.2f -- inset %.2f from the board edge"
          % (px0, py0, px1, py1, EDGE))
    print("   that is mdCopperDimension %.2f plus half the %.4f outline width, rounded up"
          % (0.30, PW))
    print("   isolate  %.2f mm from foreign copper (the rule floor is %.3f; this is"
          % (ISOLATE, clr))
    print("            wider on purpose, so the fill does not thread slivers between")
    print("            escape traces it can never usefully connect to)")
    print("   thermals yes, orphans no, rank 1")

    vias, tried = stitch(b, clr, bx0, by0, bx1, by1)
    print("")
    print("STITCHING VIAS, %s, %.1f mm drill on a %.2f mm land" % (NET, VIA_D, VIA_L))
    print("   %d of %d grid positions at %.2f mm pitch have room" % (len(vias), tried, PITCH))
    if vias:
        d = [min(math.hypot(a[0] - c[0], a[1] - c[1])
                 for c in vias if c is not a) for a in vias]
        print("   nearest neighbour %.2f .. %.2f mm" % (min(d), max(d)))
        per = collections.Counter("left" if v[0] < bx1 / 3 else
                                  "middle" if v[0] < 2 * bx1 / 3 else "right" for v in vias)
        print("   spread across the board: %s" % dict(per))
    print("   they are through holes, so each one ties L1, L2, L4 and L6 together")
    print("   at a stroke; L3 and L5 take an antipad.")
    # Drill count is a real cost step at JLCPCB and this crosses it.
    pk = {}
    for lm in re.finditer(r'<library name="([^"]+)">(.*?)</library>', b, re.S):
        for pm in re.finditer(r'<package name="([^"]+)">(.*?)</package>', lm.group(2), re.S):
            pk[(lm.group(1), pm.group(1))] = pm.group(2)
    pads = sum(len(re.findall(r"<pad ", pk.get((m.group(1), m.group(2)), "")))
               for m in re.finditer(r'<element name="[^"]+" library="([^"]+)" package="([^"]+)"', b))
    have = len(re.findall(r"<via ", b)) + pads
    area = (bx1 - bx0) * (by1 - by0) / 1e6
    thr = 150000 * area
    print("")
    print("DRILL COUNT, and this crosses a price step")
    print("   %d holes on the board now (%d escape vias + %d plated pads)"
          % (have, have - pads, pads))
    print("   %+d stitching vias -> %d" % (len(vias), have + len(vias)))
    print("   JLCPCB surcharge above 150,000 holes/m2; at %.6f m2 that is %d holes."
          % (area, thr))
    print("   %s" % ("under it before, over it after -- the stitching is what "
                     "crosses the line" if have <= thr < have + len(vias) else
                     "already over it, so these add nothing" if have > thr else
                     "still under it"))

    if not APPLY:
        print("")
        print("report only -- re-run with --apply to write it into the board")
        return 0

    if re.search(r'<signal name="%s"[^>]*>\s*<polygon' % NET, b) or \
            re.search(r'<polygon[^>]*layer="(?:1|16)"', re.search(r"<signals>.*</signals>", b, re.S).group(0)):
        print("")
        print("REFUSING TO APPLY: this board already carries a pour.")
        print("Run make_board.py and escape.py --apply again first.")
        return 1

    g = E.g
    v = "".join('<vertex x="%s" y="%s"/>' % (g(x), g(y))
                for x, y in ((px0, py0), (px1, py0), (px1, py1), (px0, py1)))
    out = b
    for net, lay in POURS:
        m = re.search(r'(<signal name="%s"[^>]*>)' % re.escape(net), out)
        if not m:
            print("no %s signal; skipped L%s" % (net, lay))
            continue
        # A plane layer is poured WITHOUT thermals: a plane exists to be low
        # impedance and a thermal spoke is four narrow necks in series with it.
        # L1 and L16 keep thermals because those pads are hand-reworkable and a
        # pad tied straight into a pour is a soldering iron's worst afternoon.
        th = "no" if lay == "5" else "yes"
        out = (out[:m.end()]
               + '<polygon width="%s" layer="%s" isolate="%s" rank="1" thermals="%s"'
                 ' orphans="no">%s</polygon>' % (g(PW), lay, g(ISOLATE), th, v)
               + out[m.end():])
    m = re.search(r'(<signal name="%s"[^>]*>)' % NET, out)
    add = ['<via x="%s" y="%s" extent="1-16" drill="%s" diameter="%s"/>'
           % (g(x), g(y), g(VIA_D), g(VIA_L)) for x, y in vias]
    out = out[:m.end()] + "".join(add) + out[m.end():]
    import xml.etree.ElementTree as ET
    ET.fromstring(out)
    open(BRD, "w", encoding="utf-8").write(out)
    print("")
    print("wrote %d polygons and %d stitching vias into %s" % (len(POURS), len(vias), BRD))
    return 0


if __name__ == "__main__":
    sys.exit(main())
