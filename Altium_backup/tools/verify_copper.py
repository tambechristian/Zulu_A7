# -*- coding: utf-8 -*-
"""Rebuild where the COPPER actually is from the placement report, and re-run the clearance check.

WHY THIS EXISTS
verify_placement.py compares the centre of Altium's pad bounding box against the placement target
and finds two parts off by 0.23 and 0.17 mm. Neither is a misplaced component. Altium's
Pad.BoundingRectangle is not the copper: for a through-hole pad it includes the anti-pad the
internal planes must clear, so a 1.52 mm pin reports as 2.53 mm across -- exactly 2 x 0.508 mm of
plane clearance wider. A pad that is ON the plane net gets a thermal relief instead and is not
inflated at all. JP3 (GND, TCK, TMS) and X1 (five signals plus grounded shield tabs) therefore
have LOPSIDED boxes, and ZuluPlacement.pas, which centres that box, put their copper 0.23 and
0.17 mm off the intended centre.

So the box is thrown away and the copper is reconstructed from Pad.X/Y of pad 1, which is a real
copper centre and cannot be inflated, plus the pad geometry in the PcbLib.

THE FLIP CONVENTION, MEASURED RATHER THAN ASSUMED
Reading pad 1 back for parts on the bottom shows Altium mirrors a flipped component about the
X AXIS (y -> -y) and then rotates counter-clockwise. U10 on the bottom at 0 degrees: library
pad 1 sits at (-2.465, +1.905) from the pad centre, and it came back at (22.285, 18.695) from a
centre of (24.750, 20.600) -- x-2.465 and y-1.905, so y is negated and x is not. U3 on the bottom
at 90 degrees confirms it: mirror to (-5.680, -10.400), rotate to (10.400, -5.680), giving
(38.750, 6.170), which is what the report says to the micron.

    python tools/verify_copper.py
"""
import math
import os
import sys

import olefile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import place_board as pb
from verify_pcblib import pads as lib_pads
from verify_placement import read_report


def lib_pad_offsets(path=pb.LIB):
    """footprint -> {pad name: (dx, dy) from the pad bounding-box centre}."""
    f = olefile.OleFileIO(path)
    skip = {'FileHeader', 'Library', 'Textures', 'Models', 'ComponentParamsTOC',
            'LayerKindMapping', 'FileVersionInfo'}
    out = {}
    for name in sorted({e[0] for e in f.listdir() if len(e) > 1} - skip):
        p = lib_pads(f, name)
        if not p:
            out[name] = {}
            continue
        x0 = min(q[1] - q[3] / 2 for q in p); x1 = max(q[1] + q[3] / 2 for q in p)
        y0 = min(q[2] - q[4] / 2 for q in p); y1 = max(q[2] + q[4] / 2 for q in p)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        out[name] = {q[0]: (q[1] - cx, q[2] - cy) for q in p}
    f.close()
    return out


def transform(dx, dy, rot, bottom):
    """Library offset -> board offset: mirror about x if flipped, then rotate CCW."""
    if bottom:
        dy = -dy
    a = math.radians(rot)
    ca, sa = math.cos(a), math.sin(a)
    return dx * ca - dy * sa, dx * sa + dy * ca


def main():
    comp, ext, place, src, missing, overflow = pb.build(verbose=False)
    got = read_report()
    off = lib_pad_offsets()

    actual = {}
    nopad1 = []
    for d, g in got.items():
        fp = comp.get(d)
        if fp is None:
            continue
        o = off.get(fp, {}).get('1')
        if o is None or g['p1'] is None:
            nopad1.append(d)
            actual[d] = (g['layer'], g['rot'], g['cx'], g['cy'])
            continue
        tx, ty = transform(o[0], o[1], g['rot'], g['layer'] == 'bottom')
        actual[d] = (g['layer'], g['rot'], g['p1'][0] - tx, g['p1'][1] - ty)

    print('reconstructed the copper centre of %d components from pad 1' % (len(actual) - len(nopad1)))
    if nopad1:
        # This is sound, and the reason is worth stating. Only a THROUGH-HOLE pad can pick up a
        # plane anti-pad, and only an anti-pad can make the bounding box lopsided. Exactly four
        # footprints in this design have through-hole pads -- ZULU-DIP37, 2X06, 1X03-NOSILK and
        # MOLEX-105017-0001, i.e. X2, J1, JP3, JP4 and X1 -- and every one of them has a pad
        # named 1 and is checked above. The parts falling through to here are LED0603, SOT23-3
        # and the BGA, which are all-SMD and so have symmetric boxes, plus the four pinless
        # Creative Commons marks. For all-SMD parts the box centre IS the copper centre.
        print('   no pad 1; all-SMD or pinless, so the box centre is the copper centre: %s'
              % ' '.join(sorted(nopad1)))

    moved = []
    for d in sorted(actual):
        if d not in place:
            continue
        want = place[d]
        dx = actual[d][2] - want[2]
        dy = actual[d][3] - want[3]
        if abs(dx) > 0.003 or abs(dy) > 0.003:
            moved.append((max(abs(dx), abs(dy)), d, dx, dy))
    moved.sort(reverse=True)
    print('\ncomponents whose copper is more than 0.003 mm from the intended centre: %d' % len(moved))
    for g, d, dx, dy in moved:
        print('   %-6s %-22s  %+.4f %+.4f mm' % (d, comp[d], dx, dy))

    print('\n--- clearance re-checked on the ACTUAL copper ---')
    offb, hits = pb.check(comp, pb.lib_geometry(), actual)
    print('within %.2f mm of the board edge: %d' % (pb.EDGE, len(offb)))
    for s in offb:
        print('   ' + s)
    print('pairs closer than %.2f mm: %d' % (pb.CLEAR, len(hits)))
    for g, a, b, ox, oy in hits[:30]:
        print('   %-6s %-6s  overlap x %6.3f  y %6.3f   (%s / %s)' % (a, b, ox, oy, comp[a], comp[b]))

    ok = not offb and not hits
    print('\n%s' % ('COPPER CLEAN' if ok else 'NOT CLEAN'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
