# -*- coding: utf-8 -*-
"""All sheets, 2026-09-09: net labels stop hanging below their wires.

THE DEFECT. Altium's Justification is a 3x3 anchor grid, h = j % 3 (0 left, 1 centre, 2 right) and
v = j // 3 (0 bottom, 1 middle, 2 top). A label with v = 2 is anchored at the TOP of its text box,
so although the anchor sits exactly on the wire, the glyphs are drawn UNDERNEATH it. Pin designators
are anchored at the bottom and sit above their own wires. Rows on these sheets are 10 units apart
and the text is about 6.8 units tall, which puts every net name on the next pin's line.

Measured on the exported PDF before this ran, sheet 2: the label CHAN0 -- which is X2 pin 3 -- has
its glyph box at y 100.88..104.00, the digit 4 is at 101.60..104.72, and its own digit 3 is at
97.29..100.40. The name overlaps the wrong number by 2.4 points of a 3.1 point box. Reading across
the row to find which pin a signal is on, which is exactly what the 40-pin footprint work needs,
gives the wrong answer unless the pin name inside the symbol saves you. On the Pmod it does not:
pin 11's GND lands on the PMOD-10 line.

THE FIX. Subtract 6 from the justification of every horizontal net label that has one of the top
values, which moves the anchor from the top of the box to the bottom and leaves the horizontal half
alone: 6 -> 0, 7 -> 1, 8 -> 2. The glyphs move up by their own height, about 6.8 units, which lands
them on their own pin's line (predicted 97.78..100.90 for CHAN0 against its own digit at
97.29..100.40). Nothing moves electrically: a label's Location is its attachment point and is not
touched, so the netlist must come out identical.

The 117 labels already anchored at the bottom are left alone -- and their existence is the other
half of the argument, because the sheets are currently inconsistent with themselves.

NOT TOUCHED: eight ROTATED labels that are also top-justified (two on sheet 1, three on sheet 4,
three on sheet 5). For a label at 90 degrees the vertical half of the justification moves the glyphs
sideways rather than up, so the same flip is not obviously right, and eight is few enough to judge
by eye. They are listed when this runs.

    python tools/label_justification.py tools "Imported zulu_a7.PrjPcb"
"""
import sys, os, collections
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

FLIP = {'6': '0', '7': '1', '8': '2'}          # top row of the anchor grid -> bottom row


def oi(b):
    o = field(b, 'OwnerIndex')
    return int(o) + 1 if o is not None else None


def main(prj):
    total, skipped = 0, []
    for n in range(7):
        path = os.path.join(prj, f'zulu_a7_{n}.SchDoc')
        recs = split(read_stream(path, 'FileHeader'))
        before = len(recs)
        assert int(field(recs[0][1], 'Weight')) == before - 1, f'sheet {n} header count'
        hit = 0
        for i, (h, b) in enumerate(recs):
            if not b.startswith(b'|RECORD=25|') or oi(b) is not None:
                continue                                    # RECORD=25 owned by a pin is a pin name
            j = field(b, 'Justification')
            if j not in FLIP:
                continue
            if (field(b, 'Orientation') or '0') != '0':
                skipped.append((n, field(b, 'Text'), j, field(b, 'Orientation')))
                continue
            recs[i][1] = set_field(b, 'Justification', FLIP[j])
            hit += 1
        if not hit:
            print(f'sheet {n}: nothing to do')
            continue
        assert len(recs) == before
        blob = join(recs)
        write_stream(path, 'FileHeader', blob)
        assert read_stream(path, 'FileHeader') == blob
        print(f'sheet {n}: {hit} net labels re-anchored to the bottom of their text')
        total += hit
    if not total:
        raise SystemExit('every horizontal net label is already bottom-anchored; nothing done')
    print(f'{total} labels moved above their wires')
    if skipped:
        print(f'{len(skipped)} rotated labels left alone, to be judged by eye:')
        for n, t, j, o in skipped:
            print(f'   sheet {n}: {t!r} justification {j}, orientation {o}')
    verify(prj)


def verify(prj):
    left = collections.Counter()
    for n in range(7):
        path = os.path.join(prj, f'zulu_a7_{n}.SchDoc')
        recs = split(read_stream(path, 'FileHeader'))
        assert int(field(recs[0][1], 'Weight')) == len(recs) - 1, f'sheet {n} header count'
        assert all(b.endswith(b'\x00') for h, b in recs), f'sheet {n} terminator'
        for h, b in recs:
            if b.startswith(b'|RECORD=25|') and oi(b) is None:
                j = field(b, 'Justification')
                if j in FLIP:
                    left[(n, field(b, 'Orientation') or '0')] += 1
    horiz = {k: v for k, v in left.items() if k[1] == '0'}
    assert not horiz, f'horizontal labels still top-anchored: {horiz}'
    print(f'verify: no horizontal net label is top-anchored on any sheet; '
          f'{sum(left.values())} rotated ones remain by design')


if __name__ == '__main__':
    main(sys.argv[2])
