# -*- coding: utf-8 -*-
"""Rip the one wire standing on a stranded GND pad's via site, then put it back.

WHY A RIP-UP AT ALL, AND WHY THIS SMALL A ONE. 30 GND pads are left that no
via and no same-layer trace can reach. The full re-route that was on the table
would have discarded 6584 wires -- including Fusion's 2 h 47 m autoroute -- to
make room for 30 vias. Measuring first showed that is wildly out of proportion:

    wires blocking the cheapest via site       pads
    0                                            5
    1                                           20
    2                                            3
    3                                            2

Thirty-two segments, across about twelve nets, stand between this board and
every one of those pads. That is 0.5 % of the copper, not all of it.

HOW IT STAYS SAFE. Each pad is done as a transaction. Rip its blockers, place
the via and stub, then re-route every ripped segment END TO END on its own layer
around the new via -- the endpoints are where that segment met the rest of its
net, so restoring them restores the net exactly. If any re-route fails, the
whole pad is rolled back and the board is untouched. A pad that cannot be served
without leaving a net broken is not served.

Pads are taken cheapest-first so the easy ones bank their vias before the
expensive ones start competing for room.

    python tools/ripup_stitch.py            report: cost per pad, nothing written
    python tools/ripup_stitch.py --apply    do it

Layer 19 is stale afterwards -- recompute the ratsnest in Fusion.
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
import stitch_traces as ST

_prev_stdout = sys.stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRD = os.environ.get("STITCH_BOARD", os.path.join(ROOT, "zulu_a7.brd"))
NET = os.environ.get("RIPUP_NET", "GND")
STUB_W = float(os.environ.get("RIPUP_STUB_W", str(P.STUB_W)))
SKIP = ("U1",)
RADII = [0.0] + [round(0.70 + 0.05 * k, 2) for k in range(17)]
SAMPLES = 96
MAXRIP = int(os.environ.get("RIP_MAX", "3"))
STEP = 0.1


def wires_of(sig, skip_net=None):
    """every copper wire as (net, layer, a, c, halfwidth, RAW TEXT).

    THE RAW TEXT IS THE POINT. The first cut rebuilt the element from its
    parsed numbers when it came time to rip, and the rebuilt string matched
    nothing: Eagle does not write every wire the way E.g formats one, and a
    single differing attribute or decimal makes the replace a no-op. Twelve of
    twenty-eight pads failed that way. Keep the span that was actually matched
    and ripping is exact by construction.
    """
    out = []
    for m in re.finditer(r'<signal name="([^"]+)"[^>]*>(.*?)</signal>', sig, re.S):
        if m.group(1) == skip_net:
            continue
        for w in re.finditer(r'<wire[^>]*/>', m.group(2)):
            a = dict(re.findall(r'(\w+)="([^"]*)"', w.group(0)))
            if "layer" not in a or not 1 <= int(a["layer"]) <= 16:
                continue
            if "curve" in a:            # an arc; re-laying it as a polyline
                continue                # would change the geometry, so leave it
            out.append((m.group(1), int(a["layer"]),
                        (float(a["x1"]), float(a["y1"])),
                        (float(a["x2"]), float(a["y2"])),
                        float(a["width"]) / 2.0, w.group(0)))
    return out


def statics(b):
    """copper that cannot be ripped: foreign pads, plated holes, every via.

    THE SAME SET clash() GRADES WITH, minus the wires -- which is the whole
    point of building it this way. The first cut assembled it by hand from
    board_copper and missed vias out of the stub's obstacle list, so site_for
    would happily lay a stub across a foreign via and the verifier would then
    refuse the transaction. Every pad rolled back. copper_model returns rects,
    circs and segs; take the first two and let the caller treat segs as the
    rippable ones, and the search and the check cannot disagree.
    """
    rects, circs, _segs = G.copper_model(b, frozenset((NET,)), None)
    out = G.as_circles(rects) + list(circs)
    surf = {}
    for sd in (1, 16):
        r2, c2, _s2 = G.copper_model(b, frozenset((NET,)), sd)
        surf[sd] = G.as_circles(r2) + list(c2)
    return out, surf


def site_for(px, py, sd, stat, surf, wires, clr, drills, drill_spacing, placed):
    """cheapest via spot: fewest rippable wires on the via AND on its stub"""
    vn, sn = P.VIA_L / 2 + clr, STUB_W / 2 + clr
    best = None
    for rad in RADII:
        samples = 1 if rad == 0.0 else SAMPLES
        for k in range(samples):
            a = 2 * math.pi * k / float(samples)
            x, y = px + rad * math.cos(a), py + rad * math.sin(a)
            if any(math.hypot(x - ox, y - oy) < r + vn - 1e-9 for ox, oy, r in stat):
                continue
            if any(math.hypot(x - ox, y - oy) < P.VIA_L + clr - 1e-9
                   for ox, oy in placed):
                continue
            if any(math.hypot(x - ox, y - oy) < drill_spacing - 1e-9
                   for ox, oy in drills):
                continue
            if any(E.seg_pt((px, py), (x, y), (ox, oy)) < r + sn - 1e-9
                   for ox, oy, r in surf[sd]):
                continue
            bad = []
            for q in wires:
                if E.seg_pt(q[2], q[3], (x, y)) < q[4] + vn - 1e-9:
                    bad.append(q)
                elif q[1] == sd and E.seg_seg((px, py), (x, y), q[2], q[3]) \
                        < q[4] + sn - 1e-9:
                    bad.append(q)
            if best is None or len(bad) < len(best[1]):
                best = ((round(x, 4), round(y, 4)), bad)
            if not bad:
                return best
        if best and not best[1]:
            return best
    return best


def clash(txt, net, lay, a, c, halfw, clr):
    """new copper measured against the board it just produced.

    geom.obstacles is check_board's model: pads as a covering chain of discs,
    wires sampled along their length, this net's own copper left out. lay=None
    is the via case, which must clear every layer. Conservative where it differs
    -- a disc chain contains the rectangle it covers -- and being refused a
    legal spot costs one pad, while being allowed an illegal one costs a board.
    """
    for ox, oy, r in G.obstacles(txt, frozenset((net,)), lay, ()):
        if E.seg_pt(a, c, (ox, oy)) < r + clr + halfw - 1e-9:
            return True
    return False


def main():
    b = io.open(BRD, "rb").read().decode("utf-8")
    clr = G.rule_mm(b, "mdWireWire")
    plan_clr = clr + 0.005
    drill_spacing = P.VIA_D + G.rule_mm(b, "mdDrill")
    w20 = re.findall(r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)"'
                     r' y2="([-\d.]+)" width="[\d.]+" layer="20"/>', b)
    xs = [float(q) for v in w20 for q in (v[0], v[2])]
    ys = [float(q) for v in w20 for q in (v[1], v[3])]
    bx = (min(xs), min(ys), max(xs), max(ys))

    sig = re.search(r"<signals>(.*)</signals>", b, re.S).group(1)
    gm = re.search(r'<signal name="%s"[^>]*>(.*?)</signal>' % NET, sig, re.S)
    vias = [(x, y) for x, y, _d in G.vias(gm.group(1))]
    holes = [(r[1], r[2]) for r in E.board_copper(b, skip=())
             if r[0] == NET and r[5] == 0]
    ground = {
        sd: G.surface_reach(gm.group(1), sd, vias + holes)
        for sd in (1, 16)
    }
    own = ST.element_of(b)

    pads = []
    targets = (ST.targets(b) if NET == "GND"
               else P.pads_of(b, NET, skip=()))
    for px, py, side in targets:
        nm = own.get((round(px, 2), round(py, 2)), "?")
        if nm in SKIP or side == 0:
            continue
        sd = 16 if side == 16 else 1
        if (round(px, 2), round(py, 2)) in ground[sd]:
            continue
        pads.append((nm, px, py, sd))

    stat, surf = statics(b)
    drills = [(x, y) for x, y, _d in G.vias(b)]
    wires = wires_of(sig, skip_net=NET)
    print("%s: %d stranded pad(s), %d foreign wire(s), clearance %.3f"
          % (NET, len(pads), len(wires), clr))

    plan = []
    for nm, px, py, sd in pads:
        s = site_for(px, py, sd, stat, surf, wires, plan_clr,
                     drills, drill_spacing, [])
        plan.append((nm, px, py, sd, s))
    hist = collections.Counter()
    for _nm, _px, _py, _sd, s in plan:
        hist[len(s[1]) if s else 99] += 1
    print("   wires blocking the cheapest site:")
    for k in sorted(hist):
        print("      %s wire(s): %d pad(s)" % ("no site" if k == 99 else k, hist[k]))
    doable = [q for q in plan if q[4] and len(q[4][1]) <= MAXRIP]
    rips = sorted({(q[0], q[1], q[2], q[3], q[4]) for p in doable for q in p[4][1]})
    print("   %d pad(s) at <= %d rip(s); %d distinct segment(s) to rip and re-lay"
          % (len(doable), MAXRIP, len(rips)))
    byn = collections.Counter("L%d %s" % (q[1], q[0]) for q in rips)
    for k, v in byn.most_common(12):
        print("      %-24s %d segment(s)" % (k, v))

    if "--apply" not in sys.argv:
        print("\nreport only -- re-run with --apply to rip, stitch and re-lay")
        return 0

    # ---- transactional: cheapest pads first -------------------------------
    #
    # EVERY TRANSACTION RE-READS THE BOARD. The first cut of this computed the
    # wire list, the statics and every pad's site ONCE, up front, and then
    # applied them in sequence -- so each pad was blind to the copper the pads
    # before it had added and to the segments they had re-laid. Twelve rolled
    # back with "segment text not found" because an earlier pad had already
    # ripped that very segment, and two clearance violations went in because a
    # stub was measured against a board that no longer existed. -0.1875 mm of
    # overlap on a CHAN10 pad is not a rounding argument; it is copper on copper.
    #
    # So the snapshot is rebuilt per pad, the site is chosen against it, and
    # every element the transaction adds is then re-measured against the text it
    # produced. Only then is it kept. A pass that cannot verify itself does not
    # get to write.
    doable.sort(key=lambda q: (len(q[4][1]), q[0]))
    order = [(q[0], q[1], q[2], q[3]) for q in doable]
    out = b
    placed, done, failed = [], [], []
    for nm, px, py, sd in order:
        stat, surf = statics(out)
        drills = [(x, y) for x, y, _d in G.vias(out)]
        wires = wires_of(re.search(r"<signals>(.*)</signals>", out, re.S).group(1),
                         skip_net=NET)
        s = site_for(px, py, sd, stat, surf, wires, plan_clr,
                     drills, drill_spacing, placed)
        if s is None or len(s[1]) > MAXRIP:
            failed.append((nm, "no site within %d rip(s) once the board moved" % MAXRIP))
            continue
        v, bad = s
        txt = out
        ok = True
        for q in bad:                                  # rip
            el = q[5]                                  # the text actually seen
            if el not in txt:
                ok = False
                break
            txt = txt.replace(el, "", 1)
        if not ok:
            failed.append((nm, "segment text not found"))
            continue
        add = '<via x="%s" y="%s" extent="1-16" drill="%s" diameter="%s"/>' % (
            E.g(v[0]), E.g(v[1]), E.g(P.VIA_D), E.g(P.VIA_L))
        if math.hypot(v[0] - px, v[1] - py) > 1e-6:
            add += (
                '<wire x1="%s" y1="%s" x2="%s" y2="%s" width="%s" layer="%d"/>'
                % (E.g(round(px, 3)), E.g(round(py, 3)),
                  E.g(v[0]), E.g(v[1]), E.g(STUB_W), sd))
        gmm = re.search(r'(<signal name="%s"[^>]*>)' % NET, txt)
        txt = txt[:gmm.end()] + add + txt[gmm.end():]
        relaid = []
        for q in bad:                                  # re-lay, around the via
            mz = P.Maze(G.obstacles(txt, frozenset((q[0],)), q[1], ()),
                        bx, plan_clr, q[4] * 2, STEP)
            pts = mz.path(q[2], q[3])
            if not pts or len(pts) < 2:
                ok = False
                break
            seg = []
            for a, c in zip(pts, pts[1:]):
                if math.hypot(c[0] - a[0], c[1] - a[1]) < 1e-9:
                    continue
                seg.append('<wire x1="%s" y1="%s" x2="%s" y2="%s"'
                           ' width="%s" layer="%d"/>'
                           % (E.g(round(a[0], 3)), E.g(round(a[1], 3)),
                              E.g(round(c[0], 3)), E.g(round(c[1], 3)),
                              E.g(q[4] * 2), q[1]))
            sm = re.search(r'(<signal name="%s"[^>]*>)' % re.escape(q[0]), txt)
            txt = txt[:sm.end()] + "".join(seg) + txt[sm.end():]
            relaid.append((q, pts))
        if not ok:
            failed.append((nm, "could not re-lay a ripped segment"))
            continue                                   # roll back: drop txt
        # the via, its stub, and every re-laid segment, against the new text
        if clash(txt, NET, None, v, v, P.VIA_L / 2, clr):
            failed.append((nm, "via would not clear on some layer"))
            continue
        if clash(txt, NET, sd, (px, py), v, STUB_W / 2, clr):
            failed.append((nm, "stub would not clear on L%d" % sd))
            continue
        bust = None
        for q, pts in relaid:
            for a, c in zip(pts, pts[1:]):
                if clash(txt, q[0], q[1], a, c, q[4], clr):
                    bust = "re-laid %s on L%d would not clear" % (q[0], q[1])
                    break
            if bust:
                break
        if bust:
            failed.append((nm, bust))
            continue
        out = txt
        placed.append(v)
        done.append(nm)
    print("")
    print("   served %d pad(s): %s" % (len(done), ", ".join(sorted(done)) or "-"))
    if failed:
        print("   rolled back %d:" % len(failed))
        for nm, why in failed:
            print("      %-8s %s" % (nm, why))
    if not done:
        print("\nnothing applied")
        return 0
    ET.fromstring(out)
    io.open(BRD, "wb").write(out.encode("utf-8"))
    print("\nwrote %s -- layer 19 is now STALE, recompute the ratsnest in Fusion"
          % BRD)
    return 0


if __name__ == "__main__":
    sys.exit(main())
