"""Move everything on a KiCad schematic sheet except its drawing frame by a fixed vector (KiCad copy of
Asar_feather/tools/move_sheet_circuit.py, 2026-11-07).

Zulu A7 sheet 7 (zulu_a7_6.kicad_sch) gets the layout the user gave Asar A7 sheet 7 in Altium: the FPGA-power circuit
moved by (24, 178) Altium units of 10 mil, i.e. +6.096 mm in x and -45.212 mm in y (KiCad's y axis points down; the
copy keeps x = 0.254 X, y = 313.182 - 0.254 Y against the Altium sheets).

Stays in place: the frame symbol (Reference FRAME*), the polylines on the frame border (edges of the bounding box of
all top-level polylines), and every item that lies inside the title block (the frame symbol's drawn area plus its
property positions). Everything else moves: every (at x y ...), (xy x y), (start x y), (end x y), (mid x y) and
(center x y) inside each other top-level item (wires, junctions, symbols with their property positions, labels,
texts, text boxes). Pin positions are relative to their symbol and need no change.

    python tools/move_sheet_circuit_kicad.py <sheet.kicad_sch> --by 6.096,-45.212 [--apply]

Without --apply it only reports. Close the sheet in KiCad first.
"""
import argparse
import re
import shutil
import sys
from decimal import Decimal

COORD = re.compile(r'\((at|xy|start|end|mid|center) (-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?)')


def end_of(s, j):
    """Index of the ')' closing the '(' at s[j]; skips quoted strings (with backslash escapes)."""
    d = 0
    while True:
        c = s[j]
        if c == '"':
            j += 1
            while s[j] != '"':
                if s[j] == '\\':
                    j += 1
                j += 1
        elif c == '(':
            d += 1
        elif c == ')':
            d -= 1
            if d == 0:
                return j
        j += 1


def items(t):
    """Top-level items after lib_symbols as (start, end, kind, text)."""
    j = end_of(t, t.index('(lib_symbols')) + 1
    out = []
    while True:
        k = t.find('\n\t(', j)
        if k < 0:
            break
        e = end_of(t, k + 2)
        body = t[k + 2:e + 1]
        out.append((k + 2, e + 1, re.match(r'\((\w+)', body).group(1), body))
        j = e + 1
    return out


def coords(body):
    """(x, y) of every coordinate token, skipping those inside quoted strings."""
    out = []
    for m in COORD.finditer(body):
        if body.count('"', 0, m.start()) % 2 == 0:
            out.append((Decimal(m.group(2)), Decimal(m.group(3))))
    return out


def fmt(v):
    s = format(v.normalize(), 'f')
    if '.' in s:
        s = s.rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


def shift(body, dx, dy):
    def rep(m):
        if body.count('"', 0, m.start()) % 2:
            return m.group(0)
        return '(%s %s %s' % (m.group(1), fmt(Decimal(m.group(2)) + dx), fmt(Decimal(m.group(3)) + dy))
    return COORD.sub(rep, body)


def frame_box(t, frame_body):
    """Title-block box: the frame symbol's library graphics placed at its (at x y rot), plus its property positions."""
    lib = re.search(r'\(lib_id "([^"]+)"\)', frame_body).group(1)
    i = t.index('\n\t\t(symbol "%s"' % lib)
    seg = t[i:end_of(t, i + 3) + 1]
    m = re.search(r'\n\t\t\(at (-?[\d.]+) (-?[\d.]+) (\d+)\)', frame_body)
    ax, ay, rot = Decimal(m.group(1)), Decimal(m.group(2)), int(m.group(3))
    if '(mirror' in frame_body:
        raise SystemExit('Refusing: mirrored frame symbol')
    place = {0: lambda x, y: (ax + x, ay - y), 90: lambda x, y: (ax - y, ay - x),
             180: lambda x, y: (ax - x, ay + y), 270: lambda x, y: (ax + y, ay + x)}[rot]
    pts = [place(x, y) for x, y in coords(seg) if True]
    pts += coords(frame_body)
    return (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sheet')
    ap.add_argument('--by', required=True, help='dx,dy in mm, e.g. 6.096,-45.212')
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    dx, dy = (Decimal(v) for v in a.by.split(','))
    t = open(a.sheet, encoding='utf-8', newline='').read()
    its = items(t)
    frames = [it for it in its if it[2] == 'symbol' and re.search(r'\(property "Reference" "FRAME', it[3])]
    if len(frames) != 1:
        raise SystemExit('Refusing: expected one FRAME symbol, found %d' % len(frames))
    tb = frame_box(t, frames[0][3])
    poly = [p for it in its if it[2] == 'polyline' for p in coords(it[3])]
    bx0, by0 = min(p[0] for p in poly), min(p[1] for p in poly)
    bx1, by1 = max(p[0] for p in poly), max(p[1] for p in poly)

    def on_border(x, y):
        return (x in (bx0, bx1) and by0 <= y <= by1) or (y in (by0, by1) and bx0 <= x <= bx1)

    def in_tb(x, y):
        return tb[0] <= x <= tb[2] and tb[1] <= y <= tb[3]
    keep, move = [], []
    for it in its:
        pts = coords(it[3])
        if it is frames[0] or (it[2] == 'polyline' and all(on_border(*p) for p in pts)) or \
                (pts and all(in_tb(*p) for p in pts)):
            keep.append(it)
        else:
            move.append(it)
    from collections import Counter
    print('move by %s, %s mm; title block %s; border %s' % (dx, dy, tuple(map(str, tb)), (str(bx0), str(by0), str(bx1), str(by1))))
    print('kept: %s' % [(it[2], re.findall(r'"([^"]*)"', it[3])[:2]) for it in keep])
    print('moving: %s' % dict(Counter(it[2] for it in move)))
    if not a.apply:
        print('(report only; add --apply to write)')
        return
    out, last = [], 0
    for s, e, kind, body in its:
        out.append(t[last:s])
        out.append(shift(body, dx, dy) if any(it[0] == s for it in move) else body)
        last = e
    out.append(t[last:])
    new = ''.join(out)
    # Check: the same items, kept ones byte-identical, moved ones differ only in coordinates, each by exactly (dx, dy).
    nits = items(new)
    assert [(it[2]) for it in nits] == [(it[2]) for it in its]
    mv = {it[0] for it in move}
    for o, n in zip(its, nits):
        if o[0] not in mv:
            assert o[3] == n[3]
            continue
        assert COORD.sub('C', o[3]) == COORD.sub('C', n[3]), 'non-coordinate text changed'
        co, cn = coords(o[3]), coords(n[3])
        assert len(co) == len(cn) and all(q[0] - p[0] == dx and q[1] - p[1] == dy for p, q in zip(co, cn))
    assert new[:its[0][0]] == t[:its[0][0]]
    shutil.copy2(a.sheet, a.sheet + '.pre-move')
    open(a.sheet, 'w', encoding='utf-8', newline='').write(new)
    print('wrote %s (backup %s.pre-move)' % (a.sheet, a.sheet))


if __name__ == '__main__':
    main()
