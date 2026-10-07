# -*- coding: utf-8 -*-
"""X2 pin field, 2026-10-07: the four power pins at the end of the top row re-ordered.

Follows x2_top_row_order.py. The user asked for GND first and the rails after it:

  before  17 +3.3V (VCC3V3), 18 +1.8V (VCC1V8), 19 +1.0V (VCC1V0), 20 GND
  after   17 GND, 18 +3.3V (VCC3V3), 19 +1.8V (VCC1V8), 20 +1.0V (VCC1V0)

Pin 16 (CHAN13), the rest of the top row and the whole bottom row are untouched. As in the sixth
pass, the pins stay numbered by position, so each gate copy moves on the sheet to the row of its
new pin together with its wire and net label, and every pin record in all 41 copies is remapped
(17->18, 18->19, 19->20, 20->17). The X2 NOTE and the sheet's text frame are rewritten. Only which
X2 pad each of the four nets lands on changes. Refuses to run twice.

    python tools/x2_power_pins.py tools "Imported zulu_a7.PrjPcb"
"""
import sys, os
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field
import x2_top_row_order as base

TOP_ORDER = ['GND2', 'CHAN-CLK', 'CHAN0', 'CHAN1', 'CHAN2', 'CHAN3', 'CHAN4', 'CHAN5', 'CHAN6',
             'CHAN7', 'CHAN8', 'CHAN9', 'CHAN10', 'CHAN11', 'CHAN12', 'CHAN13',
             'GND', '+3.3V', '+1.8V', '+1.0V']
NOTE_EDITS = [
    ('pins 10-20 (26.67..1.27) = CHAN7..CHAN13, +3.3V, +1.8V, +1.0V, GND, in channel order since 2026-09-09;',
     'pins 10-20 (26.67..1.27) = CHAN7..CHAN13, GND, +3.3V, +1.8V, +1.0V (channel order since 2026-09-09, '
     'power pins re-ordered 2026-10-07);'),
    ('Three grounds (1, 20, 21); 3.3 V for the header is pin 17 alone;',
     'Three grounds (1, 17, 21); 3.3 V for the header is pin 18 alone;'),
]
FRAME_EDITS = [
    ('  then CHAN7..CHAN13 (10-16), +3.3V, +1.8V, +1.0V, GND (17-20). ~1',
     '  then CHAN7..CHAN13 (10-16), GND, +3.3V, +1.8V, +1.0V (17-20). ~1'),
    ('THREE grounds: pins 1, 20, 21.  Pin 17 is the only +3.3V pin.',
     'THREE grounds: pins 1, 17, 21.  Pin 18 is the only +3.3V pin.'),
]
num, owner_list_index, wire_pts, shift, row_of = (base.num, base.owner_list_index, base.wire_pts,
                                                  base.shift, base.row_of)


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
        raise SystemExit('the power pins are already in this order; nothing done')
    assert {a: b for a, b in pad_map.items() if a != b} == {17: 18, 18: 19, 19: 20, 20: 17}, pad_map
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
            t = field(b, 'Text')
            for old, new in NOTE_EDITS:
                assert t.count(old) == 1, old
                t = t.replace(old, new)
            b = set_field(b, 'Text', t)
        recs[i][1] = b
    frames = [i for i, (h, b) in enumerate(recs) if b.startswith(b'|RECORD=28|') and FRAME_EDITS[0][0] in (field(b, 'Text') or '')]
    assert len(frames) == 1, frames
    t = field(recs[frames[0]][1], 'Text')
    for old, new in FRAME_EDITS:
        assert t.count(old) == 1, old
        t = t.replace(old, new)
    recs[frames[0]][1] = set_field(recs[frames[0]][1], 'Text', t)
    blob = join(recs)
    write_stream(path, 'FileHeader', blob)
    assert read_stream(path, 'FileHeader') == blob
    print(f'sheet 2: {moved} records shifted, {remapped} designators remapped')
    print('  pad map: ' + ', '.join(f'{a}->{b}' for a, b in sorted(pad_map.items()) if a != b))
    base.TOP_ORDER = TOP_ORDER                                          # verify() checks the row against this order
    base.verify(path)


if __name__ == '__main__':
    main(os.path.join(sys.argv[2], 'zulu_a7_2.SchDoc'))
