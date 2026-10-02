# -*- coding: utf-8 -*-
"""Sheet 4, 2026-09-10: R19's supply arrow points the right way and the FT-VCORE caps come off the
left edge.

1. R19's VCC3V3 PORT POINTED DOWN. The port at (213,852) that feeds R19, the FT-RESETN pull-up,
   carried `Orientation=3`. Every other VCC3V3 port on the sheet is `Orientation=1`, so this one
   alone hung its arrow and its name below the wire instead of above it. One field: 3 -> 1. The
   hot point does not move, so nothing electrical changes -- the symbol is simply drawn on the
   other side of the wire it already touches.

2. C152, C153 AND C154 SAT ON THE FRAME. The sheet's inner border is the line at x=52. C152's
   designator box began at x 54.5 and its ground bar reaches further left still, so the FT-VCORE
   decoupling bank was pressed against the border with about two units of air.

   The bank moves 40 units right. That leaves roughly 39 units to the border and about 49 to the
   VCC3V3 port at x 232, which is the next thing along the row, so it sits between the two rather
   than against one of them.

   What moves: the three placements and everything they own, the three GND ports with their stubs,
   the two rail taps, and the two junctions -- everything whose whole geometry lies inside
   x 45..145, y 960..1035. The frame line at x=52 is not swept up because it runs the height of the
   sheet and so is not inside the window.

   The FT-VCORE rail itself is one polyline that runs from x 462 all the way to C152 and then drops
   into it: (462,1022) (462,1032) (447,1032) (432,1032) (277,1032) (122,1032) (92,1032) (62,1032)
   (62,997). Its four trailing vertices are the bank's own, so they move with it and the long run
   from (277,1032) simply gets shorter. The vertex at 277 and everything beyond stays put.

Both are geometry. The drawing's connectivity signature is compared before and after and must be
identical, and the netlist must come back with the same 178 nets over 783 pads.

    python tools/sheet4_tidy.py tools "Imported zulu_a7.PrjPcb/zulu_a7_4.SchDoc"
"""
import sys, re
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field
from sheet5_right_margin import num, rectype, points, fonts_of, drawn_boxes, signature

PORT_AT = (213, 852)
PORT_FROM, PORT_TO = '3', '1'

DX = 40
WIN = (45, 145, 960, 1035)                 # x lo, x hi, y lo, y hi
RAIL = ((462, 1022), (462, 1032), (447, 1032), (432, 1032), (277, 1032),
        (122, 1032), (92, 1032), (62, 1032), (62, 997))
RAIL_MOVE_BELOW_X = 145                    # rail vertices left of this belong to the bank
BORDER_L = 52.0


def set_pts(b, pts):
    b = re.sub(rb'\|(X|Y)\d+(_Frac)?=[^|\x00]*', b'', b)
    tail = ''.join(f'|X{k}={x}|Y{k}={y}' for k, (x, y) in enumerate(pts, 1))
    b = set_field(b, 'LocationCount', str(len(pts)))
    return b[:-1] + tail.encode() + b'\x00'


def shift(b, dx):
    for k in ['Location.X', 'Corner.X'] + [f'X{k}' for k in range(1, 12)]:
        v = num(b, k)
        if v is not None:
            b = set_field(b, k, str(v + dx))
    return b


def main(path):
    recs = split(read_stream(path, 'FileHeader'))
    N = len(recs)
    assert int(field(recs[0][1], 'Weight')) == N - 1, 'header count is already wrong'
    sig = signature(recs)

    # --- 1. the port ---------------------------------------------------------------------
    hit = [i for i, (h, b) in enumerate(recs)
           if rectype(b) == 17 and (num(b, 'Location.X'), num(b, 'Location.Y')) == PORT_AT]
    assert len(hit) == 1, f'the port at {PORT_AT}: found {len(hit)}'
    port = hit[0]
    done_port = field(recs[port][1], 'Orientation') == PORT_TO
    if not done_port:
        assert field(recs[port][1], 'Orientation') == PORT_FROM, \
            f"R19's port points {field(recs[port][1], 'Orientation')}, expected {PORT_FROM}"
        recs[port][1] = set_field(recs[port][1], 'Orientation', PORT_TO)
        print(f"  R19's VCC3V3 port at {PORT_AT}: Orientation {PORT_FROM} -> {PORT_TO} (arrow up)")

    # --- 2. the capacitor bank ------------------------------------------------------------
    xl, xr, yl, yh = WIN
    root, place = __import__('sheet5_right_margin').roots(recs)
    mine = {i for i in place
            if num(recs[i][1], 'Location.X') is not None
            and xl <= num(recs[i][1], 'Location.X') <= xr
            and yl <= num(recs[i][1], 'Location.Y') <= yh}
    owned = [i for i in range(len(recs)) if root[i] in mine]
    free = [i for i, (h, b) in enumerate(recs)
            if root[i] is None and i not in place and points(b)
            and all(xl <= x <= xr and yl <= y <= yh for x, y in points(b))]
    rail = [i for i, (h, b) in enumerate(recs)
            if rectype(b) == 27 and tuple(points(b)) == RAIL]
    done_bank = not rail
    if done_bank:
        print('  the FT-VCORE bank has already been moved')
    else:
        assert len(mine) == 3, f'expected C152, C153, C154 in the window, found {len(mine)}'
        assert len(rail) == 1
        for i in owned + free:
            recs[i][1] = shift(recs[i][1], DX)
        recs[rail[0]][1] = set_pts(recs[rail[0]][1],
                                   [(x + DX if x < RAIL_MOVE_BELOW_X else x, y) for x, y in RAIL])
        print(f'  FT-VCORE bank: 3 caps, {len(owned)} owned and {len(free)} free records moved '
              f'{DX} right, and the rail polyline follows them')
    if done_port and done_bank:
        raise SystemExit('sheet 4 is already tidied; nothing done')

    assert len(recs) == N
    blob = join(recs)
    write_stream(path, 'FileHeader', blob)
    assert read_stream(path, 'FileHeader') == blob
    verify(path, sig)


def verify(path, sig_before):
    recs = split(read_stream(path, 'FileHeader'))
    assert int(field(recs[0][1], 'Weight')) == len(recs) - 1, 'header count'
    assert all(b.endswith(b'\x00') for h, b in recs), 'a record lost its terminator'
    assert signature(recs) == sig_before, 'the drawing connectivity changed'
    fonts = fonts_of(recs)
    boxes = drawn_boxes(recs, fonts)
    port = [e for e in boxes if e[1] == 17 and e[3] == 'VCC3V3']
    left = min(e[2][0] for e in boxes if e[1] != 6)
    assert left > BORDER_L, f'something is left of the border at x={left:.1f}'
    print(f'verify: {len(recs)} records, {len(boxes)} drawn objects, connectivity unchanged; '
          f'leftmost non-frame object now x={left:.1f} against a border at {BORDER_L:.0f}, '
          f'{len(port)} VCC3V3 ports on the sheet')


if __name__ == '__main__':
    main(sys.argv[2])
