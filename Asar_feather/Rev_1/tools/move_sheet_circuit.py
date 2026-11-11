"""Move everything on an Altium schematic sheet except its drawing frame by a fixed vector, as a hand drag would.

Made 2026-11-07 to give Zulu A7 sheet 7 (zulu_a7_6.SchDoc) the layout the user gave Asar A7 sheet 7: the FPGA-power
circuit moved up by (24, 178) units = (240, 1780) mil, which also puts it on the sheet's 100 mil snap grid.

What stays: the frame component (designator FRAME*) with everything it owns, the sheet-level lines that lie on the
frame border (the edges of the bounding box of all sheet-level polylines), and the sheet-level objects inside the
title block (the bounding box of the frame component's own points). Everything else moves: every coordinate
(Location, Corner, X1..Xn / Y1..Yn, EXn / EYn, with _Frac) of every other sheet-level record and of all its children.
A component's parameter with no Location sits at the origin; Altium's drag gives it the drag vector as its Location (it
adds Location.X / Location.Y after OwnerPartId), so this does the same. A pin's parameters (HiddenNetName, PinUniqueId)
keep no Location, as in Altium. Checked against the user's own drag of Asar A7 sheet 7: the same coordinates.

    python tools/move_sheet_circuit.py <sheet> --by 24,178 [--apply]

--by is in units of 10 mil (whole or fractional). Without --apply it only reports. Close the sheet in Altium first.
"""
import argparse
import os
import shutil
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schdoc import read_stream, split, join, write_stream  # noqa: E402
from snap_sheet_move import F, PAIR, parse, unparse, points, shift, top  # noqa: E402


def kept_records(P):
    """Indices of the records a circuit move leaves in place: frame subtree, border lines, title-block objects."""
    frames = set()
    for i, (pairs, _) in enumerate(P):
        d = dict(pairs)
        if d.get('RECORD') == '34' and (d.get('Text') or '').upper().startswith('FRAME') and 'OwnerIndex' in d:
            frames.add(int(d['OwnerIndex']) + 1)
    if len(frames) != 1:
        raise SystemExit('Refusing: expected one FRAME component, found %d' % len(frames))
    keep = {i for i in range(2, len(P)) if top(P, i) in frames}
    fpts = [p for i in keep for p in points(P[i][0]).values()]
    tb = (min(x for x, _ in fpts), min(y for _, y in fpts), max(x for x, _ in fpts), max(y for _, y in fpts))
    lines = [i for i in range(2, len(P)) if 'OwnerIndex' not in dict(P[i][0]) and dict(P[i][0]).get('RECORD') == '6']
    lpts = [p for i in lines for p in points(P[i][0]).values()]
    bx0, by0 = min(x for x, _ in lpts), min(y for _, y in lpts)
    bx1, by1 = max(x for x, _ in lpts), max(y for _, y in lpts)

    def on_border(x, y):
        return (x in (bx0, bx1) and by0 <= y <= by1) or (y in (by0, by1) and bx0 <= x <= bx1)
    for i in range(2, len(P)):
        d = dict(P[i][0])
        if 'OwnerIndex' in d or i in keep:
            continue
        pts = list(points(P[i][0]).values())
        if not pts:
            continue
        if d.get('RECORD') == '6' and all(on_border(x, y) for x, y in pts):
            keep.add(i)
        elif all(tb[0] <= x <= tb[2] and tb[1] <= y <= tb[3] for x, y in pts):
            keep.add(i)
    return keep, tb, (bx0, by0, bx1, by1)


def add_location(pairs, dx, dy):
    """A parameter with no Location: insert Location.X/Y (= the move) after OwnerPartId, as Altium does."""
    new = []
    for i, f in (('Location.X', dx), ('Location.Y', dy)):
        new.append([i, str(f // F)])
        if f % F:
            new.append([i + '_Frac', str(f % F)])
    keys = [k for k, _ in pairs]
    at = keys.index('OwnerPartId') + 1 if 'OwnerPartId' in keys else len(pairs)
    return pairs[:at] + new + pairs[at:]


def plan(P, dx, dy):
    keep, tb, border = kept_records(P)
    moves, adds = [], []
    for i in range(2, len(P)):
        if i in keep:
            continue
        t = top(P, i)
        if t in keep:
            continue
        pairs = P[i][0]
        d = dict(pairs)
        if points(pairs):
            moves.append(i)
        elif d.get('RECORD') == '41' and 'OwnerIndex' in d and not any(k and PAIR.match(k) for k, _ in pairs) \
                and dict(P[int(d['OwnerIndex']) + 1][0]).get('RECORD') == '1':
            adds.append(i)          # component parameters only: a pin's HiddenNetName / PinUniqueId keeps no Location
    return keep, moves, adds, tb, border


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sheet')
    ap.add_argument('--by', required=True, help='dx,dy in units of 10 mil, e.g. 24,178')
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    dx, dy = (round(float(v) * F) for v in a.by.split(','))

    recs = split(read_stream(a.sheet))
    P = [parse(b) for _, b in recs]
    for (h, b), (pairs, tail) in zip(recs, P):
        assert unparse(pairs, tail) == b, 'record does not round-trip: %r' % b[:60]
    assert dict(P[0][0]).get('HEADER') is not None and dict(P[1][0]).get('RECORD') == '31'
    keep, moves, adds, tb, border = plan(P, dx, dy)
    kinds = Counter(dict(P[i][0]).get('RECORD') for i in moves)
    print('move by %.5f, %.5f units (%.4f, %.4f mil)' % (dx / F, dy / F, dx / F * 10, dy / F * 10))
    print('title block %s, border %s (units)' % (tuple(v / F for v in tb), tuple(v / F for v in border)))
    print('kept in place: %d records (%s)' % (len(keep), dict(Counter(dict(P[i][0]).get('RECORD') for i in keep))))
    print('records to move: %d %s; origin parameters given a Location: %d' % (len(moves), dict(kinds), len(adds)))
    if not a.apply:
        print('(report only; add --apply to write)')
        return

    mset, aset = set(moves), set(adds)
    out = []
    for i, ((h, b), (pairs, tail)) in enumerate(zip(recs, P)):
        if i in mset:
            out.append([h, unparse(shift(pairs, dx, dy), tail)])
        elif i in aset:
            out.append([h, unparse(add_location(pairs, dx, dy), tail)])
        else:
            out.append([h, b])
    data = join(out)

    chk = split(data)
    assert len(chk) == len(recs)
    for i, ((h0, b0), (h1, b1)) in enumerate(zip(recs, chk)):
        p0, p1 = P[i][0], parse(b1)[0]
        if i in mset:
            q0, q1 = points(p0), points(p1)
            assert set(q0) == set(q1) and all((q1[k][0] - q0[k][0], q1[k][1] - q0[k][1]) == (dx, dy) for k in q0), i
        elif i in aset:
            assert points(p1) == {('Location.', ''): (dx, dy)}, i
        else:
            assert b0 == b1, 'untouched record %d changed' % i
            continue

        def strip(ps):
            return [kv for kv in ps if not (kv[0] and PAIR.match(kv[0][:-5] if kv[0].endswith('_Frac') else kv[0]))]
        assert strip(p0) == strip(p1), 'record %d: a non-coordinate field changed' % i

    shutil.copy2(a.sheet, a.sheet + '.pre-move')
    write_stream(a.sheet, data)
    print('wrote %s (backup %s.pre-move)' % (a.sheet, a.sheet))


if __name__ == '__main__':
    main()
