# -*- coding: utf-8 -*-
"""Check the placement Altium actually made against the one place_board.py computed.

Reads tools/placement_report.txt, which ReportPlacement writes by RE-MEASURING every component
through the PCB API after the fact -- not by echoing the numbers it was given.

Altium's Pad.BoundingRectangle is NOT the copper. It comes back wider than the land, because for a
through-hole pad it includes the anti-pad the internal planes have to clear: X2's 1.52 mm pins
report as 2.53 mm across, and 2.53 - 1.52 = 1.01 = twice the 0.508 mm plane clearance set in the
design rules. Worse, a pad that is ON the plane net gets a thermal relief and is NOT inflated, so
a part carrying both -- JP3 with GND, TCK, TMS, or X1 with five signals and four grounded shield
tabs -- has a LOPSIDED box whose centre is not its copper centre. The four footprints with
through-hole pads are therefore exempt from the centre comparison here and are checked by
tools/verify_copper.py instead, which reconstructs the copper from Pad.X/Y.

So the box edges are not compared. What IS compared is what cannot drift:

    the CENTRE of the box    - the expansion is symmetric, so this is the placement target exactly
    the layer
    the rotation
    the position of pad 1    - the only check that can catch a mirrored or quarter-turned part,
                               and the one that matters for X2, whose pin 1 defines the 2.54 mm
                               grid every mating carrier board is built to

    python tools/verify_placement.py
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import place_board as pb

REPORT = os.path.join(HERE, 'placement_report.txt')
U = 25.4 / 1e7                    # internal unit -> mm
TOL = 0.003                       # mm; Altium rounds to its internal grid

# where pad 1 has to be, for the parts where orientation is load-bearing
# footprints whose pads penetrate the internal planes, so their bounding box can be lopsided
THRU_FP = {'ZULU-DIP37', '2X06', '1X03-NOSILK', 'MOLEX-105017-0001'}

PAD1 = {
    'X2': (59.690, 24.130),       # top row, right end: the whole header grid hangs off this
}


def read_report(path=REPORT):
    out = {}
    for line in io.open(path, encoding='latin-1'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        f = line.split('|')
        d, layer, rot = f[0], f[1], int(f[2])
        l, b, r, t, px, py = [int(v) for v in f[3:9]]
        out[d] = dict(layer='bottom' if 'Bottom' in layer else 'top', rot=rot % 360,
                      cx=(l + r) / 2.0 * U, cy=(b + t) / 2.0 * U,
                      w=(r - l) * U, h=(t - b) * U,
                      p1=(px * U, py * U) if px or py else None)
    return out


def main():
    comp, ext, place, src, missing, overflow = pb.build(verbose=False)
    got = read_report()
    print('report   %d components' % len(got))
    print('expected %d components' % len(place))

    fails, info = [], []
    absent = sorted(set(place) - set(got))
    extra = sorted(set(got) - set(place))
    if absent:
        fails.append('on the board but not in the report: %s' % absent)
    if extra:
        fails.append('in the report but not in the placement: %s' % extra)

    worst = 0.0
    nlayer = nrot = npos = 0
    for d in sorted(set(place) & set(got)):
        layer, rot, cx, cy = place[d]
        g = got[d]
        if g['layer'] != layer:
            fails.append('%-6s on %s, should be %s' % (d, g['layer'], layer))
            nlayer += 1
        if g['rot'] != int(rot) % 360:
            fails.append('%-6s rotated %d, should be %d' % (d, g['rot'], int(rot)))
            nrot += 1
        if ext[comp[d]][0] <= 0:           # the pinless CC marks have no pad box to compare
            continue
        if comp[d] in THRU_FP:             # lopsided box; verify_copper.py is the authority
            info.append('%-6s box centre %+.4f %+.4f mm off the target - anti-pad inflation, '
                        'not a move' % (d, g['cx'] - cx, g['cy'] - cy))
            continue
        dx, dy = g['cx'] - cx, g['cy'] - cy
        worst = max(worst, abs(dx), abs(dy))
        if abs(dx) > TOL or abs(dy) > TOL:
            fails.append('%-6s centre off by %+.4f %+.4f mm (%.3f %.3f vs %.3f %.3f)'
                         % (d, dx, dy, g['cx'], g['cy'], cx, cy))
            npos += 1

    print('\nlayer wrong    %d' % nlayer)
    print('rotation wrong %d' % nrot)
    print('position wrong %d   (worst centre error %.4f mm, tolerance %.3f)' % (npos, worst, TOL))

    print('\nPAD 1, where orientation is load-bearing')
    for d, (wx, wy) in sorted(PAD1.items()):
        g = got.get(d)
        if not g or not g['p1']:
            fails.append('%s: the report carries no pad 1' % d)
            continue
        ok = abs(g['p1'][0] - wx) <= TOL and abs(g['p1'][1] - wy) <= TOL
        print('   %-6s pad 1 at %8.3f %8.3f   want %8.3f %8.3f   %s'
              % (d, g['p1'][0], g['p1'][1], wx, wy, 'OK' if ok else 'WRONG'))
        if not ok:
            fails.append('%s pad 1 is at %.3f %.3f, not %.3f %.3f'
                         % (d, g['p1'][0], g['p1'][1], wx, wy))

    # where pad 1 landed for the parts whose orientation was inferred rather than measured
    print('\nPAD 1 of the parts whose orientation came from the old board or the plan')
    for d in ('X1', 'X3', 'X4', 'U1', 'U2', 'U3', 'U4', 'U10', 'J1', 'U8', 'U5'):
        g = got.get(d)
        if g and g['p1']:
            print('   %-5s %-6s r%-3d  pad 1 at %7.3f %7.3f   (centre %7.3f %7.3f)'
                  % (d, g['layer'], g['rot'], g['p1'][0], g['p1'][1], g['cx'], g['cy']))

    print('\n%s' % ('PLACEMENT VERIFIED' if not fails else 'MISMATCHES (%d)' % len(fails)))
    for s in fails[:40]:
        print('   ' + s)
    return 0 if not fails else 1


if __name__ == '__main__':
    sys.exit(main())
