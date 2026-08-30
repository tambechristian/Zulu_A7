# -*- coding: utf-8 -*-
"""Give every stranded surface GND pad its own via down to the planes.

WHY. Eagle's ratsnest wants 107 airwires on this board and 57 of them are GND.
They are not a routing shortfall and they are not a pour-quality problem: they
are 63 SMD ground pads -- decoupling caps, mostly -- that have no via under
them. Of the 64 pad locations the ratsnest still wants, exactly 2 have a GND
via within 1.0 mm. There are 151 GND vias on the board and essentially none of
them are AT a pad.

What has been holding those pads to ground is the surface pour, and on L16 the
surface pour is 220 pieces of which 89.6 % reach GND. That is the wrong
instrument for the job. A decoupling capacitor whose ground pad reaches the
plane only through a fragmented surface fill has a return path that defeats the
point of fitting the capacitor -- and it explains the pour's own fragmentation
too, since the fill is being asked to do the tying-down that vias should do.

WHAT THIS IS NOT. stitch_pour.py puts one via into each ORPHANED PIECE of the
fill, which is about making the copper that is already there electrically real.
This is about the pads, and it runs against Eagle's own verdict -- the layer-19
airwires it last wrote -- rather than against a raster of the pour.

The geometry is power.py's: OFFSET 0.70 mm from the pad and a 0.30 mm stub on
the pad's own surface layer. The clearance model is geom.copper_model's --
pads as a covering chain of discs, wires sampled along their length -- which is
check_board's and stitch_pour's, rasterised through power.Maze so that checking
thousands of obstacles per candidate stays affordable. Grading a fix with a
different model than the checker uses is how you get a fix that is not one.

WHAT THIS PASS CANNOT DO, MEASURED. Of the 58 pads it is asked to stitch it
finds room for 14. Three obstacle models were tried and they agree the room is
not there: power.via_for's circumscribed-circle model found 10, the same with a
sweep four times finer found 16, and geom's exact model found 14. The board is
91.8 % routed with 6416 wires and 879 vias, at 0.09 mm clearance, and a 0.30 mm
via with its annulus does not fit beside most of these pads at any radius out to
2.4 mm.

AND THE BINDING CONSTRAINT IS THE STUB, NOT THE VIA. Searching rings out to
6.0 mm instead of 2.4 places exactly the same 14 vias, and the longest stub it
accepts is still 2.10 mm. The extra room is reachable; the straight line to it
is not. A stub has to clear everything on the pad's own layer along its whole
length, and on a 91.8 %-routed surface a straight line of any length runs into
something almost at once.

So the other 44 do not want a bigger radius, a tighter clearance or a smaller
drill. They want a stub that is allowed to TURN -- a short maze-routed path on
the pad's layer, which power.py already has the router for -- or they want a
via anywhere on the pad's own pour island, which is stitch_pour.py's machinery
seeded from pads instead of from island detection. Either is a real piece of
work. Neither is this file.

    python tools/stitch_pads.py            report
    python tools/stitch_pads.py --apply    write the vias and stubs

AFTER APPLYING, THE AIRWIRE COUNT IN THE FILE IS STALE. Layer 19 is whatever
Eagle last computed; nothing here rewrites it. Open the board and let Fusion
recompute the ratsnest to see the count move.
"""
import io
import math
import os
import re
import sys
import collections
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import escape as E
import geom as G
import power as P

_prev_stdout = sys.stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRD = os.path.join(ROOT, "zulu_a7.brd")
NET = os.environ.get("STITCH_NET", "GND")
# U1's balls are the escape's business. power.pads_of explains what happens if
# you forget: a via 0.70 mm from each ball lands inside the stage-2 moat, and
# eight extra vias in there islanded the ground copper under the 7 x 7 core.
SKIP = ("U1",)
# A FINER SWEEP THAN power.py's. That one places a handful of vias on a board
# with nothing on it yet; this one is squeezing between 6416 wires and 879
# vias, where the gaps are narrower than the 7.5 degrees a 48-sample ring can
# resolve. Radii go out to 2.4 mm because a stub is cheap and an unstitched
# decoupling cap is not -- but the sweep is still nearest-first, so a pad with
# room at 0.70 mm still gets it there.
RADII = tuple(round(0.70 + 0.10 * k, 2)
              for k in range(int(os.environ.get("STITCH_RINGS", "18"))))
SAMPLES = 192


def element_of(b):
    """(x, y) -> element name, for the report only"""
    pkg = {}
    for lm in re.finditer(r'<library name="([^"]+)">(.*?)</library>', b, re.S):
        for pm in re.finditer(r'<package name="([^"]+)">(.*?)</package>',
                              lm.group(2), re.S):
            pkg[(lm.group(1), pm.group(1))] = pm.group(2)

    def rp(x, y, rot):
        r = re.sub(r"^M", "", rot)
        x, y = {"R0": (x, y), "R90": (-y, x), "R180": (-x, -y), "R270": (y, -x)}[r]
        return (-x, y) if rot.startswith("M") else (x, y)

    out = {}
    for m in re.finditer(r'<element name="([^"]+)" library="([^"]+)" package="([^"]+)"'
                         r'[^>]*x="([-\d.]+)" y="([-\d.]+)"(?:[^>]*rot="([^"]+)")?', b):
        nm, lib, pk = m.group(1), m.group(2), m.group(3)
        ex, ey, rot = float(m.group(4)), float(m.group(5)), m.group(6) or "R0"
        for s in re.finditer(r'<(?:smd|pad) name="[^"]+" x="([-\d.]+)" y="([-\d.]+)"',
                             pkg.get((lib, pk), "")):
            a = rp(float(s.group(1)), float(s.group(2)), rot)
            out[(round(ex + a[0], 2), round(ey + a[1], 2))] = nm
    return out


def targets(b):
    """the pads Eagle's ratsnest still wants, as (x, y, side)

    Eagle's verdict, not a re-derivation of it: a layer-19 wire in the signal
    is the airwire it drew, and its endpoints are the things it could not find
    copper between. Matching those to pads of this net gives the work list.
    """
    sig = re.search(r"<signals>(.*)</signals>", b, re.S).group(1)
    m = re.search(r'<signal name="%s"[^>]*>(.*?)</signal>' % re.escape(NET), sig, re.S)
    if not m:
        return []
    pads = {}
    for onet, x, y, _hx, _hy, side in E.board_copper(b, skip=()):
        if onet == NET:
            pads[(round(x, 2), round(y, 2))] = (x, y, side)
    seen, out = set(), []
    for w in re.finditer(r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)"'
                         r' y2="([-\d.]+)"[^>]*layer="19"', m.group(1)):
        a, c, d, e = [float(q) for q in w.groups()]
        for p in ((round(a, 2), round(c, 2)), (round(d, 2), round(e, 2))):
            if p in pads and p not in seen:
                seen.add(p)
                out.append(pads[p])
    return out


def freept(mz, x, y):
    i, j = mz.i(x), mz.j(y)
    return 0 <= i < mz.W and 0 <= j < mz.H and bool(mz.free[j * mz.W + i])


def freeseg(mz, a, c, step=0.05):
    """the whole stub, not just its ends -- it is the ends that are safe"""
    n = max(2, int(math.hypot(c[0] - a[0], c[1] - a[1]) / step) + 1)
    for k in range(n + 1):
        t = k / float(n)
        if not freept(mz, a[0] + (c[0] - a[0]) * t, a[1] + (c[1] - a[1]) * t):
            return False
    return True


def spot_for(px, py, vmz, smz, mine, clr, bx):
    """nearest clear via position on a ring around the pad, with its stub"""
    for rad in RADII:
        best = None
        for k in range(SAMPLES):
            a = 2 * math.pi * k / float(SAMPLES)
            x, y = px + rad * math.cos(a), py + rad * math.sin(a)
            if not (bx[0] + 0.5 < x < bx[2] - 0.5 and bx[1] + 0.5 < y < bx[3] - 0.5):
                continue
            if not freept(vmz, x, y):
                continue
            if any(math.hypot(x - vx, y - vy) < P.VIA_L + clr - 1e-9
                   for vx, vy in mine):
                continue
            if not freeseg(smz, (px, py), (x, y)):
                continue
            d = math.hypot(x - px, y - py)
            if best is None or d < best[0]:
                best = (d, (round(x, 4), round(y, 4)))
        if best:
            return best[1]
    return None


def main():
    raw = io.open(BRD, "rb").read()
    eol = "\r\n" if b"\r\n" in raw else "\n"
    b = raw.decode("utf-8")
    clr = float(re.search(r'<param name="mdWireWire" value="([\d.]+)mm"/>', b).group(1))
    w20 = re.findall(r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)"'
                     r' y2="([-\d.]+)" width="[\d.]+" layer="20"/>', b)
    xs = [float(q) for v in w20 for q in (v[0], v[2])]
    ys = [float(q) for v in w20 for q in (v[1], v[3])]
    bx = (min(xs), min(ys), max(xs), max(ys))

    own = element_of(b)
    tgt = targets(b)
    mine = [(x, y) for x, y, _d in G.vias(
        re.search(r'<signal name="%s"[^>]*>(.*?)</signal>' % re.escape(NET),
                  b, re.S).group(1))]
    # a via must clear foreign copper on EVERY layer; a stub only on its own
    vmz = P.Maze(G.obstacles(b, frozenset((NET,)), None, ()), bx, clr,
                 P.VIA_L, 0.05)
    smz = {sd: P.Maze(G.obstacles(b, frozenset((NET,)), sd, ()), bx, clr,
                      P.STUB_W, 0.05) for sd in (1, 16)}

    print("%s: ratsnest wants %d pad location(s), clearance %.3f mm"
          % (NET, len(tgt), clr))
    vias, stubs = [], []
    skipped = collections.Counter()
    miss = []
    for px, py, side in tgt:
        nm = own.get((round(px, 2), round(py, 2)), "?")
        if nm in SKIP:
            skipped["%s -- the escape owns its balls" % nm] += 1
            continue
        if side == 0:
            skipped["plated hole (spans every layer already)"] += 1
            continue
        if min((math.hypot(px - vx, py - vy) for vx, vy in mine),
               default=9e9) < 0.01:
            skipped["already has a via on it"] += 1
            continue
        sd = 16 if side == 16 else 1
        v = spot_for(px, py, vmz, smz[sd], mine + vias, clr, bx)
        if v is None:
            miss.append((nm, px, py, sd))
            continue
        vias.append(v)
        # SNAP THE PAD END TO 3 dp, WHICH IS check_board's COMPARISON PRECISION.
        # It decides a wire end is connected by matching round(x, 3) against
        # round(pad_centre, 3). A pad centre of 29.82050000001 gets written by
        # E.g as "29.8205" -- exactly on the half-thousandth boundary -- and the
        # two roundings then disagree, so a stub sitting dead centre on its pad
        # reports as connecting to nothing. 2 of the first 14 landed there.
        # Rounding first makes the written value a fixed point of round(_, 3),
        # and 0.0005 mm inside a pad with a 0.35 mm half-extent is nothing.
        stubs.append(((round(px, 3), round(py, 3)), v, str(sd)))

    for k, n in skipped.most_common():
        print("   skipped %2d: %s" % (n, k))
    top = sum(1 for _a, _c, l in stubs if l == "1")
    print("   placed %d via(s) + %d stub(s) of %.2f mm  (L1 %d, L16 %d)%s"
          % (len(vias), len(stubs), P.STUB_W, top, len(stubs) - top,
             "" if not stubs else
             ": " + ", ".join("%s at (%.2f,%.2f) L%s"
                              % (own.get((round(a[0], 2), round(a[1], 2)), "?"),
                                 a[0], a[1], l) for a, _c, l in stubs)))
    if miss:
        print("   NO ROOM for %d pad(s):" % len(miss))
        for nm, px, py, sd in miss:
            print("      %-8s at (%.2f, %.2f) L%d" % (nm, px, py, sd))
    if not vias:
        print("\nnothing to stitch")
        return 0
    d = [math.hypot(v[0] - s[0][0], v[1] - s[0][1]) for s, v in zip(stubs, vias)]
    print("   stub length: min %.2f, median %.2f, max %.2f mm"
          % (min(d), sorted(d)[len(d) // 2], max(d)))

    if "--apply" not in sys.argv:
        print("\nreport only -- re-run with --apply to write "
              "%d via(s) and %d stub(s)" % (len(vias), len(stubs)))
        return 0

    g = E.g
    add = []
    for x, y in vias:
        add.append('<via x="%s" y="%s" extent="1-16" drill="%s" diameter="%s"/>'
                   % (g(x), g(y), g(P.VIA_D), g(P.VIA_L)))
    for a, c, lay in stubs:
        add.append('<wire x1="%s" y1="%s" x2="%s" y2="%s" width="%s" layer="%s"/>'
                   % (g(a[0]), g(a[1]), g(c[0]), g(c[1]), g(P.STUB_W), lay))
    m = re.search(r'(<signal name="%s"[^>]*>)' % re.escape(NET), b)
    out = b[:m.end()] + "".join(add) + b[m.end():]
    ET.fromstring(out)
    io.open(BRD, "wb").write(out.encode("utf-8"))
    print("\nwrote %d via(s) and %d stub(s) into %s (%s preserved)"
          % (len(vias), len(stubs), BRD, "CRLF" if eol == "\r\n" else "LF"))
    print("layer 19 in the file is now STALE -- recompute the ratsnest in Fusion")
    return 0


if __name__ == "__main__":
    sys.exit(main())
