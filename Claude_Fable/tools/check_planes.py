# -*- coding: utf-8 -*-
"""Does a moat full of escape vias cut L2 into islands?

L4 USED TO BE A SECOND GROUND PLANE and this file still tests the moat geometry
as though two planes were at stake. Since 2026-08-27 L4 is a signal layer -- see
board/STACKUP.md -- so the flood test below now speaks for L2 alone. The geometry
it checks is unchanged and so is the answer.

    python tools/check_planes.py

WHY. Stage 2 of the BGA escape drops 97 vias into a 1.295 mm annulus at the
centre of the ball field. Every via that is not GND needs an antipad in the
ground planes, and at a 0.39 mm via pitch those antipads overlap. If they overlap
all the way round, the plane copper under the 7 x 7 core is severed from the rest
of L2 and L4 -- a floating patch of copper under the middle of the FPGA, and no
reference for anything routing there on L3. Nothing else in the toolchain looks
at a plane layer, and the failure is invisible in the copper layers.

HOW. Build a candidate via placement, punch its antipads out of a raster of the
plane, and flood from outside the package. If the flood does not reach the copper
under the core, the plane there is an island.

The check is only worth anything if it can fail, so it runs two controls it
expects to FAIL, and says so. A pass with no failing control is not evidence.

L5 IS NOT CHECKED. It is split three ways and the split is not designed yet. It
is the harder case -- a planelet sees every via of the other two rails as foreign
as well -- but it is also a different question, because a planelet only has to
reach its own vias, not stay continuous. Check it when the split exists.
"""

import re, sys, os, math, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import escape as E                                    # noqa: E402
import geom as G                                       # noqa: E402

VIA, PITCH, RASTER = 0.30, 0.39, 0.02


def annulus(pos, land, clr):
    xs = sorted({round(p[0], 3) for p in pos.values()})
    ys = sorted({round(p[1], 3) for p in pos.values()})
    inset = land / 2 + clr + VIA / 2
    return (xs[2] + inset, ys[2] + inset, xs[16] - inset, ys[16] - inset,
            xs[6] - inset, ys[6] - inset, xs[9], ys[9])


def ring_places(ox0, oy0, ox1, oy1, rows=3):
    out = []
    for r in range(rows):
        x0, x1 = ox0 + r * PITCH, ox1 - r * PITCH
        y0, y1 = oy0 + r * PITCH, oy1 - r * PITCH
        m = int(round((x1 - x0) / PITCH))
        for i in range(m):
            t = x0 + i * PITCH
            out += [(t, y0), (x1 - (t - x0), y1)]
        for i in range(1, m):
            t = y0 + i * PITCH
            out += [(x0, t), (x1, y1 - (t - y0))]
    return sorted(set((round(a, 3), round(c, 3)) for a, c in out))


def flood(vias, iso, geo):
    """True if the copper under the core still reaches the copper outside"""
    ox0, oy0, ox1, oy1, ix0, iy0, mx, my = geo
    S = RASTER
    X0, Y0 = ox0 - 1.5, oy0 - 1.5
    W = int((ox1 - ox0 + 3.0) / S) + 1
    H = int((oy1 - oy0 + 3.0) / S) + 1
    cop = bytearray(b"\x01" * (W * H))
    rad = VIA / 2 + iso
    rr = int(rad / S) + 1
    for (px, py) in vias:
        ci, cj = int((px - X0) / S), int((py - Y0) / S)
        for i in range(max(0, ci - rr), min(W, ci + rr + 1)):
            for j in range(max(0, cj - rr), min(H, cj + rr + 1)):
                if (i - ci) ** 2 + (j - cj) ** 2 <= (rad / S) ** 2:
                    cop[j * W + i] = 0
    st = [int(0.2 / S) * W + int(0.2 / S)]
    seen = bytearray(W * H)
    seen[st[0]] = 1
    while st:
        c = st.pop()
        for d in (-1, 1, -W, W):
            q = c + d
            if not (0 <= q < W * H) or seen[q] or not cop[q]:
                continue
            if d in (-1, 1) and (q % W == 0 or c % W == 0):
                continue
            seen[q] = 1
            st.append(q)
    return bool(seen[int((my - Y0) / S) * W + int((mx - X0) / S)])


def main():
    b, pos, land, net, clr = E.load(E.BRD)
    cell, at, ring, n = E.grid(pos)
    pwr, edges, comp = E.gang(pos, net, cell, at)
    strand = [k for r, v in comp.items()
              if not any(ring[x] in (0, 2, 6) for x in v) for k in v]
    slots, need, match, miss = E.lanes(pos, net, cell, at, ring, n, edges, set(strand))
    geo = annulus(pos, land, clr)
    places = ring_places(*geo[:4])
    print("annulus %.3f..%.3f, band %.3f mm -> %d via places at %.2f pitch"
          % (geo[0], geo[2], geo[4] - geo[0], len(places), PITCH))

    # The real via positions, read back out of the board. Stage 2 places them
    # by geometry, not on the candidate grid this file used to guess with, so
    # ask the board rather than re-deriving them.
    real = []
    for m in re.finditer(r'<signal name="([^"]+)"[^>]*>(.*?)</signal>', b, re.S):
        for v in re.finditer(r'<via x="([-\d.]+)" y="([-\d.]+)"', m.group(2)):
            real.append((m.group(1), float(v.group(1)), float(v.group(2))))
    inside = [(s, x, y) for s, x, y in real
              if geo[0] - 0.6 <= x <= geo[2] + 0.6 and geo[1] - 0.6 <= y <= geo[3] + 0.6]
    gnd = sum(1 for s, _x, _y in inside if s == "GND")
    print("vias drawn in the moat: %d of %d on the board -- %d GND, %d foreign"
          % (len(inside), len(real), gnd, len(inside) - gnd))
    assign = {(x, y): s for s, x, y in inside}
    if not assign:
        print("nothing drawn yet; falling back to the candidate placement")
        want = [(k, net[k]) for k in pos
                if ring[k] == 2 and k in net and not E.POWER.match(net[k])]
        want += [(k, net[k]) for gi, k in match.items() if slots[gi]["tag"] == "in"]
        freep = set(places)
        for k, s in sorted(want):
            q = min(freep, key=lambda q: (q[0] - pos[k][0]) ** 2 + (q[1] - pos[k][1]) ** 2)
            freep.discard(q)
            assign[q] = s
    print("")

    bad = 0
    print("L2 / L4, solid GND -- the vias stage 2 actually drew:")
    for iso in (0.09, 0.15, 0.20):
        v = [p for p, s in assign.items() if s != "GND"]
        r = flood(v, iso, geo)
        print("   isolation %.2f, antipad %.2f   core copper %s"
              % (iso, VIA + 2 * iso, "connected" if r else "*** ISLAND ***"))
        bad += 0 if r else 1
    print("   and again with every one of the %d treated as foreign:" % len(assign))
    for iso in (0.15, 0.20):
        r = flood(list(assign), iso, geo)
        print("   isolation %.2f                 core copper %s"
              % (iso, "connected" if r else "*** ISLAND ***"))
        bad += 0 if r else 1

    print("\ncontrols, which MUST fail or this check proves nothing:")
    ctl = 0
    for iso in (0.15, 0.20):
        r = flood(places, iso, geo)
        print("   every place filled, isolation %.2f   %s"
              % (iso, "still connected -- CHECK IS BROKEN" if r else "island, as expected"))
        ctl += 1 if r else 0

    print("\nhow full the annulus may get before the core islands:")
    for iso in (0.15, 0.20):
        lim = None
        for k in range(len(places), 80, -2):
            step = len(places) / float(k)
            v = [places[int(i * step)] for i in range(k)]
            if flood(v, iso, geo):
                lim = k
                break
        print("   isolation %.2f: connected up to %d of %d places (%.0f%%)"
              % (iso, lim, len(places), 100.0 * lim / len(places)))

    bad += l5(b)
    bad += pours(b)
    print("\n%d finding(s)" % (bad + ctl))
    return bad + ctl


# A FLOOR ARGUED WITH ONCE AND LOST STAYS LOST. L16 sits below the 95 % floor
# and the decision on 2026-08-29 was to accept it. Recording the accepted number
# here beats leaving the check to report, every run, a failure nobody intends to
# fix -- a check that cries wolf is a check people stop reading.
#
# Why it was accepted; the argument is in board/STACKUP.md. The damage is not
# concentrated: the ten worst nets are worth 2.73 points between them, stripping
# every power rail off L16 buys 1.9, and an L16 carrying NO signals at all tops
# out at 98.2 %. So 95 % means a bottom layer with no routing on it, and this
# board needs four routing layers. L2 and L5 are the actual reference planes and
# both are solid; L16's fill is shielding and secondary return.
#
# THE NUMBERS MOVED ON 2026-08-29, AND NOT BECAUSE THE BOARD DID. 0.89 was set
# against an anchor rule that counted every pad of the net as grounding the
# piece it sat on -- circular, since an SMD pad is copper on one layer and
# floats with its island unless something reaches the planes. Correcting that
# took L16 to 81.0 % and L1 to 91.9 %, and crediting pads grounded through a
# trace to a via brought them to 83.8 % and 94.6 %. So 0.89 was never a real
# 89 %; it was 83 % measured with a rule that flattered it, and L1 had been
# failing quietly all along.
#
# Set from measurement, one point below each honest figure, so that a genuine
# regression trips the check and ordinary noise does not:
#     L1   94.6 %  ->  0.94       L16   83.8 %  ->  0.83
#
# Raise a value here only with a measurement behind it, and lower it the moment
# the board improves.
ACCEPTED = {"1": 0.94, "16": 0.83}


def pours(brd, net="GND", raster=0.15, iso=0.25, floor=0.95):
    """the GND pours on the OUTER layers, L1 and L16.

    NOT CHECKED UNTIL NOW, and the gap only became visible when it started to
    matter. VCC1V0 and VCC1V8 used to run entirely on L3; they were moved onto
    L16 and L1 to give the SDRAM bus the one clean signal layer back, and a
    power trace crossing a pour cuts it. L16's largest piece went from 97.9 % to
    85.2 % in that move -- the cost of the change, measured rather than assumed.

    LARGEST-PIECE IS THE WRONG TEST HERE, and this used to apply it. l5() asks
    for one piece because L5 is a solid plane whose whole job is to be one
    piece. An outer fill is not that: it is supplementary copper on a layer that
    also carries signals, perforated by every through-hole on the board, and it
    arrives in dozens of pieces with nothing routed on it at all -- L1 measured
    93.9 % before anything was moved onto it.

    What actually matters is whether the copper is CONNECTED. A fragment holding
    a GND via or pad is tied to the real planes on L2 and L4 and is doing its
    job however small it is; a fragment holding neither is floating metal, and
    Eagle drops it anyway since both pours are poured with orphans off. So the
    test is the fraction of fill area that reaches the net, and the largest
    piece is reported alongside as information about how good a shield is left.

    The difference is not academic. Routing 14 SDRAM nets on L16 takes its
    largest piece from 97.9 % to 39.7 %, which reads like a disaster and is not:
    92 % of that copper still sits in a piece with a via in it.
    """
    import geom as G
    import escape as E
    print("")
    head = "L1 and L16, the outer %s pours" % net
    print(head)
    print("-" * len(head))
    sig = re.search(r"<signals>(.*)</signals>", brd, re.S)
    if not sig or not re.search(r'<polygon[^>]*layer="(1|16)"', sig.group(1)):
        print("  ----  no outer pour yet; nothing to check")
        return 0
    w = re.findall(r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)"'
                   r' width="[\d.]+" layer="20"/>', brd)
    xs = [float(q) for v in w for q in (v[0], v[2])]
    ys = [float(q) for v in w for q in (v[1], v[3])]
    X0, Y0 = min(xs), min(ys)
    W = int((max(xs) - X0) / raster) + 1
    H = int((max(ys) - Y0) / raster) + 1
    worst = 0
    for lay in ("1", "16"):
        rects, circs, segs = G.copper_model(brd, net, int(lay))
        blk = G.as_circles([(x, y, hx + iso, hy + iso, 0.0)
                            for x, y, hx, hy, _c in rects])
        blk += [(x, y, r + iso) for x, y, r in circs]
        for u, v, r in segs:
            blk += G.sample(u, v, r + iso, 0.1)
        cop = bytearray(b"\x01" * (W * H))
        for ox, oy, r in blk:
            rr = int(r / raster) + 1
            ci, cj = int((ox - X0) / raster), int((oy - Y0) / raster)
            for i in range(max(0, ci - rr), min(W, ci + rr + 1)):
                for j in range(max(0, cj - rr), min(H, cj + rr + 1)):
                    if (X0 + i * raster - ox) ** 2 + (Y0 + j * raster - oy) ** 2 <= r * r:
                        cop[j * W + i] = 0
        # WHERE THE FILL CAN REACH THE GROUND SYSTEM: vias and plated holes.
        #
        # Not pads. This counted every pad of the net and that is circular: an
        # SMD pad on L16 is copper on L16 and nothing else, so an island whose
        # only anchor is such a pad ties the pad to the island and the island to
        # the pad, with nothing going down to the L2/L4 planes. The pair floats
        # together and this function called it grounded.
        #
        # The overstatement was large -- L16 read 89.7 % under the old rule and
        # 81.0 % under this one, L1 96.2 % against 91.9 % -- and it hid a real
        # fault: 44 GND pads that Eagle's ratsnest reports as unconnected all
        # sit on pieces this check was scoring as tied. A via spans 1-16 and a
        # plated hole is copper on every layer. Those anchor; nothing else does.
        # AND COPPER THAT REACHES ONE. A trace from a stranded pad to a via is a
        # connection, and 13 pads on this board are grounded exactly that way.
        # Seeding on vias alone scored those pieces as floating, which is wrong
        # in the safe direction but still wrong. So: seed with vias and plated
        # holes, then repeatedly ground any of the net's own wires ON THIS LAYER
        # that touches something already grounded, to a fixed point. Wires on
        # different layers that merely cross are NOT connected -- only a via
        # bridges layers, and vias are already seeds.
        #
        # These cells land inside the pieces rather than outside them because
        # copper_model skips the net's own copper, so a pour is never blocked by
        # its own wires and merges with them.
        anchor = set()
        gm = re.search(r'<signal name="%s"[^>]*>(.*?)</signal>' % re.escape(net),
                       sig.group(1), re.S)
        pts = [(float(q.group(1)), float(q.group(2))) for q in
               re.finditer(r'<via x="([-\d.]+)" y="([-\d.]+)"', gm.group(1))] if gm else []
        pts += [(x, y) for rec in E.board_copper(brd, skip=())
                for x, y in [(rec[1], rec[2])] if rec[0] == net and rec[5] == 0]
        for x, y in pts:
            i, j = int((x - X0) / raster), int((y - Y0) / raster)
            if 0 <= i < W and 0 <= j < H:
                anchor.add(j * W + i)
        own = []
        for q in re.finditer(r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)"'
                             r' y2="([-\d.]+)" width="[\d.]+" layer="(\d+)"',
                             gm.group(1) if gm else ""):
            if q.group(5) != lay:
                continue
            a = (float(q.group(1)), float(q.group(2)))
            c = (float(q.group(3)), float(q.group(4)))
            n = max(2, int(math.hypot(c[0] - a[0], c[1] - a[1]) / raster) + 1)
            cells = set()
            for k in range(n + 1):
                t = k / float(n)
                i = int((a[0] + (c[0] - a[0]) * t - X0) / raster)
                j = int((a[1] + (c[1] - a[1]) * t - Y0) / raster)
                if 0 <= i < W and 0 <= j < H:
                    cells.add(j * W + i)
            own.append(cells)
        live = True
        while live:
            live = False
            for k in range(len(own)):
                if own[k] and (own[k] & anchor):
                    anchor |= own[k]
                    own[k] = None
                    live = True
        seen = bytearray(W * H)
        pieces = []
        for st in range(W * H):
            if cop[st] and not seen[st]:
                cells, stack = [], [st]
                seen[st] = 1
                while stack:
                    c = stack.pop(); cells.append(c)
                    for d in (-1, 1, -W, W):
                        q = c + d
                        if 0 <= q < W * H and cop[q] and not seen[q]:
                            if d in (-1, 1) and (q % W == 0 or c % W == 0):
                                continue
                            seen[q] = 1; stack.append(q)
                pieces.append(cells)
        area = sum(len(p) for p in pieces) * raster * raster
        tied = sum(len(p) for p in pieces
                   if any(c in set(p) for c in anchor)) * raster * raster
        sizes = sorted((len(p) * raster * raster for p in pieces), reverse=True)
        frac = tied / area if area else 1.0
        okay = frac >= floor
        note = ""
        if not okay and frac >= ACCEPTED.get(lay, 2.0):
            okay, note = True, "  ACCEPTED, see board/STACKUP.md"
        print("  %s  L%-3s %3d piece(s); %.1f%% of the fill reaches GND, "
              "largest piece %4.0f mm2 (%.0f%%)%s"
              % ("PASS" if okay else "****", lay, len(pieces), 100 * frac,
                 sizes[0], 100 * sizes[0] / area, note))
        worst += 0 if okay else 1
    return worst


def l5(brd, net="VCC3V3", raster=0.15):
    """L5, poured solid, against every foreign via on the board.

    L5 USED TO BE SKIPPED, and the header still explains why: it was planned as
    a three-way split between VCC3V3, VCC1V0 and VCC1V8, and a planelet only has
    to reach its own vias rather than stay continuous, so "is it in one piece"
    was the wrong question to ask of it.

    That split was measured on 2026-08-27 and does not work -- both low rails run
    the full length of the board and interleave, and the most favourable possible
    partition leaves VCC1V0 in ten disconnected pieces. L5 is solid VCC3V3 now,
    the low rails are traces, and "is it in one piece" became exactly the right
    question. See board/STACKUP.md.

    A solid plane takes an antipad from every via that is not its own, and this
    board has 265 vias of which only 16 are VCC3V3. 249 holes in one plane is
    enough to be worth checking rather than assuming.
    """
    print("")
    head = "L5, poured solid %s" % net
    print(head)
    print("-" * len(head))
    sig = re.search(r"<signals>(.*)</signals>", brd, re.S)
    if not sig:
        print("  ----  no <signals> in this board")
        return 0
    if not re.search(r'<polygon[^>]*layer="5"', sig.group(1)):
        print("  ----  no pour on L5 yet; nothing to check")
        return 0
    own = {}
    for m in re.finditer(r'<signal name="([^"]+)"[^>]*>(.*?)</signal>', sig.group(1), re.S):
        for vx, vy, vd in G.vias(m.group(2)):
            own[(round(vx, 3), round(vy, 3))] = (m.group(1), vd)
    foreign = [(x, y, d) for (x, y), (n, d) in own.items() if n != net]
    w = re.findall(r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)"'
                   r' width="[\d.]+" layer="20"/>', brd)
    bx = [float(v) for q in w for v in (q[0], q[2])]
    by = [float(v) for q in w for v in (q[1], q[3])]
    W = int((max(bx) - min(bx)) / raster) + 1
    H = int((max(by) - min(by)) / raster) + 1
    print("  ----  %d vias on the board: %d are %s, %d punch an antipad"
          % (len(own), len(own) - len(foreign), net, len(foreign)))
    worst = 0
    for iso in (0.20, 0.25, 0.30):
        cop = bytearray(b"\x01" * (W * H))
        for x, y, d in foreign:
            r = d / 2 + iso
            rr = int(r / raster) + 1
            ci, cj = int((x - min(bx)) / raster), int((y - min(by)) / raster)
            for i in range(max(0, ci - rr), min(W, ci + rr + 1)):
                for j in range(max(0, cj - rr), min(H, cj + rr + 1)):
                    if (i - ci) ** 2 + (j - cj) ** 2 <= (r / raster) ** 2:
                        cop[j * W + i] = 0
        seen = bytearray(W * H)
        sizes = []
        for st in range(W * H):
            if cop[st] and not seen[st]:
                sz, stack = 0, [st]
                seen[st] = 1
                while stack:
                    c = stack.pop(); sz += 1
                    for dd in (-1, 1, -W, W):
                        q = c + dd
                        if 0 <= q < W * H and cop[q] and not seen[q]:
                            if dd in (-1, 1) and (q % W == 0 or c % W == 0):
                                continue
                            seen[q] = 1; stack.append(q)
                sizes.append(sz * raster * raster)
        sizes.sort(reverse=True)
        frac = sizes[0] / sum(sizes)
        # orphans="no" on the polygon means Eagle drops the strays itself, so
        # the test is whether the MAIN body holds, not whether stray copper
        # exists -- a few square millimetres in a via shadow always will.
        okay = frac > 0.98
        print("  %s  isolate %.2f, antipad %.2f: %d piece(s), largest %.0f mm2, %.1f%% of the copper"
              % ("PASS" if okay else "****", iso, 0.30 + 2 * iso, len(sizes), sizes[0], 100 * frac))
        worst += 0 if okay else 1
    return worst


if __name__ == "__main__":
    sys.exit(main())
