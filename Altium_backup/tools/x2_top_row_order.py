# -*- coding: utf-8 -*-
"""X2 pin field, 2026-09-09 (sixth pass): the top row put in channel order.

Follows x2_move_landing.py. The top row (the symbol's left column) is reordered so the channels
run straight up from CHAN-CLK without the CHAN12/CHAN13 pair sitting in front of them:

  before  1 GND2, 2 CHAN12, 3 CHAN13, 4 CHAN-CLK, 5-9 CHAN0-4, [USB landing],
          10-16 CHAN5-11, 17 +3.3V, 18 +1.8V, 19 +1.0V, 20 GND
  after   1 GND2, 2 CHAN-CLK, 3-9 CHAN0-6, [USB landing],
          10-16 CHAN7-13, 17 +3.3V, 18 +1.8V, 19 +1.0V, 20 GND

The 9 + landing + 11 split, the landing positions and the whole bottom row are untouched, and the
pins stay numbered 1-40 by position, so each signal takes the pin number of the place it moves to:
CHAN-CLK 4->2, CHAN0..CHAN4 5..9 -> 3..7, CHAN5/CHAN6 10/11 -> 8/9, CHAN7..CHAN11 12..16 -> 10..14,
CHAN12/CHAN13 2/3 -> 15/16. Sixteen gate copies move on the sheet with their wires and net labels,
every pin record in all 41 copies is remapped, and the X2 NOTE and the text frame are rewritten.
Connectivity does not change; only which X2 pad each net lands on. Refuses to run twice.

    python tools/x2_top_row_order.py tools "Imported zulu_a7.PrjPcb"
"""
import sys, os, re
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

TOP_ORDER = ['GND2', 'CHAN-CLK', 'CHAN0', 'CHAN1', 'CHAN2', 'CHAN3', 'CHAN4', 'CHAN5', 'CHAN6',
             'CHAN7', 'CHAN8', 'CHAN9', 'CHAN10', 'CHAN11', 'CHAN12', 'CHAN13',
             '+3.3V', '+1.8V', '+1.0V', 'GND']
COORD_KEYS = re.compile(rb'\|(Location\.X|Location\.Y|X\d+|Y\d+)=(-?\d+)')
NOTE_OLD = 'top row pins 1-9 (x 59.69..39.37), FOUR positions for the micro-USB X1 (36.83..29.21), pins 10-20 (26.67..1.27);'
NOTE_NEW = ('top row pins 1-9 (x 59.69..39.37) = GND, CHAN-CLK, CHAN0..CHAN6, FOUR positions for the micro-USB X1 (36.83..29.21), '
            'pins 10-20 (26.67..1.27) = CHAN7..CHAN13, +3.3V, +1.8V, +1.0V, GND, in channel order since 2026-09-09;')
FRAME_OLD = ('TOP ROW, x 59.69 down to 1.27: GND, CHAN12, CHAN13, then CHAN-CLK and CHAN0..CHAN3 ~1'
             '  (pins 4-8), CHAN4 (pin 9), CHAN5..CHAN11 (10-16), +3.3V, +1.8V, +1.0V, GND. ~1')
FRAME_NEW = ('TOP ROW, x 59.69 down to 1.27: GND (pin 1), CHAN-CLK (2), CHAN0..CHAN6 (3-9), ~1'
             '  then CHAN7..CHAN13 (10-16), +3.3V, +1.8V, +1.0V, GND (17-20). ~1')


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


def row_of(pad):
    """the y of a top-row pad: 1-9 above the USB landing, 10-20 below it"""
    return 1149 - 10 * (pad - 1) if pad <= 9 else 1019 - 10 * (pad - 10)


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
    gate_of, pad_of = {}, {}
    for i, (h, b) in enumerate(recs):
        r = root.get(i)
        if r not in copies:
            continue
        if b.startswith(b'|RECORD=41|') and field(b, 'Name') == 'GATE':
            gate_of[r] = field(b, 'Text')
        elif b.startswith(b'|RECORD=2|') and field(b, 'OwnerPartId') == field(recs[r][1], 'CurrentPartId'):
            pad_of[r] = int(field(b, 'Designator'))
    top = {ci for ci in copies if num(recs[ci][1], 'Location.X') == 185 and ci in pad_of}
    assert len(top) == 20, len(top)
    assert {gate_of[ci] for ci in top} == set(TOP_ORDER), sorted({gate_of[ci] for ci in top} ^ set(TOP_ORDER))
    new_pad = {name: n for n, name in enumerate(TOP_ORDER, 1)}
    pad_map = {pad_of[ci]: new_pad[gate_of[ci]] for ci in top}
    assert sorted(pad_map) == list(range(1, 21)) and sorted(pad_map.values()) == list(range(1, 21))
    if all(k == v for k, v in pad_map.items()):
        raise SystemExit('the top row is already in this order; nothing done')
    dy_of_copy, dy_of_row = {}, {}
    for ci in top:
        dy = row_of(pad_map[pad_of[ci]]) - row_of(pad_of[ci])
        if dy:
            dy_of_copy[ci] = dy
            dy_of_row[row_of(pad_of[ci])] = dy                          # the wire and label on that row move with it
    moved = remapped = 0
    for i in range(len(recs)):
        h, b = recs[i]
        r = root.get(i)
        if r in dy_of_copy:
            b = shift(b, dy_of_copy[r]); moved += 1
        elif owner_list_index(b) is None:
            p = wire_pts(b)
            if p and len(p) == 2 and p[0][0] == 155 and p[1][0] == 185 and p[0][1] == p[1][1] and p[0][1] in dy_of_row:
                b = shift(b, dy_of_row[p[0][1]]); moved += 1
            elif b.startswith(b'|RECORD=25|') and num(b, 'Location.X') == 155 and num(b, 'Location.Y') in dy_of_row:
                b = shift(b, dy_of_row[num(b, 'Location.Y')]); moved += 1
        if b.startswith(b'|RECORD=2|') and owner_list_index(b) in copies:
            d = int(field(b, 'Designator'))
            if d in pad_map and pad_map[d] != d:
                b = set_field(b, 'Designator', str(pad_map[d])); remapped += 1
        if b.startswith(b'|RECORD=41|') and owner_list_index(b) in copies and field(b, 'Name') == 'NOTE':
            t = field(b, 'Text'); assert NOTE_OLD in t
            b = set_field(b, 'Text', t.replace(NOTE_OLD, NOTE_NEW))
        recs[i][1] = b
    frames = [i for i, (h, b) in enumerate(recs) if b.startswith(b'|RECORD=28|') and FRAME_OLD in (field(b, 'Text') or '')]
    assert len(frames) == 1, frames
    recs[frames[0]][1] = set_field(recs[frames[0]][1], 'Text', field(recs[frames[0]][1], 'Text').replace(FRAME_OLD, FRAME_NEW))
    blob = join(recs)
    write_stream(path, 'FileHeader', blob)
    assert read_stream(path, 'FileHeader') == blob
    print(f'sheet 2: {moved} records shifted, {remapped} designators remapped')
    print('  pad map: ' + ', '.join(f'{a}->{b}' for a, b in sorted(pad_map.items()) if a != b))
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
        pid = field(recs[ci][1], 'CurrentPartId')
        vis = [b for b in pins if field(b, 'OwnerPartId') == pid]
        gate = [field(b, 'Text') for b in kids[ci] if b.startswith(b'|RECORD=41|') and field(b, 'Name') == 'GATE']
        if vis:
            pad = int(field(vis[0], 'Designator'))
            table.append((pad, gate[0]))
            rows[pad] = (num(recs[ci][1], 'Location.X'), num(recs[ci][1], 'Location.Y'), num(vis[0], 'Location.Y'))
    for pad, name in sorted(table):
        print(f'   pin {pad:>2} {name}')
    t = dict(table)
    assert sorted(t) == list(range(1, 41))
    assert [t[n] for n in range(1, 21)] == TOP_ORDER, [t[n] for n in range(1, 21)]
    labels = {(num(b, 'Location.X'), num(b, 'Location.Y')) for h, b in recs if b.startswith(b'|RECORD=25|') and owner_list_index(b) is None}
    wires = {wire_pts(b) for h, b in recs if b.startswith(b'|RECORD=27|') and owner_list_index(b) is None}
    for pad, (x, gy, py) in rows.items():
        want = row_of(pad) if pad <= 20 else (1149 - 10 * (pad - 21) if pad <= 29 else 1019 - 10 * (pad - 30))
        assert gy == py == want, (pad, gy, py, want)
        stub = 155 if pad <= 20 else 355
        a, c = ((155, gy), (185, gy)) if pad <= 20 else ((325, gy), (355, gy))
        assert (a, c) in wires and (stub, gy) in labels, pad
    for y in (1059, 1049, 1039, 1029):                                  # both landings share these four rows
        for x, s in ((155, 185), (325, 355)):
            assert ((x, y), (s, y)) not in wires and ((s if x == 155 else s), y) not in labels, y
    print('verify: pins 1-40, top row in channel order, every gate on the row of its pad, both landings clear')


if __name__ == '__main__':
    main(os.path.join(sys.argv[2], 'zulu_a7_2.SchDoc'))
