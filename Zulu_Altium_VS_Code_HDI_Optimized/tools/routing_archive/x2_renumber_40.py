# -*- coding: utf-8 -*-
"""X2 pin field, 2026-09-09 (fourth pass): bottom row closed up, pins renumbered 1-40.

Follows x2_drop_3v3.py. CHAN14, CHAN15 and CHAN16 move one position towards the right-hand end
into the hole +3.3V2 left behind, so the LiPo landing widens from three positions to four and
matches the micro-USB landing in the top row exactly: 12.70 mm between the neighbouring pin
centres, 11.176 mm clear, which leaves 1.61 mm each side of the 7.95 mm JST body.

The pins are then numbered 1-40 straight through, skipping both gaps -- the convention the top
row has always used, where pad 9 is followed by pad 10 across the four USB positions:

  position (x)      59.69 ................................................. 1.27
  top row           1-9 | USB gap (4) | 10-20
  bottom row        21-26 | LiPo gap (4, x 44.45/41.91/39.37/36.83) | 27-40

  pad changes       25->24 CHAN14, 26->25 CHAN15, 27->26 CHAN16, then 31..44 -> 27..40
                    (CHAN17..CHAN28, ANALOG-IO0, ANALOG-IO1); pads 1-23 unchanged.

Sheet 2 only: the three CHAN14-16 gate copies shift up one row (10 units) with their wires and
net labels, every pin record in every gate copy is remapped, and MANF#, SPEC, NOTE and the text
frame are rewritten. No component, sub-part or net changes, so the netlist keeps every connection
and only the X2 pad names move. Refuses to run twice.

THE FOOTPRINT MUST FOLLOW. ZULU-DIP37 still carries pads named 1-44 in the imported library; from
now on the pad names diverge from the old positions (schematic pin 27 is the pad at x 34.29, which
that library calls 31), so the PCB footprint has to be redrawn with 40 pads named 1-40 in these
positions before the netlist can be loaded onto a board.

    python tools/x2_renumber_40.py tools "Imported zulu_a7.PrjPcb"
"""
import sys, os, re
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

SLIDE = ('CHAN14', 'CHAN15', 'CHAN16')                                  # gate names that move up one row
DY = 10
REMAP = {25: 24, 26: 25, 27: 26}
REMAP.update({n: n - 4 for n in range(31, 45)})                         # CHAN17..ANALOG-IO1 -> 27..40
COORD_KEYS = re.compile(rb'\|(Location\.X|Location\.Y|X\d+|Y\d+)=(-?\d+)')
MANF = 'PRPC014SAAN-RC + PRPC011SAAN-RC + PRPC009SAAN-RC + PRPC006SAAN-RC'
SPEC = ('four 0.1 in male breakaway header strips, 0.64 mm square gold-flash pins, 2.54 mm pitch, through-hole, mounted from the '
        'underside: PRPC006SAAN-RC 1x6 (pins 21-26) and PRPC014SAAN-RC 1x14 (pins 27-40) on the bottom row, PRPC009SAAN-RC 1x9 '
        '(pins 1-9) and PRPC011SAAN-RC 1x11 (pins 10-20) on the top row; one of each per board; strips added 2026-09-08, bottom '
        'row re-cut 2026-09-09 around the four-position LiPo gap')
NOTE = ('Pin field ZULU-DIP37: 40 pins of 1.016 mm on 2.54 mm pitch, two rows 22.86 mm (0.900 in) apart, numbered 1-40 straight '
        'through and skipping both landings. Top row 1-9 (x 59.69..39.37), FOUR positions for the micro-USB X1 (36.83..29.21), '
        '10-20 (26.67..1.27). Bottom row 21-26 (59.69..46.99), FOUR positions for the LiPo header X4 (44.45..36.83), 27-40 '
        '(34.29..1.27). Both gaps are 12.70 mm between the neighbouring pin centres, 11.176 mm clear: the JST B2B-PH-SM4-TB body '
        'is 7.95 mm, so 1.61 mm each side. Reworked 2026-09-09 from the old 44-position pattern: +5V-INPUT with D2/D3, GND5, GND3 '
        'and +3.3V2 removed, CHAN12/CHAN13 moved to pins 2/3, the bottom row closed up and renumbered. Three grounds (1, 20, 21); '
        '3.3 V for the header is pin 17 alone; pin 22 VU sources the 4.4 V rail. THE PCB FOOTPRINT MUST BE REDRAWN with 40 pads '
        'named 1-40 in these positions -- the imported ZULU-DIP37 still names 44. Sullins PRPC strips fit the holes (0.64 mm '
        'square pins, Sullins recommends 1.02 mm). Digi-Key 2026-09-09: PRPC006SAAN-RC 4,529 at $0.13, PRPC014SAAN-RC 663 at '
        '$0.28; 2026-09-08: PRPC009SAAN-RC 1,201 at $0.18, PRPC011SAAN-RC 428 at $0.22. Alternate: any 2.54 mm 1x40 breakaway '
        'strip (LCSC Boomele C2337, 81,690) cut to 14 + 11 + 9 + 6.')
FRAME = ('X2: 40 pins on a 2.54 mm grid, rows 22.86 mm (0.900 in) apart, numbered 1-40 straight ~1'
         'through from the right and skipping both landings, as the top row has always done. ~1'
         'TOP ROW, x 59.69 down to 1.27: GND, CHAN12, CHAN13, then CHAN-CLK and CHAN0..CHAN3 ~1'
         '  (pins 4-8), CHAN4 (pin 9), CHAN5..CHAN11 (10-16), +3.3V, +1.8V, +1.0V, GND. ~1'
         '  FOUR positions between pin 9 and pin 10 -- x 36.83, 34.29, 31.75, 29.21 -- are ~1'
         '  RESERVED, not spare: the landing for the edge-mounted micro-USB X1, 7.80 mm of ~1'
         '  copper in 11.176 mm clear, centred with 1.69 mm each side. ~1'
         'BOTTOM ROW, x 59.69 down to 1.27: GND, VU, RST# (pins 21-23), CHAN14..CHAN16 (24-26), ~1'
         '  FOUR positions between pin 26 and pin 27 -- x 44.45, 41.91, 39.37, 36.83 -- are ~1'
         '  RESERVED for the top-side LiPo header X4 (JST B2B-PH-SM4-TB, opposite the USB): ~1'
         '  7.95 mm of body in the same 11.176 mm clear, 1.61 mm each side, ~1'
         '  then CHAN17..CHAN28 (pins 27-38), ANALOG-IO0, ANALOG-IO1 (39, 40). ~1'
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
    N = len(recs)
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
    if rows == {1119, 1109, 1099}:
        raise SystemExit('CHAN14-16 already sit on rows 24-26; nothing done')
    assert rows == {1109, 1099, 1089}, rows
    moved = remapped = 0
    for i in range(N):
        h, b = recs[i]
        if root.get(i) in movers:                                       # the three sliding gate copies
            b = shift(b, DY); moved += 1
        elif owner_list_index(b) is None:
            p = wire_pts(b)
            if p and len(p) == 2 and p[0][0] == 325 and p[1][0] == 355 and p[0][1] == p[1][1] and p[0][1] in rows:
                b = shift(b, DY); moved += 1
            elif b.startswith(b'|RECORD=25|') and num(b, 'Location.X') == 355 and num(b, 'Location.Y') in rows:
                b = shift(b, DY); moved += 1
        if b.startswith(b'|RECORD=2|') and owner_list_index(b) in copies:
            d = int(field(b, 'Designator'))
            if d in REMAP:
                b = set_field(b, 'Designator', str(REMAP[d])); remapped += 1
        if b.startswith(b'|RECORD=41|') and owner_list_index(b) in copies:
            name = field(b, 'Name')
            if name == 'MANF#': b = set_field(b, 'Text', MANF)
            elif name == 'SPEC': b = set_field(b, 'Text', SPEC)
            elif name == 'NOTE': b = set_field(b, 'Text', NOTE)
        recs[i][1] = b
    frames = [i for i, (h, b) in enumerate(recs) if b.startswith(b'|RECORD=28|') and (field(b, 'Text') or '').startswith('X2: 40 pins on a 2.54 mm grid in a 44-position')]
    assert len(frames) == 1, frames
    recs[frames[0]][1] = set_field(recs[frames[0]][1], 'Text', FRAME)
    blob = join(recs)
    write_stream(path, 'FileHeader', blob)
    assert read_stream(path, 'FileHeader') == blob
    print(f'sheet 2: {len(recs)} records unchanged in count ({moved} shifted, {remapped} designators remapped)')
    verify(path)


CATALOGUE = ('DeviceName', 'LibraryName', 'DeviceSetName', 'MANF', 'MANF#', 'SPEC', 'NOTE')


def verify(path):
    recs = split(read_stream(path, 'FileHeader'))
    assert int(field(recs[0][1], 'Weight')) == len(recs) - 1
    copies = [i for i, (h, b) in enumerate(recs) if b.startswith(b'|RECORD=1|') and field(b, 'LibReference') == 'ZULU-CONN']
    assert len(copies) == 41
    assert sorted(int(field(recs[ci][1], 'CurrentPartId')) for ci in copies) == list(range(1, 42))
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
        assert {f'GateName_{n}' for n in range(1, 42)} <= set(names)
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
    for pad, (gy, py) in rows.items():                                  # 21-26 on 1149..1099, 27-40 on 1049..919
        want = 1149 - 10 * (pad - 21) if pad <= 26 else 1049 - 10 * (pad - 27)
        assert gy == py == want, (pad, gy, py, want)
    labels = {(num(b, 'Location.X'), num(b, 'Location.Y')) for h, b in recs if b.startswith(b'|RECORD=25|') and owner_list_index(b) is None}
    wires = {wire_pts(b) for h, b in recs if b.startswith(b'|RECORD=27|') and owner_list_index(b) is None}
    for pad, (gy, py) in rows.items():
        assert ((325, gy), (355, gy)) in wires and (355, gy) in labels, pad
    for y in (1089, 1079, 1069, 1059):                                  # the four-position LiPo gap
        assert (355, y) not in labels and ((325, y), (355, y)) not in wires, y
    t = dict(table)
    assert sorted(t) == list(range(1, 41)), sorted(t)
    assert t[23] == 'RST#' and t[24] == 'CHAN14' and t[26] == 'CHAN16' and t[27] == 'CHAN17' and t[38] == 'CHAN28' and t[40] == 'ANALOG-IO1'
    assert t[17] == '+3.3V' and t[22] == 'VU'
    print('verify: 41 copies, pins 1-40 in every copy, rows match the new numbering, four empty rows for the LiPo header')


if __name__ == '__main__':
    main(os.path.join(sys.argv[2], 'zulu_a7_2.SchDoc'))
