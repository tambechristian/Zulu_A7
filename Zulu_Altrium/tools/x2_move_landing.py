# -*- coding: utf-8 -*-
"""X2 pin field, 2026-09-09 (fifth pass): the LiPo landing moves to sit opposite the micro-USB.

Follows x2_renumber_40.py. CHAN17, CHAN18 and CHAN19 (pins 27-29) slide four positions towards
the right-hand end, so the four-position landing moves with them and now lies between pin 29 and
pin 30, at x 36.83 / 34.29 / 31.75 / 29.21 -- the same four x values as the micro-USB landing in
the top row. The two rows become mirror images:

  position (x)      59.69 ................................................. 1.27
  top row           pins 1-9 | USB landing (4) | pins 10-20
  bottom row        pins 21-29 | LiPo landing (4) | pins 30-40

Pin numbers do not change: the field is still numbered 1-40 straight through and the numbering
already skipped the landing, so this is a pure geometry move and the exported netlist is
byte-for-byte identical in connectivity AND in pad names. Only the three gate copies with their
wires and net labels move on the sheet, plus the X2 MANF#/SPEC/NOTE and the text frame, which now
describe a bottom row cut as 1x9 + 1x11 like the top one (two Sullins part numbers, two of each
per board instead of four different ones). Refuses to run twice.

THE FOOTPRINT MUST FOLLOW, as it already had to after the renumbering: ZULU-DIP37 needs 40 pads
named 1-40, the bottom row now split 9 + landing + 11.

    python tools/x2_move_landing.py tools "Imported zulu_a7.PrjPcb"
"""
import sys, os, re
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

SLIDE = ('CHAN17', 'CHAN18', 'CHAN19')                                  # pins 27-29
DY = 40                                                                 # four rows towards the corner
FROM_ROWS = {1049, 1039, 1029}
COORD_KEYS = re.compile(rb'\|(Location\.X|Location\.Y|X\d+|Y\d+)=(-?\d+)')
MANF = '2x PRPC009SAAN-RC + 2x PRPC011SAAN-RC'
SPEC = ('four 0.1 in male breakaway header strips, 0.64 mm square gold-flash pins, 2.54 mm pitch, through-hole, mounted from the '
        'underside, two part numbers and two of each per board: PRPC009SAAN-RC 1x9 twice (pins 1-9 and 21-29) and PRPC011SAAN-RC '
        '1x11 twice (pins 10-20 and 30-40); the two rows are cut identically since the LiPo landing was moved opposite the '
        'micro-USB on 2026-09-09')
NOTE = ('Pin field ZULU-DIP37: 40 pins of 1.016 mm on 2.54 mm pitch, two rows 22.86 mm (0.900 in) apart, numbered 1-40 straight '
        'through and skipping both landings. The rows are mirror images: top row pins 1-9 (x 59.69..39.37), FOUR positions for '
        'the micro-USB X1 (36.83..29.21), pins 10-20 (26.67..1.27); bottom row pins 21-29 (59.69..39.37), FOUR positions for the '
        'LiPo header X4 at the SAME four x values (36.83..29.21), pins 30-40 (26.67..1.27), so X4 sits on the top side directly '
        'opposite the edge-mounted USB receptacle. Each landing is 12.70 mm between the neighbouring pin centres, 11.176 mm '
        'clear: the JST B2B-PH-SM4-TB body is 7.95 mm, so 1.61 mm each side. Reworked 2026-09-09 from the old 44-position '
        'pattern: +5V-INPUT with D2/D3, GND5, GND3 and +3.3V2 removed, CHAN12/CHAN13 moved to pins 2/3, the bottom row closed up, '
        'the field renumbered and the landing moved. Three grounds (1, 20, 21); 3.3 V for the header is pin 17 alone; pin 22 VU '
        'sources the 4.4 V rail. THE PCB FOOTPRINT MUST BE REDRAWN with 40 pads named 1-40 in these positions -- the imported '
        'ZULU-DIP37 still names 44. Sullins PRPC strips fit the holes (0.64 mm square pins, Sullins recommends 1.02 mm). '
        'Digi-Key 2026-09-08: PRPC009SAAN-RC 1,201 at $0.18, PRPC011SAAN-RC 428 at $0.22, two of each per board (the 1x11 stock '
        'covers about 200 boards). Alternate: any 2.54 mm 1x40 breakaway strip (LCSC Boomele C2337, 81,690) cut to 9 + 11 twice.')
FRAME = ('X2: 40 pins on a 2.54 mm grid, rows 22.86 mm (0.900 in) apart, numbered 1-40 straight ~1'
         'through from the right and skipping both landings.  The two rows are mirror images. ~1'
         'TOP ROW, x 59.69 down to 1.27: GND, CHAN12, CHAN13, then CHAN-CLK and CHAN0..CHAN3 ~1'
         '  (pins 4-8), CHAN4 (pin 9), CHAN5..CHAN11 (10-16), +3.3V, +1.8V, +1.0V, GND. ~1'
         'BOTTOM ROW, x 59.69 down to 1.27: GND, VU, RST# (pins 21-23), CHAN14..CHAN16 (24-26), ~1'
         '  CHAN17..CHAN19 (27-29), then CHAN20..CHAN28 (30-38), ANALOG-IO0, ANALOG-IO1 (39, 40). ~1'
         'FOUR positions in each row -- x 36.83, 34.29, 31.75, 29.21, between pins 9 and 10 above ~1'
         '  and between pins 29 and 30 below -- are RESERVED, not spare: the edge-mounted ~1'
         '  micro-USB X1 lands on the top row (7.80 mm of copper), the top-side LiPo header X4 ~1'
         '  (JST B2B-PH-SM4-TB, 7.95 mm body) lands on the bottom row directly opposite it. ~1'
         '  Each landing is 12.70 mm between the neighbouring pin centres, 11.176 mm clear. ~1'
         'THREE grounds: pins 1, 20, 21.  Pin 17 is the only +3.3V pin.  Pin 22 VU SOURCES the ~1'
         '  4.4 V rail (bq24232 OUT) -- the +5V-INPUT pin and its D2/D3 went on 2026-09-09, ~1'
         '  so external power is the LiPo on X4.  THE PCB FOOTPRINT MUST BE REDRAWN: 40 pads named 1-40.')


def num(b, k):
    v = field(b, k); return int(v) if v is not None else None


def owner_list_index(b):
    o = field(b, 'OwnerIndex')
    return int(o) + 1 if o is not None else None


def wire_pts(b):
    if not b.startswith(b'|RECORD=27|'):
        return None
    n = num(b, 'LocationCount') or 0
    return tuple((num(b, f'X{k}'), num(b, f'Y{k}')) for k in range(1, n + 1))


def shift(b, dy):
    def rep(m):
        k, v = m.group(1), int(m.group(2))
        if k == b'Location.Y' or k.startswith(b'Y'):
            v += dy
        return b'|' + k + b'=' + str(v).encode()
    return COORD_KEYS.sub(rep, b)


def main(path):
    recs = split(read_stream(path, 'FileHeader'))
    copies = [i for i, (h, b) in enumerate(recs) if b.startswith(b'|RECORD=1|') and field(b, 'LibReference') == 'ZULU-CONN']
    assert len(copies) == 41, len(copies)
    root = {}
    for i, (h, b) in enumerate(recs):
        oi = owner_list_index(b)
        if oi is None:
            if b.startswith(b'|RECORD=1|'): root[i] = i
            continue
        r = oi
        while owner_list_index(recs[r][1]) is not None:
            r = owner_list_index(recs[r][1])
        root[i] = r
    gate_of = {}
    for i, (h, b) in enumerate(recs):
        if b.startswith(b'|RECORD=41|') and field(b, 'Name') == 'GATE' and root.get(i) in copies:
            gate_of[root[i]] = field(b, 'Text')
    movers = {ci for ci, g in gate_of.items() if g in SLIDE}
    assert len(movers) == 3, movers
    rows = {num(recs[ci][1], 'Location.Y') for ci in movers}
    if rows == {1089, 1079, 1069}:
        raise SystemExit('CHAN17-19 already sit above the landing; nothing done')
    assert rows == FROM_ROWS, rows
    moved = 0
    for i in range(len(recs)):
        h, b = recs[i]
        if root.get(i) in movers:
            b = shift(b, DY); moved += 1
        elif owner_list_index(b) is None:
            p = wire_pts(b)
            if p and len(p) == 2 and p[0][0] == 325 and p[1][0] == 355 and p[0][1] == p[1][1] and p[0][1] in rows:
                b = shift(b, DY); moved += 1
            elif b.startswith(b'|RECORD=25|') and num(b, 'Location.X') == 355 and num(b, 'Location.Y') in rows:
                b = shift(b, DY); moved += 1
        if b.startswith(b'|RECORD=41|') and owner_list_index(b) in copies:
            name = field(b, 'Name')
            if name == 'MANF#': b = set_field(b, 'Text', MANF)
            elif name == 'SPEC': b = set_field(b, 'Text', SPEC)
            elif name == 'NOTE': b = set_field(b, 'Text', NOTE)
        recs[i][1] = b
    frames = [i for i, (h, b) in enumerate(recs) if b.startswith(b'|RECORD=28|') and (field(b, 'Text') or '').startswith('X2: 40 pins on a 2.54 mm grid, rows')]
    assert len(frames) == 1, frames
    recs[frames[0]][1] = set_field(recs[frames[0]][1], 'Text', FRAME)
    blob = join(recs)
    write_stream(path, 'FileHeader', blob)
    assert read_stream(path, 'FileHeader') == blob
    print(f'sheet 2: {len(recs)} records, {moved} shifted by {DY} (pins 27-29 and their wires and labels)')
    verify(path)


CATALOGUE = ('DeviceName', 'LibraryName', 'DeviceSetName', 'MANF', 'MANF#', 'SPEC', 'NOTE')


def verify(path):
    recs = split(read_stream(path, 'FileHeader'))
    assert int(field(recs[0][1], 'Weight')) == len(recs) - 1
    copies = [i for i, (h, b) in enumerate(recs) if b.startswith(b'|RECORD=1|') and field(b, 'LibReference') == 'ZULU-CONN']
    assert len(copies) == 41
    kids = {}
    for i, (h, b) in enumerate(recs):
        oi = owner_list_index(b)
        if oi in copies: kids.setdefault(oi, []).append(b)
    table, rows = [], {}
    for ci in copies:
        pins = [b for b in kids[ci] if b.startswith(b'|RECORD=2|')]
        assert sorted(int(field(b, 'Designator')) for b in pins) == list(range(1, 41))
        names = [field(b, 'Name') for b in kids[ci] if b.startswith(b'|RECORD=41|')]
        assert all(names.count(c) == 1 for c in CATALOGUE), [c for c in CATALOGUE if names.count(c) != 1]
        assert field(recs[ci][1], 'PartCount') == '42' and field(recs[ci][1], 'AllPinCount') == '40'
        pid = field(recs[ci][1], 'CurrentPartId')
        vis = [b for b in pins if field(b, 'OwnerPartId') == pid]
        gate = [field(b, 'Text') for b in kids[ci] if b.startswith(b'|RECORD=41|') and field(b, 'Name') == 'GATE']
        if vis:
            pad = int(field(vis[0], 'Designator'))
            table.append((pad, gate[0]))
            if num(recs[ci][1], 'Location.X') == 325:
                rows[pad] = (num(recs[ci][1], 'Location.Y'), num(vis[0], 'Location.Y'))
    for pad, name in sorted(table):
        print(f'   pin {pad:>2} {name}')
    for pad, (gy, py) in rows.items():                                  # 21-29 on 1149..1069, 30-40 on 1019..919
        want = 1149 - 10 * (pad - 21) if pad <= 29 else 1019 - 10 * (pad - 30)
        assert gy == py == want, (pad, gy, py, want)
    labels = {(num(b, 'Location.X'), num(b, 'Location.Y')) for h, b in recs if b.startswith(b'|RECORD=25|') and owner_list_index(b) is None}
    wires = {wire_pts(b) for h, b in recs if b.startswith(b'|RECORD=27|') and owner_list_index(b) is None}
    for pad, (gy, py) in rows.items():
        assert ((325, gy), (355, gy)) in wires and (355, gy) in labels, pad
    for y in (1059, 1049, 1039, 1029):                                  # the landing, now between pins 29 and 30
        assert (355, y) not in labels and ((325, y), (355, y)) not in wires, y
    t = dict(table)
    assert sorted(t) == list(range(1, 41))
    assert t[26] == 'CHAN16' and t[27] == 'CHAN17' and t[29] == 'CHAN19' and t[30] == 'CHAN20' and t[38] == 'CHAN28' and t[40] == 'ANALOG-IO1'
    print('verify: pins 1-40 unchanged, rows 21-29 then a four-row landing then 30-40, mirroring the top row')


if __name__ == '__main__':
    main(os.path.join(sys.argv[2], 'zulu_a7_2.SchDoc'))
