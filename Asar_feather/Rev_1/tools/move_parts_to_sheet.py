"""Move parts, with the wires and labels drawn around them, from one Altium schematic sheet to another.

Made 2026-11-07 for the user's request "move R26, R27, R28 to sheet 2 close to X1": the three USB-C resistors
(R26 VU->EN 100k, R27/R28 the CC1/CC2 5.1k pull-downs) were drawn on sheet 3 with their own net labels.

What moves: each named component with everything it owns, plus every sheet-level record lying entirely inside
--window on the source sheet (wires, net labels, power ports, junctions, no-ERC marks, texts). The tool refuses if
another component reaches into the window, or a sheet-level record is only partly inside it (a wire would be cut).
The records are deleted from the source (OwnerIndex renumbered, header Weight updated) and appended to the
destination with: coordinates shifted by --by (units of 10 mil), OwnerIndex remapped, every *FontID mapped to a
destination font with the same name/size/rotation (a missing font is added to the destination's font table), and
sheet-level IndexInSheet continued after the destination's highest. UniqueIDs are kept, so the PCB link
(SOURCEUNIQUEID = \\<component UID>) still holds; Altium's next ECO only moves the parts to the destination
sheet's component class.

    python tools/move_parts_to_sheet.py --src a.SchDoc --dst b.SchDoc --parts R26,R27,R28 \
        --window 200,440,340,490 --by 80,648 [--apply]

Close both sheets in Altium first. The project is flat and net labels / power ports are global, so the netlist does
not change; check with sch_netlist.py before and after.
"""
import argparse
import os
import re
import shutil
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schdoc import read_stream, split, join, write_stream, delete  # noqa: E402
from snap_sheet_move import F, parse, unparse, points, shift  # noqa: E402

FONT_KEYS = ('FontName', 'Size', 'Rotation', 'Bold', 'Italic', 'Underline', 'StrikeOut')


def fonts(pairs):
    d = dict(pairs)
    n = int(d['FontIdCount'])
    return {i: tuple(d.get('%s%d' % (k, i)) for k in FONT_KEYS) for i in range(1, n + 1)}


def subtree(P, roots):
    out = set(roots)
    grew = True
    while grew:
        grew = False
        for j in range(2, len(P)):
            o = dict(P[j][0]).get('OwnerIndex')
            if j not in out and o is not None and int(o) + 1 in out:
                out.add(j)
                grew = True
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True)
    ap.add_argument('--dst', required=True)
    ap.add_argument('--parts', required=True)
    ap.add_argument('--window', required=True, help='x0,y0,x1,y1 in units of 10 mil, on the source sheet')
    ap.add_argument('--by', required=True, help='dx,dy in units of 10 mil')
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    parts = a.parts.split(',')
    x0, y0, x1, y1 = (round(float(v) * F) for v in a.window.split(','))
    dx, dy = (round(float(v) * F) for v in a.by.split(','))

    srec, drec = split(read_stream(a.src)), split(read_stream(a.dst))
    S = [parse(b) for _, b in srec]
    Dd = [parse(b) for _, b in drec]
    for recs, P in ((srec, S), (drec, Dd)):
        for (h, b), (pairs, tail) in zip(recs, P):
            assert unparse(pairs, tail) == b, 'record does not round-trip: %r' % b[:60]

    # 1. the parts and the window contents on the source sheet
    comps = {}
    for j in range(2, len(S)):
        d = dict(S[j][0])
        if d.get('RECORD') == '34' and d.get('Text') in parts and 'OwnerIndex' in d:
            comps[d['Text']] = int(d['OwnerIndex']) + 1
    missing = [p for p in parts if p not in comps]
    if missing:
        sys.exit('Refusing: %s not found on %s' % (missing, a.src))
    inside = lambda p: x0 <= p[0] <= x1 and y0 <= p[1] <= y1  # noqa: E731
    roots = set(comps.values())
    for j in range(2, len(S)):
        d = dict(S[j][0])
        if 'OwnerIndex' in d or j in roots:
            continue
        pts = list(points(S[j][0]).values())
        if not pts:
            continue
        n_in = sum(1 for p in pts if inside(p))
        if d.get('RECORD') == '1' and n_in:
            sys.exit('Refusing: another component (record %d) sits inside the window' % j)
        if 0 < n_in < len(pts):
            sys.exit('Refusing: record %d (RECORD=%s) is only partly inside the window' % (j, d.get('RECORD')))
        if n_in == len(pts):
            roots.add(j)
    sel = sorted(subtree(S, roots))
    kinds = Counter(dict(S[j][0]).get('RECORD') for j in sel)
    print('moving %d records (%d sheet-level): %s' % (len(sel), len(roots), dict(kinds)))

    # 2. font mapping
    sf, df = fonts(S[1][0]), fonts(Dd[1][0])
    used = sorted({int(v) for j in sel for k, v in S[j][0] if k and k.endswith('FontID') and v})
    fmap, added = {}, []
    for f in used:
        hit = [g for g in sorted(df) if df[g] == sf[f]]
        if hit:
            fmap[f] = hit[0]
        else:
            g = max(df) + 1
            df[g] = sf[f]
            fmap[f] = g
            added.append(g)
    print('font map (source -> destination): %s; fonts added to the destination: %s' % (fmap, added))

    # 3. destination UIDs must stay unique
    duids = {dict(p).get('UniqueID') for p, _ in Dd} - {None}
    clash = [dict(S[j][0]).get('UniqueID') for j in sel if dict(S[j][0]).get('UniqueID') in duids]
    if clash:
        sys.exit('Refusing: UniqueID clash on the destination: %s' % clash)

    # 4. build the appended records
    base = len(drec)
    newidx = {j: base + k for k, j in enumerate(sel)}
    nxt = max(int(dict(p).get('IndexInSheet', 0)) for p, _ in Dd[2:] if 'OwnerIndex' not in dict(p)) + 1
    app = []
    for j in sel:
        pairs, tail = S[j]
        pairs = shift(pairs, dx, dy) if points(pairs) else [list(kv) for kv in pairs]
        out = []
        top_level = 'OwnerIndex' not in dict(pairs)
        for k, v in pairs:
            if k == 'OwnerIndex':
                o = int(v) + 1
                assert o in newidx, 'record %d belongs to an unselected owner %d' % (j, o)
                v = str(newidx[o] - 1)
            elif k and k.endswith('FontID') and v:
                v = str(fmap[int(v)])
            elif k == 'IndexInSheet' and top_level:
                v = str(nxt)
                nxt += 1
            out.append([k, v])
        app.append([srec[j][0], unparse(out, tail)])

    # 5. destination sheet record: new fonts after the last font field
    dpairs = [list(kv) for kv in Dd[1][0]]
    if added:
        last = max(i for i, (k, _) in enumerate(dpairs) if k and re.fullmatch(r'(%s)\d+' % '|'.join(FONT_KEYS), k))
        ins = []
        for g in added:
            for k, v in zip(FONT_KEYS, df[g]):
                if v is not None:
                    ins.append(['%s%d' % (k, g), v])
        dpairs = dpairs[:last + 1] + ins + dpairs[last + 1:]
        dpairs = [[k, str(len(df)) if k == 'FontIdCount' else v] for k, v in dpairs]
    dnew = [list(r) for r in drec]
    dnew[1] = [drec[1][0], unparse(dpairs, Dd[1][1])]
    dnew += app
    hp, ht = parse(dnew[0][1])
    dnew[0] = [dnew[0][0], unparse([[k, str(len(dnew) - 1) if k == 'Weight' else v] for k, v in hp], ht)]
    snew = delete([list(r) for r in srec], sel)

    # 6. checks
    sd, dd = join(snew), join(dnew)
    S2, D2 = [parse(b) for _, b in split(sd)], [parse(b) for _, b in split(dd)]
    assert len(S2) == len(S) - len(sel) and len(D2) == len(Dd) + len(sel)
    assert int(dict(S2[0][0])['Weight']) == len(S2) - 1 and int(dict(D2[0][0])['Weight']) == len(D2) - 1
    for k, j in enumerate(sel):
        p0, p1 = S[j][0], D2[base + k][0]
        q0, q1 = points(p0), points(p1)
        assert set(q0) == set(q1) and all((q1[t][0] - q0[t][0], q1[t][1] - q0[t][1]) == (dx, dy) for t in q0)
        f0 = [fonts(S[1][0])[int(v)] for kk, v in p0 if kk and kk.endswith('FontID') and v]
        f1 = [fonts(D2[1][0])[int(v)] for kk, v in p1 if kk and kk.endswith('FontID') and v]
        assert f0 == f1, 'font changed in record %d' % j
        o0, o1 = dict(p0).get('OwnerIndex'), dict(p1).get('OwnerIndex')
        if o0 is not None:
            assert int(o1) + 1 == newidx[int(o0) + 1]
    for i in range(2, len(Dd)):
        assert D2[i] == Dd[i], 'destination record %d changed' % i
    left = [dict(p).get('Text') for p, _ in S2 if dict(p).get('RECORD') == '34' and dict(p).get('Text') in parts]
    assert not left
    print('checks passed: %d records moved; source %d -> %d records, destination %d -> %d'
          % (len(sel), len(S), len(S2), len(Dd), len(D2)))
    if not a.apply:
        print('(report only; add --apply to write)')
        return
    for path, data in ((a.src, sd), (a.dst, dd)):
        shutil.copy2(path, path + '.pre-partmove')
        write_stream(path, data)
        print('wrote %s (backup %s.pre-partmove)' % (path, path))


if __name__ == '__main__':
    main()
