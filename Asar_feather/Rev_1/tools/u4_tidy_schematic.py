"""Sheet 4 (asar_a7_3.SchDoc), 2026-11-18: three drawing fixes around U4 (the SPI boot flash), asked for by the user.

- R2 (WP# pull-up): its VCC3V3 port pointed right from the bottom of a wire hanging under R2's left pin. The wire now
  rises 10 units from the pin and the port points up, the way R7's does.
- R2's designator sat 32 units under the resistor; it now sits just under the body, centred.
- C11 (U4's bypass): its GND port hung from C11's east pin straight over the FLASH-D03 wire (the port's stem, bars and
  text reach ~28 units down; the wire is 10 units below). C11 moves up 30 units on a jog of the pin-8 VCC wire, so the
  GND port hangs in free space 11 units above FLASH-D03.

No connection changes; the script proves the sheet's nets identical before and after.

    python tools/u4_tidy_schematic.py <sheet in> <sheet out>      (in == out to edit in place)
"""
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schdoc import field, join, owner, read_stream, set_field, split, subtree, write_stream  # noqa: E402
from sheet3_u3_layout import drop_key, fval, move_part, net_map, num, report, set_f  # noqa: E402

SRC_MD5 = 'eef0ab0543870b19d504e6f728a50ded'
C11_DY = 30


def wire_pts(b):
    return [(fval(b, 'X%d' % j), fval(b, 'Y%d' % j)) for j in range(1, num(b, 'LocationCount') + 1)]


def set_wire(b, pts):
    for j in range(1, (num(b, 'LocationCount') or 0) + 1):
        b = drop_key(drop_key(drop_key(drop_key(b, 'X%d' % j), 'Y%d' % j), 'X%d_Frac' % j), 'Y%d_Frac' % j)
    b = set_field(b, 'LocationCount', str(len(pts)))
    for j, (x, y) in enumerate(pts, 1):
        b = set_f(set_f(b, 'X%d' % j, x), 'Y%d' % j, y)
    return b


def main(src, dst):
    raw = open(src, 'rb').read()
    if hashlib.md5(raw).hexdigest() != SRC_MD5:
        raise SystemExit('%s is not the expected sheet (md5 %s)' % (src, SRC_MD5))
    R = split(read_stream(src))
    before = net_map(R)

    def one(pred, what):
        hit = [i for i, (h, b) in enumerate(R) if pred(b)]
        assert len(hit) == 1, (what, hit)
        return hit[0]

    def at(b, x, y):
        return fval(b, 'Location.X') == x and fval(b, 'Location.Y') == y

    def is_wire(pts):
        return lambda b: field(b, 'RECORD') == '27' and wire_pts(b) == pts

    des_owner = {field(b, 'Text'): owner(b) for h, b in R if field(b, 'RECORD') == '34'}
    r2, c11 = des_owner['R2'], des_owner['C11']
    assert field(R[r2][1], 'RECORD') == '1' and field(R[c11][1], 'RECORD') == '1'

    # R2: VCC3V3 wire + port
    w = one(is_wire([(195, 957), (195, 977)]), 'R2 VCC3V3 wire')
    p = one(lambda b: field(b, 'RECORD') == '17' and field(b, 'Text') == 'VCC3V3' and at(b, 195, 957), 'R2 port')
    assert num(R[p][1], 'Orientation') is None
    R[w][1] = set_wire(R[w][1], [(195, 977), (195, 987)])
    R[p][1] = set_field(set_f(R[p][1], 'Location.Y', 987), 'Orientation', '1')

    # R2 designator under the body (body x 205-225, y 974-980), centred
    d = one(lambda b: field(b, 'RECORD') == '34' and field(b, 'Text') == 'R2', 'R2 designator')
    assert owner(R[d][1]) == r2 and at(R[d][1], 215, 942.394)
    R[d][1] = set_f(set_f(R[d][1], 'Location.X', 211), 'Location.Y', 964)

    # C11 up 30 on a jog of the pin-8 wire; its GND wire + port follow
    assert at(R[c11][1], 435, 997)
    kids = sorted(subtree(R, [c11]) - {c11})
    move_part(R, c11, kids, lambda q: (q[0], q[1] + C11_DY))
    v = one(is_wire([(375, 997), (425, 997)]), 'U4-8 VCC wire')
    R[v][1] = set_wire(R[v][1], [(375, 997), (415, 997), (415, 997 + C11_DY), (425, 997 + C11_DY)])
    g = one(is_wire([(445, 997), (455, 997)]), 'C11 GND wire')
    R[g][1] = set_wire(R[g][1], [(445, 997 + C11_DY), (455, 997 + C11_DY)])
    gp = one(lambda b: field(b, 'RECORD') == '17' and field(b, 'Text') == 'GND' and at(b, 455, 997), 'C11 GND port')
    assert num(R[gp][1], 'Orientation') == 3
    R[gp][1] = set_f(R[gp][1], 'Location.Y', 997 + C11_DY)
    one(lambda b: field(b, 'RECORD') == '29' and at(b, 382, 997), 'VCC3V3 junction stays on the pin-8 wire')

    blob = join(R)
    if os.path.abspath(dst) != os.path.abspath(src):
        open(dst, 'wb').write(raw)
    write_stream(dst, blob)
    assert read_stream(dst) == blob
    print('%s written (%d records)' % (os.path.basename(dst), len(R)))
    report(before, net_map(split(read_stream(dst))))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
