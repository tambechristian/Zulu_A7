# -*- coding: utf-8 -*-
"""Sheet 5, 2026-09-09: the right-hand blocks are pulled back inside the drawing frame.

THE DEFECT. The inner border of sheet 5 is the line at x=1020 (RECORD=6 from y 92 to 1302). Text
belonging to the five right-hand blocks was drawn straight through it and off the printed page:

    MGTREFCLK0P/0N, MGTREFCLK1P/1N   ran to x 1054.6   -- 34.6 past the border
    UART_CTS / UART_RTS / UART_DTR   ran to x 1051.7   -- 31.7 past
    UART_TXD / UART_RXD              ran to x 1041.7   -- 21.7 past
    MGTPTXP0/N0/P1, MGTPTXN1         ran to x 1041.7   -- 21.7 past
    IO_A14/A15/A16/B15/C15/W19       ran to x 1033.2   -- 13.2 past
    IO_N2 / IO_W7                    ran to x 1028.9   --  8.9 past
    GNDADC x4                        ran to x 1022.5   --  2.5 past

25 objects in all. 21 of them are the gate pin names -- RECORD=41 parameters named GATE, owned by
the U1 placement and drawn just right of the pin, which is where this symbol puts its pin names on
every block of the sheet. The other four are the GNDADC net labels of the unconnected XADC balls,
which sit at the far end of their own wire. Measured two ways and they agree: from the exported PDF
(31 crossing spans, of which 6 are the invisible PIU10xx netlist overlay) and from the records
themselves, using Courier advance = 0.535 * FontSize schematic units, a constant calibrated against
the PDF and accurate to 0.3 units over an 11-character string.

WHY IT CANNOT BE FIXED IN PLACE. A row of these blocks is caption + net label + wire + pin + pin
name, and the widest of them is 165 units end to end with the border 165 units away -- it fits, but
only if the whole row moves left. Two of the five blocks had nowhere to go: the SDRAM block's pin
names end at x 830.3 and the Pmod captions begin at 843.6, leaving 8.3 units of slack where 18.2
were needed, and 11.5 where the GTP block needed 39.6. So the SDRAM block moves too. It had 71.8
units of clear space to ITS left -- it is simply sitting further right than it needs to.

THE FIX. Six blocks translate 40 units left, rigidly. Nothing is resized, reordered, shortened or
re-anchored, and no record is added or removed, so the netlist cannot change; the connectivity
signature is computed before and after and compared, and the 40-unit shift is a whole number of
units so no _Frac field has to move.

    block            placements  free objects   after the move
    SDRAM                39      40 captions, 39 labels, 39 wires
    Pmod JA               8       9 texts, 8 labels, 8 wires      right edge 1033.2 -> 993.2
    GTP float             8       9 texts, 8 no-ERC crosses       right edge 1054.6 -> 1014.6
    Unconnected balls     6      10 texts, 6 labels, 6 wires      right edge 1022.5 ->  982.5
    FT2232H handshake     3       5 texts, 3 labels, 3 wires      right edge 1051.7 -> 1011.7
    FT2232H UART          2       2 captions, 2 labels, 2 wires   right edge 1041.7 -> 1001.7

A block owns a record if the record's owner chain reaches one of its placements -- that takes the
pins, the arrowheads, the pin-name parameters and the whole dead-gate set, which must travel with
the placement or the file stops agreeing with itself. Free-standing records (captions, block
titles, net labels, wires, no-ERC crosses) are claimed by an x/y window, and the window is bounded
on the right as well as the left, because the SDRAM window would otherwise swallow the right-hand
blocks' captions. The XADC and JTAG blocks are left where they are: neither crosses the border.

Refuses to run twice.

    python tools/sheet5_right_margin.py tools "Imported zulu_a7.PrjPcb/zulu_a7_5.SchDoc"
"""
import sys, os, re, collections
sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 and os.path.isdir(sys.argv[1])
                else os.path.dirname(os.path.abspath(__file__)))
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

DX = -40
BORDER = 1020.0
ADV, HGT = 0.535, 0.87              # Courier New, calibrated against the exported PDF

BLOCKS = [
    dict(name='SDRAM',             px=765, ylo=312, yhi=692, xl=595, xr=840,  wylo=303, wyhi=702,
         want=(39, 118)),
    dict(name='Pmod JA',           px=985, ylo=337, yhi=407, xl=840, xr=1100, wylo=330, wyhi=419,
         want=(8, 25)),
    dict(name='GTP float',         px=985, ylo=427, yhi=497, xl=840, xr=1100, wylo=420, wyhi=513,
         want=(8, 17)),
    dict(name='Unconnected balls', px=975, ylo=537, yhi=597, xl=845, xr=1100, wylo=516, wyhi=624,
         want=(6, 22)),
    dict(name='FT2232H handshake', px=995, ylo=747, yhi=767, xl=790, xr=1100, wylo=726, wyhi=783,
         want=(3, 11)),
    dict(name='FT2232H UART',      px=985, ylo=792, yhi=802, xl=790, xr=1100, wylo=784, wyhi=812,
         want=(2, 6)),
]

XKEYS = ['Location.X', 'Corner.X'] + [f'X{k}' for k in range(1, 9)]


def num(b, k):
    v = field(b, k)
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def fnum(b, k):
    n = num(b, k)
    if n is None:
        return None
    f = field(b, k + '_Frac')
    return n + int(f) / 100000.0 if f else float(n)


def oi(b):
    o = field(b, 'OwnerIndex')
    return int(o) + 1 if o is not None else None


def rectype(b):
    m = re.match(rb'\|RECORD=(\d+)\|', b)
    return int(m.group(1)) if m else None


def points(b):
    """every (x, y) the record carries, as exact integers."""
    out = []
    n = num(b, 'LocationCount')
    if n:
        out += [(num(b, f'X{k}'), num(b, f'Y{k}')) for k in range(1, n + 1)]
    for a, c in (('Location.X', 'Location.Y'), ('Corner.X', 'Corner.Y')):
        if num(b, a) is not None:
            out.append((num(b, a), num(b, c)))
    return [p for p in out if p[0] is not None and p[1] is not None]


def fonts_of(recs):
    hdr = next(b for h, b in recs if b.startswith(b'|RECORD=31|'))
    return {k: (int(field(hdr, f'Size{k}')), int(field(hdr, f'Rotation{k}') or 0))
            for k in range(1, int(field(hdr, 'FontIdCount')) + 1)}


def roots(recs):
    """record index -> the RECORD=1 placement at the top of its owner chain, or None."""
    place = {i for i, (h, b) in enumerate(recs) if b.startswith(b'|RECORD=1|')}
    out = {}
    for i, (h, b) in enumerate(recs):
        p, n = oi(b), 0
        while p is not None and p not in place and n < 6:
            p = oi(recs[p][1])
            n += 1
        out[i] = p if p in place else None
    return out, place


def live(recs, place):
    """index -> is this record drawn?  A multi-gate placement carries every gate's children."""
    cur = {i: field(recs[i][1], 'CurrentPartId') for i in place}
    root, _ = roots(recs)
    ok = {}
    for i, (h, b) in enumerate(recs):
        good = field(b, 'IsHidden') != 'T'
        r = root[i]
        if r is not None:
            j, n = i, 0
            while j is not None and n < 6:
                opi = field(recs[j][1], 'OwnerPartId')
                if opi is not None and opi not in ('-1', cur[r]):
                    good = False
                j = oi(recs[j][1])
                n += 1
        ok[i] = good
    return ok


def text_box(b, fonts):
    """schematic-space box of a drawn text record, or None."""
    t = field(b, 'Text') or ''
    x, y = fnum(b, 'Location.X'), fnum(b, 'Location.Y')
    if not t or x is None or y is None:
        return None
    size, rot = fonts.get(num(b, 'FontID') or 4, (8, 0))
    w, ht = len(t) * ADV * size, HGT * size
    j = num(b, 'Justification') or 0
    hj, vj = j % 3, j // 3
    if rot in (90, 270):
        y0 = y - (0, w / 2, w)[hj] if rot == 90 else y - (w, w / 2, 0)[hj]
        x0 = x - (0, ht / 2, ht)[vj]
        return x0, y0, x0 + ht, y0 + w
    x0, y0 = x - (0, w / 2, w)[hj], y - (0, ht / 2, ht)[vj]
    return x0, y0, x0 + w, y0 + ht


def drawn_boxes(recs, fonts):
    root, place = roots(recs)
    ok = live(recs, place)
    out = []
    for i, (h, b) in enumerate(recs):
        r = rectype(b)
        if r is None or not ok[i]:
            continue
        if r in (4, 25, 34, 41, 17):
            bx = text_box(b, fonts)
            if bx:
                out.append((i, r, bx, field(b, 'Text')))
        elif r in (6, 7, 12, 27, 22, 29):
            P = points(b)
            if P:
                out.append((i, r, (min(p[0] for p in P), min(p[1] for p in P),
                                   max(p[0] for p in P), max(p[1] for p in P)), ''))
        elif r == 2:
            x, y = num(b, 'Location.X'), num(b, 'Location.Y')
            if x is None:
                continue
            L = num(b, 'PinLength') or 0
            dx, dy = ((1, 0), (0, 1), (-1, 0), (0, -1))[(num(b, 'PinConglomerate') or 0) & 3]
            out.append((i, r, (min(x, x + dx * L), min(y, y + dy * L),
                               max(x, x + dx * L), max(y, y + dy * L)), ''))
    return out


def signature(recs):
    """A netlist of sheet 5 built from the drawing: which pins and labels share a node.

    Union-find over wire endpoints, wire interiors, pin electrical ends, junctions and ports. The
    six blocks translate rigidly, so this has to come out identical afterwards."""
    root, place = roots(recs)
    ok = live(recs, place)
    desig = {oi(b): field(b, 'Text') for h, b in recs if b.startswith(b'|RECORD=34|')}
    parent = {}

    def find(a):
        parent.setdefault(a, a)
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b_):
        ra, rb = find(a), find(b_)
        if ra != rb:
            parent[ra] = rb

    segs = []
    for i, (h, b) in enumerate(recs):
        if rectype(b) == 27 and ok[i]:
            P = points(b)
            for a, c in zip(P, P[1:]):
                union(a, c)
                segs.append((a, c))
    attach = []
    for i, (h, b) in enumerate(recs):
        r = rectype(b)
        if not ok[i]:
            continue
        if r == 2 and root[i] is not None:
            x, y = num(b, 'Location.X'), num(b, 'Location.Y')
            if x is None:
                continue
            L = num(b, 'PinLength') or 0
            dx, dy = ((1, 0), (0, 1), (-1, 0), (0, -1))[(num(b, 'PinConglomerate') or 0) & 3]
            attach.append(((x + dx * L, y + dy * L),
                           f'{desig.get(root[i], "?")}-{field(b, "Designator")}'))
        elif r in (25, 17):
            x, y = num(b, 'Location.X'), num(b, 'Location.Y')
            if x is not None:
                attach.append(((x, y), f'<{field(b, "Text")}>'))
    for pt, _ in attach:                       # a point lying anywhere on a wire joins that wire
        for a, c in segs:
            if a[0] == c[0] == pt[0] and min(a[1], c[1]) <= pt[1] <= max(a[1], c[1]):
                union(pt, a)
            elif a[1] == c[1] == pt[1] and min(a[0], c[0]) <= pt[0] <= max(a[0], c[0]):
                union(pt, a)
    nodes = collections.defaultdict(list)
    for pt, name in attach:
        nodes[find(pt)].append(name)
    return sorted(tuple(sorted(v)) for v in nodes.values() if len(v) > 1)


def translate(b, dx):
    for k in XKEYS:
        v = num(b, k)
        if v is not None:
            b = set_field(b, k, str(v + dx))
    return b


def select(recs):
    root, place = roots(recs)
    picked, per = {}, []
    for B in BLOCKS:
        mine = {i for i in place
                if num(recs[i][1], 'Location.X') == B['px']
                and B['ylo'] <= num(recs[i][1], 'Location.Y') <= B['yhi']}
        owned = [i for i in range(len(recs)) if root[i] in mine]
        free = []
        for i, (h, b) in enumerate(recs):
            if root[i] is not None or i in place:
                continue
            P = points(b)
            if P and all(B['xl'] <= x <= B['xr'] and B['wylo'] <= y <= B['wyhi'] for x, y in P):
                free.append(i)
        got = (len(mine), len(free))
        assert got == B['want'], f"{B['name']}: found {got} placements/free, expected {B['want']}"
        for i in owned + free:
            assert i not in picked, f'record {i} claimed by both {picked[i]} and {B["name"]}'
            picked[i] = B['name']
        per.append((B['name'], len(mine), len(owned), len(free)))
    return picked, per


def main(path):
    recs = split(read_stream(path, 'FileHeader'))
    N = len(recs)
    assert int(field(recs[0][1], 'Weight')) == N - 1, 'header count is already wrong'
    fonts = fonts_of(recs)
    before = [e for e in drawn_boxes(recs, fonts) if e[2][2] > BORDER + 0.05]
    if not before:
        raise SystemExit('nothing on sheet 5 crosses the drawing border; nothing done')
    print(f'{len(before)} drawn objects cross x={BORDER:.0f}, the worst by '
          f'{max(e[2][2] for e in before) - BORDER:.1f} units')

    sig = signature(recs)
    picked, per = select(recs)
    for name, p, o, f in per:
        print(f'   {name:18} {p:3} placements  {o:6} owned  {f:4} free')
    for i in picked:
        recs[i][1] = translate(recs[i][1], DX)

    assert len(recs) == N
    blob = join(recs)
    write_stream(path, 'FileHeader', blob)
    assert read_stream(path, 'FileHeader') == blob
    print(f'sheet 5: {len(picked)} records moved {abs(DX)} units left, {N} records unchanged in count')
    verify(path, sig)


def verify(path, sig_before):
    recs = split(read_stream(path, 'FileHeader'))
    assert int(field(recs[0][1], 'Weight')) == len(recs) - 1, 'header count'
    assert all(b.endswith(b'\x00') for h, b in recs), 'a record lost its terminator'
    uids = [field(b, 'UniqueID') for h, b in recs if field(b, 'UniqueID')]
    assert len(uids) == len(set(uids)), 'duplicate UniqueID'
    fonts = fonts_of(recs)
    boxes = drawn_boxes(recs, fonts)
    over = [e for e in boxes if e[2][2] > BORDER + 0.05]
    assert not over, f'{len(over)} objects still cross the border: ' \
                     f'{[(e[3], round(e[2][2], 1)) for e in over[:5]]}'
    frame = [e for e in boxes if e[1] == 6 and e[2][0] == e[2][2] == BORDER]
    assert frame, 'the border line at x=1020 has gone'
    right = max(e[2][2] for e in boxes if e[2][2] <= BORDER + 0.05)
    left = min(e[2][0] for e in boxes)
    assert left > 0, f'something has been pushed off the left edge (x={left:.1f})'
    sig_after = signature(recs)
    assert sig_after == sig_before, (
        f'the drawing connectivity changed: {len(sig_before)} nodes -> {len(sig_after)}')
    print(f'verify: {len(boxes)} drawn objects, none past x={BORDER:.0f} (widest now {right:.1f}), '
          f'leftmost {left:.1f}; all {len(sig_after)} drawn nodes unchanged')


if __name__ == '__main__':
    main(sys.argv[2])
