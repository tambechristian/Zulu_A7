"""Tidy sheet 1 after replace_u5_tps63802.py (2026-11-09, user request): the taller TPS63802 symbol's GND port ran into
U6, so the U6 and U7 blocks (regulators, caps, inductors, wires, ports, junctions) move down 40 units as one piece.
Also: the TPS63802 part-name text moves off the GND/AGND pin names, and R109/R110's designator/value texts move off
the wires (horizontal, R109 above the VCC3V3 wire, R110 left of the resistor).
    python tools/tidy_regulator_sheet.py <sheet-1 SchDoc>        (close the project in Altium first)
Refuses if a wire crosses the block's edge (it would be stretched) or the U5 texts are not where the replace left them."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schdoc import del_field, field, join, owner, read_stream, set_field, split, subtree, write_stream  # noqa: E402

BOX = (370, 268, 730, 468)          # x0, y0, x1, y1: everything of U6/U7's blocks, nothing of U5's
DY = -40
TEXTS = {  # (component designator, parameter name or 'Designator'): (x, y)
    ('U5', 'PartName'): (505, 546),
    ('R109', 'Designator'): (640, 563), ('R109', 'Comment'): (664, 563),
    ('R110', 'Designator'): (628, 517), ('R110', 'Comment'): (628, 509)}


def num(b, k):
    v, f = field(b, k), field(b, k + '_Frac')
    return (int(v) if v else 0) + (int(f) if f else 0) / 1e5


def inside(x, y):
    return BOX[0] <= x <= BOX[2] and BOX[1] <= y <= BOX[3]


def moved(b):
    for kx, ky in [('Location.X', 'Location.Y'), ('Corner.X', 'Corner.Y')] + [('X%d' % k, 'Y%d' % k) for k in range(1, 60)] \
            + [('EX%d' % k, 'EY%d' % k) for k in range(1, 60)]:
        if field(b, ky) is not None or field(b, ky + '_Frac') is not None:
            b = set_field(b, ky, '%d' % (int(field(b, ky) or 0) + DY))
    return b


def main():
    path = sys.argv[1]
    recs = split(read_stream(path))
    comps = [i for i, (h, b) in enumerate(recs) if field(b, 'RECORD') == '1']
    move = set()
    for c in comps:
        if inside(num(recs[c][1], 'Location.X'), num(recs[c][1], 'Location.Y')):
            move |= subtree(recs, [c])
    for i, (h, b) in enumerate(recs):
        if owner(b) not in (None, 0) or field(b, 'RECORD') == '1':
            continue
        if field(b, 'RECORD') == '27':
            n = int(field(b, 'LocationCount'))
            pts = [(num(b, 'X%d' % k), num(b, 'Y%d' % k)) for k in range(1, n + 1)]
            ins = [inside(*p) for p in pts]
            if all(ins):
                move.add(i)
            elif any(ins):
                sys.exit('REFUSED: wire %d crosses the block edge: %s' % (i, pts))
        elif field(b, 'Location.X') is not None and inside(num(b, 'Location.X'), num(b, 'Location.Y')):
            move |= subtree(recs, [i])
    names = sorted(field(b, 'Text') for h, b in recs if field(b, 'RECORD') == '34' and owner(b) in move)
    if names != ['C148', 'C149', 'C82', 'C84', 'L2', 'L3', 'U6', 'U7']:
        sys.exit('REFUSED: the block holds %s' % names)
    for i in move:
        recs[i][1] = moved(recs[i][1])

    for (des, name), (x, y) in TEXTS.items():
        c = [owner(b) for h, b in recs if field(b, 'RECORD') == '34' and field(b, 'Text') == des]
        if len(c) != 1:
            sys.exit('REFUSED: %d parts named %s' % (len(c), des))
        hit = [i for i, (h, b) in enumerate(recs) if owner(b) == c[0] and field(b, 'Name') == name
               and field(b, 'RECORD') in ('34', '41')]
        if len(hit) != 1:
            sys.exit('REFUSED: %s %s not found' % (des, name))
        b = del_field(del_field(del_field(recs[hit[0]][1], 'Location.X_Frac'), 'Location.Y_Frac'), 'Orientation')
        recs[hit[0]][1] = set_field(set_field(b, 'Location.X', str(x)), 'Location.Y', str(y))
    write_stream(path, join(recs))
    print('%s: moved %d records (%s) by %d; %d texts placed' % (os.path.basename(path), len(move), ' '.join(names), DY,
                                                             len(TEXTS)))


if __name__ == '__main__':
    main()
