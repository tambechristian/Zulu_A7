# -*- coding: utf-8 -*-
"""How far west can U2 and the LED row actually go?

docs/routing_readiness.md item 5 asks for U2 1.6 mm west and LD0-LD5 1.3 mm west, to widen
the U2-to-U1 corridor that fell from 3.680 mm on the six-layer board to 2.36 mm here. The
numbers in that document were measured before Q2 and R77 were deleted and the packer re-flowed
the west power corner, so they are re-derived here from tools/placement_report.txt as the board
stands, and they do not survive unchanged:

    BTN east edge 21.750, LED west edge 23.300  ->  1.550 mm of slack, not 1.650
    a 1.300 mm LED shift therefore leaves 0.250 mm against a 0.300 mm rule

and with the LEDs capped, U2 is capped too, because U2 must stay 0.300 clear of the LEDs it
is moving toward.

There is also one finding that makes the move CHEAPER than the document priced it: nothing of
U2's own decoupling sits under U2. The only bottom-side parts wholly inside U2's outline are
R80-R83, and the area beneath it belongs to U3, which must not move. So the shift is U2 plus
the six LEDs and nothing else.

    python tools/shift_u2_leds.py            scan and report
    python tools/shift_u2_leds.py --emit     write tools/ZuluShift.pas for the best pair
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import place_board as pb
from verify_placement import read_report
from verify_copper import lib_pad_offsets, transform

LEDS = ['LD0', 'LD1', 'LD2', 'LD3', 'LD4', 'LD5']
U2 = ['U2']

BOXCLEAR = 0.30      # component-extent clearance we hold ourselves to
                     # Altium's own ComponentClearance rule is GAP=10mil = 0.254 mm, scope
                     # All/All, and it measures between component EXTENTS, not lands. The
                     # land-to-land check in place_board.py passes at a 0.200 mm box gap
                     # because BTN's four corner pads straddle the LED row in y -- but the
                     # DRC would still fail. So both criteria are enforced here.


def boxes():
    """designator -> (layer, x0, x1, y0, y1) of the pad bounding box, from the report."""
    got = read_report()
    return {d: (g['layer'], g['cx'] - g['w'] / 2, g['cx'] + g['w'] / 2,
                g['cy'] - g['h'] / 2, g['cy'] + g['h'] / 2)
            for d, g in got.items() if g['w'] > 0 or g['h'] > 0}


def box_hits(bx, du, dl):
    """same-side component pairs whose extents come closer than BOXCLEAR after the shift."""
    moved = {}
    for d, (lay, x0, x1, y0, y1) in bx.items():
        dx = du if d in U2 else (dl if d in LEDS else 0.0)
        moved[d] = (lay, x0 - dx, x1 - dx, y0, y1)
    names = sorted(moved)
    out = []
    for i, a in enumerate(names):
        la, ax0, ax1, ay0, ay1 = moved[a]
        for b in names[i + 1:]:
            lb, bx0, bx1, by0, by1 = moved[b]
            if la != lb:
                continue
            ox = min(ax1, bx1) - max(ax0, bx0)
            oy = min(ay1, by1) - max(ay0, by0)
            gap = min(ox, oy)
            if gap > -BOXCLEAR + 1e-9:
                out.append((round(gap, 4), a, b))
    return sorted(out, reverse=True)



def actual_centres():
    comp, ext, place, src, missing, overflow = pb.build(verbose=False)
    got = read_report()
    off = lib_pad_offsets()
    out = {}
    for d, g in got.items():
        fp = comp.get(d)
        o = off.get(fp, {}).get('1') if fp else None
        if o is None or g['p1'] is None:
            out[d] = (g['layer'], g['rot'], g['cx'], g['cy'])
        else:
            tx, ty = transform(o[0], o[1], g['rot'], g['layer'] == 'bottom')
            out[d] = (g['layer'], g['rot'], g['p1'][0] - tx, g['p1'][1] - ty)
    return comp, out


def shifted(base, du, dl):
    out = dict(base)
    for d in U2:
        if d in out:
            l, r, x, y = out[d]
            out[d] = (l, r, x - du, y)
    for d in LEDS:
        if d in out:
            l, r, x, y = out[d]
            out[d] = (l, r, x - dl, y)
    return out


def main():
    comp, base = actual_centres()
    geom = pb.lib_geometry()
    bx = boxes()

    offb, hits = pb.check(comp, geom, base)
    bh = box_hits(bx, 0, 0)
    print('as it stands: %d off-board, %d land pairs under %.2f mm, %d box pairs under %.2f mm'
          % (len(offb), len(hits), pb.CLEAR, len(bh), BOXCLEAR))
    for g, a, b in bh[:8]:
        print('   box %-6s %-6s %+.3f' % (a, b, g))

    # walk the pair down in 0.025 mm steps -- the new snap grid -- keeping the document's
    # ratio of 1.6 : 1.3 until one of them binds, then holding the other.
    best = (0.0, 0.0)
    step = 0.025
    du = 0.0
    while du + step <= 1.6 + 1e-9:
        cand_u = round(du + step, 3)
        cand_l = round(min(1.3, cand_u * 1.3 / 1.6), 3)
        cand_l = round(cand_l / step) * step
        o, h = pb.check(comp, geom, shifted(base, cand_u, cand_l))
        if o or h or box_hits(bx, cand_u, cand_l):
            break
        best = (cand_u, cand_l)
        du = cand_u

    print('largest clean shift on the 1.6 : 1.3 ratio: U2 %.3f mm, LEDs %.3f mm' % best)

    # now hold U2 there and see whether the LEDs can go further on their own, and vice versa
    bu, bl = best
    l = bl
    while True:
        c = round(l + step, 3)
        o, h = pb.check(comp, geom, shifted(base, bu, c))
        if o or h or box_hits(bx, bu, c) or c > 3:
            break
        l = c
    u = bu
    while True:
        c = round(u + step, 3)
        o, h = pb.check(comp, geom, shifted(base, c, l))
        if o or h or box_hits(bx, c, l) or c > 3:
            break
        u = c
    print('after relaxing each in turn:                U2 %.3f mm, LEDs %.3f mm' % (u, l))

    final = shifted(base, u, l)
    o, h = pb.check(comp, geom, final)
    bh = box_hits(bx, u, l)
    print('final check: %d off-board, %d land pairs under %.2f mm, %d box pairs under %.2f mm'
          % (len(o), len(h), pb.CLEAR, len(bh), BOXCLEAR))
    for g, a, b in bh[:8]:
        print('   box %-6s %-6s %+.3f' % (a, b, g))

    def box(d, st):
        g = geom[comp[d]]
        return st[d][2], st[d][3]

    # the two numbers that matter
    from verify_placement import read_report as rr
    got = rr()
    def edges(d, dx):
        g = got[d]
        return g['cx'] - g['w'] / 2 - dx, g['cx'] + g['w'] / 2 - dx
    u2w, u2e = edges('U2', u)
    ldw = min(edges(d, l)[0] for d in LEDS)
    lde = max(edges(d, l)[1] for d in LEDS)
    btne = got['BTN']['cx'] + got['BTN']['w'] / 2
    u1w = got['U1']['cx'] - got['U1']['w'] / 2
    print('\n            before        after')
    print('BTN -> LED  %7.3f      %7.3f' % (min(edges(d, 0)[0] for d in LEDS) - btne, ldw - btne))
    print('LED -> U2   %7.3f      %7.3f' % (edges('U2', 0)[0] - max(edges(d, 0)[1] for d in LEDS),
                                            u2w - lde))
    print('U2  -> U1   %7.3f      %7.3f' % (u1w - edges('U2', 0)[1], u1w - u2e))

    if '--emit' in sys.argv:
        lines = []
        for d in U2:
            lines.append("    Move('%s', %.4f);" % (d, -u))
        for d in LEDS:
            lines.append("    Move('%s', %.4f);" % (d, -l))
        open(os.path.join(HERE, 'shift_moves.txt'), 'w').write('\n'.join(lines) + '\n')
        print('\nwrote tools/shift_moves.txt')
    return 0


if __name__ == '__main__':
    sys.exit(main())
