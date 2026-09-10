# -*- coding: utf-8 -*-
"""2026-09-09: the three places where a rail name has nowhere to put a symbol get room made.

`tools/rail_ports.py` converts a rail net label into a power port only where the symbol actually
fits, and it refuses at exactly the three spots review finding 5 singled out. This runs first and
makes room; after it, all three convert. Nothing here changes a connection -- every group moved is a
rigid translation of a self-contained island, and the drawing's own connectivity signature is
compared before and after.

1. SHEET 3, THE U3 DECOUPLING LADDER. Seven rows on a 30-unit pitch, each `pin 54 -GND- ||C|| -
   VCC3V3- pin 1`. A ground bar with its name under it is 30 units tall, so at a 30-unit pitch it
   lands on the next row down; measured, the GND text would finish 0.5 units above the next row's
   wire. The pitch goes to 45 -- rows move up 0, 15, 30 ... 90, the bottom row staying put -- which
   leaves 15 units of air under each bar. There is 145 units of headroom above the ladder before
   U3's own body starts at y 797, and the new top row reaches y 727, so 55 of it is still spare.

   The two labels also move along their own wire to the middle of the segment they name: GND from
   632 to 657 (its wire runs 625 to 690) and VCC3V3 from 715 to 745 (710 to 780). At 715 the supply
   arrow overlapped C3's left plate at x 698 by 0.4 units, which is the whole reason that half of
   the ladder could not convert; at 745 it is centred in the gap between the cap and U3's pin.

2. SHEET 6, THE BULK COLUMN. Three stacks one above the other, each a rail label on top, caps, and a
   ground port at the bottom. The gap between them is 70 units and a stack needs about 99 from the
   top of a supply arrow's name to the bottom of a ground bar's, so each ground bar was drawn
   straight through the next stack's supply label: the GND bar of the VCC1V0 stack occupies y 612
   to 632 and the `VCC1V8` label sits at 612 to 619 inside it.

   The column is boxed in by C86/C92's wires at y 767 and U1C's body at y 452 -- 315 units, which
   holds two stacks and not three. So the VCC3V3 stack moves out to (+160, +71), into the empty band
   between U1C's right edge at x 216 and U1A's left edge at x 376 which holds nothing at all between
   y 460 and y 710; the sheet already draws its four bank-VCCO banks side by side, so a bank beside a
   bank is this sheet's own idiom. The VCC1V8 stack then drops 40 into the space that leaves, which
   puts 11 units between the VCC1V0 ground bar's name and the top of its own supply arrow, and 40
   between its own ground bar and U1C.

   Moving the VCC1V0 stack UP instead was tried and is wrong: 40 is what the VCC1V8 stack needs, and
   40 puts the `VCC1V0` label under the VCCAUX block's ground symbol at (106,757), which occupies x
   95.5 to 116.5. Down was the direction with room in it.

3. SHEET 4, Q1's SUPPLY LABEL. `VCC3V3` names the stub that feeds C38, and the stub runs LEFT out of
   the junction at (357,222) to a dangling end at 347 with the label right-justified on it -- so its
   glyphs run from 327.8 to 353.5 and Q1's pin-2 ground drop at x 337 goes straight through them, 3
   points above the ground symbol. It reads as VDD grounded. The stub is turned to run DOWN instead,
   from (357,222) to (357,202), and the label goes to its end left-justified, into clear space
   between the ground bar (which ends at x 347.4) and C38's designator (which starts at 376).

    python tools/rail_layout.py tools "Imported zulu_a7.PrjPcb"
"""
import sys, os, collections
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field
from sheet5_right_margin import (num, oi, rectype, points, fonts_of, roots, drawn_boxes, signature)

LADDER_ROWS = [457, 487, 517, 547, 577, 607, 637]     # bottom to top, 30 apart
LADDER_PITCH = 45
LADDER_X = (620, 790)
LADDER_PLACE_X = (625, 700, 780)
LABEL_MOVE = {'GND': 657 - 632, 'VCC3V3': 745 - 715}  # to the middle of the segment each names

STACKS = [                                  # the VCC3V3 stack leaves first, then the VCC1V8 stack
    dict(name='VCC3V3 bulk', desigs={'C145', 'C146'}, win=(70, 140, 485, 550),
         dx=160, dy=71, want=(2, 9)),       # drops into the empty band beside U1C
    dict(name='VCC1V8 bulk', desigs={'C144'}, win=(70, 125, 552, 620),
         dx=0, dy=-40, want=(1, 4)),        # into the room the VCC3V3 stack just left
]

Q1_STUB_OLD = ((347, 222), (357, 222))
Q1_STUB_NEW = ((357, 222), (357, 202))
Q1_LABEL_OLD = (353, 222)
Q1_LABEL_NEW = (357, 202)

XKEYS = ['Location.X', 'Corner.X'] + [f'X{k}' for k in range(1, 9)]
YKEYS = ['Location.Y', 'Corner.Y'] + [f'Y{k}' for k in range(1, 9)]


def shift(b, dx, dy):
    for k, d in [(k, dx) for k in XKEYS] + [(k, dy) for k in YKEYS]:
        if d:
            v = num(b, k)
            if v is not None:
                b = set_field(b, k, str(v + d))
    return b


def group(recs, root, place, desig, want_place, win):
    """placement indices + every record they own + the free records inside the window."""
    xl, xr, yl, yh = win
    owned = [i for i in range(len(recs)) if root[i] in want_place]
    free = []
    for i, (h, b) in enumerate(recs):
        if root[i] is not None or i in place:
            continue
        P = points(b)
        if P and all(xl <= x <= xr and yl <= y <= yh for x, y in P):
            free.append(i)
    return owned + free, len(want_place), len(free)


def sheet3(path):
    recs = split(read_stream(path, 'FileHeader'))
    root, place = roots(recs)
    fonts = fonts_of(recs)
    sig = signature(recs)
    labels = [i for i, (h, b) in enumerate(recs)
              if rectype(b) == 25 and field(b, 'Text') in LABEL_MOVE
              and num(b, 'Location.Y') in LADDER_ROWS and LADDER_X[0] <= num(b, 'Location.X') <= LADDER_X[1]]
    assert len(labels) == 14, f'expected 14 ladder labels, found {len(labels)}'
    tops = [num(recs[i][1], 'Location.Y') for i in place
            if num(recs[i][1], 'Location.Y') == 727]
    if tops:
        raise SystemExit('the sheet 3 ladder is already on a 45-unit pitch; nothing done')
    moved = 0
    # top row first: a row that has moved up must never land in a window not yet processed
    for k in range(len(LADDER_ROWS) - 1, -1, -1):
        y = LADDER_ROWS[k]
        dy = (LADDER_PITCH - 30) * k
        want = {i for i in place if num(recs[i][1], 'Location.Y') == y
                and num(recs[i][1], 'Location.X') in LADDER_PLACE_X}
        assert len(want) == 3, f'row {y}: {len(want)} placements, expected 3'
        idx, np_, nf = group(recs, root, place, None, want,
                             (LADDER_X[0], LADDER_X[1], y - 8, y + 8))
        assert nf == 4, f'row {y}: {nf} free records, expected 2 wires and 2 labels'
        if dy:
            for i in idx:
                recs[i][1] = shift(recs[i][1], 0, dy)
            moved += len(idx)
    for i in labels:
        b = recs[i][1]
        recs[i][1] = shift(b, LABEL_MOVE[field(b, 'Text')], 0)
    print(f'  sheet 3: ladder re-spaced 30 -> {LADDER_PITCH}, {moved} records moved, '
          f'{len(labels)} labels centred on their segment')
    return recs, sig


def sheet6(path):
    recs = split(read_stream(path, 'FileHeader'))
    root, place = roots(recs)
    des = {oi(b): field(b, 'Text') for h, b in recs if b.startswith(b'|RECORD=34|')}
    sig = signature(recs)
    if any(num(recs[i][1], 'Location.X') and num(recs[i][1], 'Location.X') > 200
           and des.get(i) in ('C145', 'C146') for i in place):
        raise SystemExit('the sheet 6 bulk column has already been re-laid-out; nothing done')
    total = 0
    for S in STACKS:
        want = {i for i in place if des.get(i) in S['desigs']}
        idx, np_, nf = group(recs, root, place, des, want, S['win'])
        assert (np_, nf) == S['want'], f"{S['name']}: {(np_, nf)} placements/free, expected {S['want']}"
        for i in idx:
            recs[i][1] = shift(recs[i][1], S['dx'], S['dy'])
        total += len(idx)
        print(f"  sheet 6: {S['name']} moved ({S['dx']:+}, {S['dy']:+}), "
              f"{np_} caps, {nf} free records")
    return recs, sig


def sheet4(path):
    recs = split(read_stream(path, 'FileHeader'))
    sig = signature(recs)
    wire = [i for i, (h, b) in enumerate(recs)
            if rectype(b) == 27 and tuple(points(b)) == Q1_STUB_OLD]
    lab = [i for i, (h, b) in enumerate(recs)
           if rectype(b) == 25 and field(b, 'Text') == 'VCC3V3'
           and tuple(points(b)) == (Q1_LABEL_OLD,)]
    if not wire or not lab:
        raise SystemExit("Q1's supply stub has already been turned; nothing done")
    assert len(wire) == 1 and len(lab) == 1, (wire, lab)
    b = recs[wire[0]][1]
    for k, v in (('X1', Q1_STUB_NEW[0][0]), ('Y1', Q1_STUB_NEW[0][1]),
                 ('X2', Q1_STUB_NEW[1][0]), ('Y2', Q1_STUB_NEW[1][1])):
        b = set_field(b, k, str(v))
    recs[wire[0]][1] = b
    b = recs[lab[0]][1]
    b = set_field(set_field(b, 'Location.X', str(Q1_LABEL_NEW[0])),
                  'Location.Y', str(Q1_LABEL_NEW[1]))
    recs[lab[0]][1] = set_field(b, 'Justification', '0')      # bottom left, glyphs run right
    print(f"  sheet 4: Q1's supply stub turned down to {Q1_STUB_NEW[1]}, its label to "
          f"{Q1_LABEL_NEW} left-justified")
    return recs, sig


def save(path, recs, sig, name):
    blob = join(recs)
    write_stream(path, 'FileHeader', blob)
    assert read_stream(path, 'FileHeader') == blob
    back = split(read_stream(path, 'FileHeader'))
    assert int(field(back[0][1], 'Weight')) == len(back) - 1, 'header count'
    assert all(b.endswith(b'\x00') for h, b in back), 'a record lost its terminator'
    assert signature(back) == sig, f'{name}: the drawing connectivity changed'
    fonts = fonts_of(back)
    boxes = drawn_boxes(back, fonts)
    lo = min(e[2][0] for e in boxes), min(e[2][1] for e in boxes)
    assert lo[0] > 0 and lo[1] > 0, f'{name}: something has been pushed off the sheet {lo}'
    print(f'    verify: {len(back)} records, {len(boxes)} drawn objects, connectivity unchanged')


def main(prj):
    for name, fn in (('zulu_a7_3', sheet3), ('zulu_a7_6', sheet6), ('zulu_a7_4', sheet4)):
        path = os.path.join(prj, name + '.SchDoc')
        recs, sig = fn(path)
        save(path, recs, sig, name)


if __name__ == '__main__':
    main(sys.argv[2])
