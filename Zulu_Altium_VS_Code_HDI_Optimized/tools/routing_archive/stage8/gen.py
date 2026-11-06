# -*- coding: utf-8 -*-
"""Stage 8 FINAL -- the XADC knot.  Judge's plan.

Base: planner "re-order-the-row" (p_reorder, md5 90789730fc83b5b3df9d74747290c11e), the only one of
the three whose route_reach held at 138/138 with nothing walled off and no pad foreclosed.

Two changes, each measured, never estimated:

  1. AIN16_P's north crossing moves OFF the Top layer.  p_reorder ran V2 -> Top (45.14,3.45)-
     (45.45,3.95)-(45.70,4.50) -> V4.  Bisected against route_foreclosure (probe_d6.py and the
     result), those two Top segments -- and nothing else in the plan, not even the V4 via -- take
     D6's stale fan-out escape from 25+ Top via slots to 0, which made route_foreclosure exit 1
     where the bare board exits 0.  The same hop on L4-SIG is a single straight segment
     (45.14,3.45)-(45.70,4.50), measured maxwidth 0.1500 mm, binding the D0 fan-out via at
     (45.250,4.400) at the 0.10 SDRAM-inner clearance, and it leaves the Top raster untouched.
     It also keeps AIN16_P on an L5-VCC3V3-referenced layer for the whole hop (Bottom -> L4 ->
     Bottom) instead of crossing to a Top/L2-GND reference and back.

  2. The three vias on y 3.450 come off the exact 0.4400 mm pitch.  p_reorder had
     44.700 / 45.140 / 45.580 -- 0.4400 and 0.4400, i.e. zero margin on the rule.  They become
     44.690 / 45.140 / 45.590: 0.4500 and 0.4500.  The L3-SIG detour that carries NODE_P1 under
     AIN16_P's via moves with them, so there is no kink.

Everything else is p_reorder's, including the one decision that makes it the winner: R14-1's
descent crosses the C37-1/C37-2 gap as a TRACK, not a via.  A via there has a 0.35 mm land that
closes the 0.600 mm gap, and that is exactly what seals R14-2 and walls off ANALOG-IO1 in both
sibling plans.

NOT DONE, and measured rather than assumed: R15-1's GND tie.  See probe_r15_1.py and the result.

    python gen.py            write plan.json + the per-segment width/clearance report
    python gen.py --check    rebuild and compare with plan.json byte for byte
"""
import io, os, sys, hashlib
sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium/tools/stage6')
import lib

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'plan.json')
W = 0.0762                      # every net here is a signal at the 3 mil minimum

# ---------------------------------------------------------------- removals
# Exactly brief.md's approved list: the AIN16_N via at (43.300,3.200), AIN16_P's four Bottom
# primitives, and the two pieces of AIN16_N's OWN copper that the via removal orphans
# ("whatever of AIN16_N's own copper the re-route needs").  Nothing else.
REMOVE = {
    'vias': [
        {'net': 'AIN16_N', 'x': 43.3, 'y': 3.2},
    ],
    'tracks': [
        {'net': 'AIN16_P', 'layer': 'Bottom', 'x1': 43.95, 'y1': 3.05, 'x2': 44.95, 'y2': 3.95, 'width': 0.0762},
        {'net': 'AIN16_P', 'layer': 'Bottom', 'x1': 44.95, 'y1': 3.95, 'x2': 45.15, 'y2': 3.65, 'width': 0.0762},
        {'net': 'AIN16_P', 'layer': 'Bottom', 'x1': 45.15, 'y1': 3.65, 'x2': 45.85, 'y2': 3.65, 'width': 0.0762},
        {'net': 'AIN16_P', 'layer': 'Bottom', 'x1': 45.85, 'y1': 3.65, 'x2': 45.85, 'y2': 4.9,  'width': 0.0762},
        {'net': 'AIN16_N', 'layer': 'Bottom', 'x1': 42.65, 'y1': 3.05, 'x2': 43.3,  'y2': 3.2,  'width': 0.0762},
        {'net': 'AIN16_N', 'layer': 'Top',    'x1': 43.3,  'y1': 3.2,  'x2': 46.15, 'y2': 3.35, 'width': 0.0762},
    ],
}

P = lib.Plan(remove=REMOVE)

V1 = (44.69, 3.45)      # NODE_P1, pocket B west
V2 = (45.14, 3.45)      # AIN16_P, pocket B centre
V3 = (45.59, 3.45)      # NODE_P1, pocket B east
V4 = (45.70, 4.50)      # AIN16_P, north of the y 4.400 fan-out fence
VA = (43.40, 1.89)      # NODE_P1, X2-28/X2-27 gap
VN = (42.98, 1.45)      # AIN16_N, X2-28/X2-27 gap
VG = (40.70, 1.55)      # GND plane via, X2-29/X2-28 gap

# ---------------------------------------------------------------- NODE_P1 (priority 1)
# R16-1 (AIN16_P) sits between R15-2 and R16-2 and its only escape is southward, so any Bottom run
# along the row from R15-2 to R16-2 must cross it.  All three NODE_P1 pads therefore dive into the
# one via pocket south of the row (x 44.60-45.70, y 3.15-3.55 -- the VU Top rail at y 2.23-2.83
# forbids a via centre between y 1.965 and 3.095) and the crossing is made underground.
# R14-1 is trapped: north is the SDRAM via fence (LDQM 42.375 / D6 42.850 at y 4.400 leave a
# 0.125 mm slot against the 0.2562 mm a 3 mil track needs), so its only exit is the 0.30 mm band
# over the capacitors.  It runs EAST along that band into the C37-1/C37-2 gap, drops through it as a
# TRACK and dives in the X2 gap instead.
P.via('NODE_P1', *VA)
P.via('NODE_P1', *V1)
P.via('NODE_P1', *V3)
P.run('NODE_P1', 'Bottom', [(42.5498, 3.9499), (42.5498, 3.65), (43.17, 3.65), (43.17, 2.42), VA],
      wish=W, tag='R14-1 band east -> cap gap -> VA')
P.run('NODE_P1', 'L3-SIG', [VA, (43.60, 2.60), V1], wish=W, tag='VA -> V1')
P.run('NODE_P1', 'Bottom', [V1, (44.3497, 3.9499)], wish=W, tag='V1 -> R15-2')
P.run('NODE_P1', 'L3-SIG', [V1, (44.69, 2.95), (45.59, 2.95), V3], wish=W, tag='V1 -> V3 under AIN16_P V2')
P.run('NODE_P1', 'Bottom', [V3, (45.5496, 3.9499)], wish=W, tag='V3 -> R16-2')

# ---------------------------------------------------------------- AIN16_P (priority 5)
# C37-2 runs east on the y 3.100 lane -- the one lane between the R10-1/R10-2 pad tops (2.900) and
# the pocket via lands (3.275) -- and R16-1 drops into the same via V2.  From V2 the net crosses the
# y 4.400 fan-out fence on L4-SIG, east of the D0 via, and lands end to end on the surviving board
# track's own endpoint (45.850, 4.900).
P.via('AIN16_P', *V2)
P.via('AIN16_P', *V4)
P.run('AIN16_P', 'Bottom', [(43.95, 3.05), (44.25, 3.10), (45.14, 3.10), V2],
      wish=W, tag='C37-2 -> V2 under pocket B')
P.run('AIN16_P', 'Bottom', [(44.9497, 3.9499), V2], wish=W, tag='R16-1 -> V2')
P.run('AIN16_P', 'L4-SIG', [V2, V4], wish=W, tag='V2 -> V4 east of the D0 via')
P.run('AIN16_P', 'Bottom', [V4, (45.85, 4.90)], wish=W, tag='V4 -> U1 stub end')

# ---------------------------------------------------------------- AIN16_N (priority 5)
# C37-1 drops through the X2-28/X2-27 gap -- the only via pocket south of the capacitors -- and runs
# east on L4-SIG to AIN16_N's OWN existing via at (46.150, 3.350).  Same corridor the removed Top
# track used, one layer down, and it keeps the whole under-capacitor band free.
P.via('AIN16_N', *VN)
P.run('AIN16_N', 'Bottom', [(42.65, 3.05), (42.98, 2.90), VN], wish=W, tag='C37-1 -> south via')
P.run('AIN16_N', 'L4-SIG', [VN, (43.00, 2.30), (45.00, 2.70), (46.15, 3.35)],
      wish=W, tag='south via -> existing via (46.15,3.35)')

# ---------------------------------------------------------------- GND R13-2 (priority 2)
# R13-2's only exit is the C36-2/C37-1 gap at x 42.15 (AIN15_P's Bottom wall at x 41.650 closes the
# band west, NODE_P1's R14-1 leg owns it east).  It runs WEST along the under-capacitor band to the
# X2-29/X2-28 gap, the nearest via pocket the AIN16_N and NODE_P1 descents leave free.
P.via('GND', *VG)
P.run('GND', 'Bottom', [(41.9498, 3.9499), (42.15, 3.60), (42.15, 2.20), (40.70, 2.20), VG],
      wish=W, tag='R13-2 -> plane via')

# ---------------------------------------------------------------- NOT ROUTED, with the measurement
# GND R15-1 (priority 2): see probe_r15_1.py.  R15-1 sits over C37-2, so its only exit is the
# 0.300 mm y 3.650 band, and the band is where NODE_P1's R14-1 leg has to be.  Every tie built for
# it walls off connections; the plan leaves it open and hands the user the number.
# NODE_P0 (priority 3): R10-1 and R11-2 sit either side of R10-2, and R10-2's only two exits (the
# R10-1/R10-2 gap at x 45.05 and the R10-2/R11-1 gap at x 45.65) open into the same band any NODE_P0
# copper must occupy.  Routed, it makes route_foreclosure report R10-2 "sealed" and route_reach wall
# off ANALOG-IO0.  Stage 7's rule -- close less, wall off nothing -- decides it.
# ANALOG-IO0 / ANALOG-IO1 (priority 4): 42 mm hauls to X2-39 (3.810,1.270) and X2-40 (1.270,1.270)
# across the regulator block; out of this knot's scope.  Both left fully routable.


def main():
    P.dump(OUT + '.tmp')
    new = io.open(OUT + '.tmp', encoding='utf-8').read()
    os.remove(OUT + '.tmp')
    if '--check' in sys.argv:
        old = io.open(OUT, encoding='utf-8').read()
        print('--check: %s  (md5 %s)' % ('IDENTICAL' if old == new else 'DIFFERS',
                                         hashlib.md5(new.encode('utf-8')).hexdigest()))
        return 0 if old == new else 1
    with io.open(OUT, 'w', encoding='utf-8') as f:
        f.write(new)
    print('%d vias, %d tracks -> %s' % (len(P.VIAS), len(P.TRACKS), OUT))
    print('md5 %s' % hashlib.md5(new.encode('utf-8')).hexdigest())
    P.print_report()
    return 0


sys.exit(main())
