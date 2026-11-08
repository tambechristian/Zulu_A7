"""Put a hand-dragged circuit back on the grid: finish the move by a whole number of grid steps.

A drag in the schematic editor moves the selection by the offset of the grabbed point, which need not be a whole
grid step. Sheet 7 (asar_a7_6.SchDoc) was moved up on 2026-11-07 by (240.2369, 1779.0522) mil, so none of its 804
pins stayed on the grid. This compares the sheet with a reference copy (the committed version), finds the drag vector,
rounds it to the nearest multiple of --grid, and adds the difference to every coordinate of every record the drag
moved. Coordinates are Location, Corner, X1..Xn / Y1..Yn and the extra wire vertices EXn / EYn, each with its _Frac
part (1e-5 of a unit; 1 unit = 10 mil).

Which records moved: a sheet-level record moved if its coordinates differ from the reference record with the same
UniqueID, or if the reference has no record with that UniqueID; a child record (OwnerIndex) moves with its top-level
owner. Records the drag left alone (here the drawing frame and the title-block text) stay byte-identical.
Refuses unless every moved sheet-level record that has a reference twin moved by the same vector, rigidly.

    python tools/snap_sheet_move.py <sheet> --ref <reference sheet> [--grid 1] [--apply]

Without --apply it only reports. With --apply the sheet is backed up to <sheet>.pre-snap first. Close the sheet in
Altium before applying, and reopen it afterwards.
"""
import argparse
import re
import shutil
import sys
from collections import Counter
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schdoc import read_stream, split, join, write_stream  # noqa: E402

F = 100000                                   # _Frac denominator
PAIR = re.compile(r'(Location\.|Corner\.|E?)([XY])(\d*)$')


def parse(body):
    """Ordered [key, value] pairs of a record body, and the raw tail after the last field (normally NUL)."""
    t = body.decode('latin-1')
    end = t.find('\x00')
    tail = t[end:] if end >= 0 else ''
    core = t[:end] if end >= 0 else t
    assert core.startswith('|'), core[:40]
    pairs = []
    for kv in core[1:].split('|'):          # pin records hold raw '|' inside SwapIDPart, so keep empty / bare segments
        k, sep, v = kv.partition('=')
        pairs.append([k, v if sep else None])
    return pairs, tail


def unparse(pairs, tail):
    return ('|' + '|'.join(k if v is None else k + '=' + v for k, v in pairs) + tail).encode('latin-1')


def coord_keys(pairs):
    """Integer coordinate keys present, as (prefix, axis, index) -> key. Location.X etc.; X1/Y1; EX51/EY51."""
    out = {}
    for k, _ in pairs:
        if k.endswith('_Frac'):
            continue
        m = PAIR.match(k)
        if not m:
            continue
        pre, axis, idx = m.groups()
        if pre in ('Location.', 'Corner.') and idx:
            continue
        if pre in ('', 'E') and not idx:
            continue
        out[(pre, axis, idx)] = k
    return out


def value(d, key):
    return int(d.get(key, '0')) * F + int(d.get(key + '_Frac', '0'))


def points(pairs):
    """{(prefix, index): (x, y)} in 1e-5 units."""
    d = dict(pairs)
    keys = coord_keys(pairs)
    pts = {}
    for (pre, axis, idx) in keys:
        name = lambda a: (pre + a + idx)
        pts[(pre, idx)] = (value(d, name('X')), value(d, name('Y')))
    return pts


def shift(pairs, dx, dy):
    """Add (dx, dy) (1e-5 units) to every coordinate pair; keep field order, drop a _Frac that becomes 0."""
    d = dict(pairs)
    new = {}
    for (pre, idx), (x, y) in points(pairs).items():
        for axis, val in (('X', x + dx), ('Y', y + dy)):
            if val < 0:
                raise SystemExit('Refusing: a shifted coordinate would be negative (%s%s%s)' % (pre, axis, idx))
            new[pre + axis + idx] = (str(val // F), str(val % F))
    out = []
    done = set()
    for k, v in pairs:
        base = k[:-5] if k.endswith('_Frac') else k
        if base in new:
            if base in done:
                continue
            i, f = new[base]
            out.append([base, i])
            if f != '0':
                out.append([base + '_Frac', f])
            done.add(base)
        else:
            out.append([k, v])
    for base, (i, f) in new.items():          # a pair whose X or Y field was absent (value 0) gets written too
        if base not in done:
            out.append([base, i])
            if f != '0':
                out.append([base + '_Frac', f])
    return out


def top(parsed, i):
    """Index of the top-level (sheet-level) record that owns record i, following OwnerIndex."""
    seen = 0
    while True:
        o = dict(parsed[i][0]).get('OwnerIndex')
        if o is None:
            return i
        i = int(o) + 1
        seen += 1
        assert seen < 100, 'owner loop'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sheet')
    ap.add_argument('--ref', required=True, help='reference copy of the sheet from before the drag (e.g. git show HEAD:...)')
    ap.add_argument('--grid', type=float, default=1.0, help='grid step in units of 10 mil (default 1 = 10 mil)')
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()

    recs = split(read_stream(a.sheet))
    ref = split(read_stream(a.ref))
    P = [parse(b) for _, b in recs]
    R = [parse(b) for _, b in ref]
    for (h, b), (pairs, tail) in zip(recs, P):
        assert unparse(pairs, tail) == b, 'record does not round-trip: %r' % b[:60]
    assert dict(P[0][0]).get('HEADER') is not None and dict(P[1][0]).get('RECORD') == '31'

    ref_by_uid = {}
    for pairs, _ in R[2:]:
        d = dict(pairs)
        if 'UniqueID' in d and 'OwnerIndex' not in d:
            ref_by_uid[d['UniqueID']] = pairs
    vectors = Counter()
    moved_top = set()
    for i, (pairs, _) in enumerate(P[2:], 2):
        d = dict(pairs)
        if 'OwnerIndex' in d:
            continue
        pts = points(pairs)
        if not pts:
            continue
        rp = ref_by_uid.get(d.get('UniqueID'))
        if rp is None:
            moved_top.add(i)
            continue
        rpts = points(rp)
        if pts == rpts:
            continue
        moved_top.add(i)
        if set(pts) == set(rpts):
            vs = {(pts[k][0] - rpts[k][0], pts[k][1] - rpts[k][1]) for k in pts}
            if len(vs) == 1:
                vectors[vs.pop()] += 1
    if not vectors:
        sys.exit('Nothing moved relative to the reference.')
    (vx, vy), n = vectors.most_common(1)[0]
    print('drag vector %.5f, %.5f units (%d sheet-level records rigidly moved by it; other vectors: %s)'
          % (vx / F, vy / F, n, [((x / F, y / F), c) for (x, y), c in vectors.most_common()[1:4]]))
    g = round(a.grid * F)
    sx, sy = round(vx / g) * g, round(vy / g) * g
    dx, dy = sx - vx, sy - vy
    print('snapped vector %.5f, %.5f units -> correction dx %.5f, dy %.5f units (%.4f, %.4f mil)'
          % (sx / F, sy / F, dx / F, dy / F, dx / F * 10, dy / F * 10))
    if dx == 0 and dy == 0:
        sys.exit('Already on the grid: nothing to do.')

    # Every moved sheet-level record with a twin must have moved rigidly by (vx, vy), or be a wire reshaped by the
    # drag (merged with its neighbour): its vertices must then all be reference vertices + (vx, vy) of SOME wire.
    ref_wire_pts = set()
    for pairs, _ in R[2:]:
        if dict(pairs).get('RECORD') == '27':
            ref_wire_pts |= set(points(pairs).values())
    odd = []
    for i in moved_top:
        pairs = P[i][0]
        d = dict(pairs)
        rp = ref_by_uid.get(d.get('UniqueID'))
        pts = points(pairs)
        if rp is not None and set(pts) == set(points(rp)) and \
                all((pts[k][0] - points(rp)[k][0], pts[k][1] - points(rp)[k][1]) == (vx, vy) for k in pts):
            continue
        if d.get('RECORD') == '27' and all((x - vx, y - vy) in ref_wire_pts for x, y in pts.values()):
            continue
        odd.append((i, d.get('RECORD'), d.get('UniqueID')))
    if odd:
        sys.exit('Refusing: %d moved records are not a rigid copy of the reference: %s' % (len(odd), odd[:10]))

    targets = [i for i in range(2, len(P)) if points(P[i][0]) and top(P, i) in moved_top]
    kinds = Counter(dict(P[i][0]).get('RECORD') for i in targets)
    kept = [i for i in range(2, len(P)) if points(P[i][0]) and i not in targets]
    print('records to shift: %d %s; records with coordinates left in place: %d'
          % (len(targets), dict(kinds), len(kept)))
    if not a.apply:
        print('(report only; add --apply to write)')
        return

    out = []
    tset = set(targets)
    for i, ((h, b), (pairs, tail)) in enumerate(zip(recs, P)):
        if i in tset:
            out.append([h, unparse(shift(pairs, dx, dy), tail)])
        else:
            out.append([h, b])
    data = join(out)

    # Check: re-parse; untouched records byte-identical; shifted ones moved by exactly (dx, dy), nothing else changed.
    chk = split(data)
    assert len(chk) == len(recs)
    for i, ((h0, b0), (h1, b1)) in enumerate(zip(recs, chk)):
        if i not in tset:
            assert b0 == b1, 'untouched record %d changed' % i
            continue
        p0, p1 = P[i][0], parse(b1)[0]
        q0, q1 = points(p0), points(p1)
        assert set(q0) == set(q1)
        for k in q0:
            assert (q1[k][0] - q0[k][0], q1[k][1] - q0[k][1]) == (dx, dy), (i, k)
        strip = lambda ps: [kv for kv in ps if not (PAIR.match(kv[0][:-5] if kv[0].endswith('_Frac') else kv[0]))
                            or kv[0] in ('LocationCount', 'EXTRALOCATIONCOUNT')]
        assert strip(p0) == strip(p1), 'record %d: a non-coordinate field changed' % i

    shutil.copy2(a.sheet, a.sheet + '.pre-snap')
    write_stream(a.sheet, data)
    print('wrote %s (backup %s.pre-snap)' % (a.sheet, a.sheet))


if __name__ == '__main__':
    main()
