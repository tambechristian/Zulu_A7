# -*- coding: utf-8 -*-
"""Text drawn on top of other text is pulled apart, measured on the exported PDF.

WHY THE PDF. A schematic record does not know how wide it renders, and two of the things that
collide here -- pin names and pin numbers -- are not records at all: they are drawn by the pin from
its own conglomerate fields, and no amount of reading `Text=` finds them. The exported PDF has every
glyph box that actually appears, so that is where the geometry comes from. Each span is mapped back
to schematic units with the sheet's own transform and then matched to the record that drew it.

WHAT COUNTS. Altium writes three layers of invisible metadata into the PDF -- `COxxx` per component,
`PIxxx` per pin, `NLxxx` per net -- sitting exactly on the visible text they describe. Counting those
gives 12409 "overlaps" across the seven sheets, which is noise. Filtered out, and ignoring a
parameter drawn twice at one spot (the title block does that, and it renders as one), 40 real
collisions are left on five sheets; sheets 0 and 6 are clean.

MATCHING A SPAN TO ITS RECORD is done by predicting where the anchor of a box must be. Justification
is a 3x3 grid, so a horizontal bottom-left label anchors at the box's bottom left, a right-justified
one at its bottom right, and a rotated one swaps the roles of the two axes. Predicting the anchor and
taking the nearest record separates labels only 10 units apart, which a plain "is the anchor inside
the box" test does not: the four GNDADC labels on sheet 5 each matched two records that way.

TWO KINDS OF FIX.

  1. A REDUNDANT LABEL IS DELETED. Sheet 4 carries two `FT-RESETN` labels on one wire, at 302 left
     justified and 343 right justified, so both sets of glyphs land on x 300..345 -- one drawn on top
     of the other. `FT-REF` is the same, at 332 and 347 on the wire right of R18. The net keeps its
     name from the survivor. Only a pair that is identical in text, on one wire, AND actually
     overlapping is treated this way: several nets legitimately carry more than one label, such as
     the nine GND labels spread along the bus at y 557, and those are left alone.

  2. EVERYTHING ELSE IS NUDGED. One of the two moves, the other stays, in this order of preference:
     net label, then comment, then designator, then free text, and a power port only as a last
     resort. A PIN never moves at all -- its name and number belong to the symbol and its hot point
     is the connection. A port MAY slide, but under a label's rules and no others: its Location IS
     its electrical point, so it has to stay on the same wire run, which is what tools/snap_ports.py
     had to be written to repair once already.

     Candidates are searched and tested, never assumed. A net label may only slide ALONG the wire it
     names, in 5-unit steps out to 60, and its anchor has to stay on that wire, because a label that
     misses its wire names nothing. A comment, designator or free text may go anywhere in a ring out
     to 26 units. The first candidate whose box hits nothing wins. Anything with no clean candidate
     keeps its position and is reported rather than shoved somewhere worse.

No wire, pin or port location is touched, so the netlist cannot move; the drawing's connectivity
signature is compared anyway, and the PDF is re-measured afterwards to prove the count fell.

    python tools/text_overlaps.py tools "Imported zulu_a7.PrjPcb"          # plan only
    python tools/text_overlaps.py tools "Imported zulu_a7.PrjPcb" --apply
"""
import sys, os, re
sys.path.insert(0, sys.argv[1])
import pymupdf
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field
from sheet5_right_margin import num, oi, rectype, points, roots, signature
from rail_ports import footprint as port_box, GROUNDS, PREFER, dirs_at

PDF = 'zulu_a7.pdf'
SHEETS = [f'zulu_a7_{k}' for k in range(7)]
HIDDEN = re.compile(r'^(PI|NL|CO)[A-Z0-9#\-\.\$_]*$')
TOL = 0.4
PRIORITY = {25: 0, 41: 1, 34: 2, 4: 3, 17: 4}          # 2 (pin) never moves; 17 is a last
SLIDERS = (25, 17)                                     # resort and may only slide on its wire
LABEL_STEPS = [d * s * 5 for d in range(1, 13) for s in (1, -1)]        # +-5 .. +-60 along the wire
RING = [(dx, dy) for r in (8, 16, 26) for dx, dy in
        ((0, r), (0, -r), (r, 0), (-r, 0), (r, r), (-r, r), (r, -r), (-r, -r))]


def sheet_dims(recs):
    hdr = next(b for h, b in recs if b.startswith(b'|RECORD=31|'))
    x, y = int(field(hdr, 'CustomX')), int(field(hdr, 'CustomY'))
    return (y, x) if field(hdr, 'WorkspaceOrientation') == '1' else (x, y)


def spans_of(page, W, H):
    sc = 602.2 / H
    x0 = (792 - W * sc) / 2
    out = []
    for blk in page.get_text('dict')['blocks']:
        for ln in blk.get('lines', []):
            for s in ln['spans']:
                t = s['text'].strip()
                if not t or HIDDEN.match(t):
                    continue
                X0, Y0, X1, Y1 = s['bbox']
                out.append([t, (X0 - x0) / sc, (607 - Y1) / sc, (X1 - x0) / sc, (607 - Y0) / sc])
    return out


def overlap(a, b):
    return (a[1] < b[3] - TOL and b[1] < a[3] - TOL
            and a[2] < b[4] - TOL and b[2] < a[4] - TOL)


def hits(span, others):
    """span and others are both [text, x0, y0, x1, y1]."""
    for s in others:
        if overlap(span, s):
            return s[0]
    return None


def pairs(spans):
    out = []
    order = sorted(range(len(spans)), key=lambda i: spans[i][1])
    for a in range(len(order)):
        i = order[a]
        for b in range(a + 1, len(order)):
            j = order[b]
            if spans[j][1] >= spans[i][3] - TOL:
                break
            if overlap(spans[i], spans[j]):
                if (spans[i][0] == spans[j][0] and abs(spans[i][1] - spans[j][1]) < 0.6
                        and abs(spans[i][2] - spans[j][2]) < 0.6):
                    continue                    # one parameter drawn twice: renders as one
                out.append((i, j))
    return out


def predicted(box, just, rot):
    """where a record with this justification must be anchored to render into this box."""
    _, x0, y0, x1, y1 = box
    h, v = (just or 0) % 3, (just or 0) // 3
    if rot in ('1', '3'):
        # rotated 90 degrees: justification's horizontal half runs along y, its vertical half
        # along x, and the vertical half runs the OPPOSITE way -- measured against C135's
        # rotated comment, whose anchor sits at its box's bottom RIGHT, not bottom left
        y = (y0, (y0 + y1) / 2, y1)[h] if rot == '1' else (y1, (y0 + y1) / 2, y0)[h]
        return (x1, (x0 + x1) / 2, x0)[v] if rot == '1' else (x0, (x0 + x1) / 2, x1)[v], y
    return (x0, (x0 + x1) / 2, x1)[h], (y0, (y0 + y1) / 2, y1)[v]


def movable(recs):
    root, place = roots(recs)
    cur = {i: field(recs[i][1], 'CurrentPartId') for i in place}
    out = {}
    for i, (h, b) in enumerate(recs):
        r = rectype(b)
        if r not in PRIORITY or field(b, 'IsHidden') == 'T':
            continue
        rt = root[i]
        if rt is not None and field(b, 'OwnerPartId') not in (None, '-1', cur.get(rt)):
            continue
        x, y = num(b, 'Location.X'), num(b, 'Location.Y')
        if x is None or not (field(b, 'Text') or ''):
            continue
        out[i] = (r, x, y)
    return out


def match(spans, recs, mov):
    """span index -> record index, by predicting each candidate's anchor from the box."""
    owner = {}
    for k, sp in enumerate(spans):
        best = []
        for i, (r, ax, ay) in mov.items():
            if (field(recs[i][1], 'Text') or '') != sp[0]:
                continue
            if r == 17:
                # a port's text is offset from its hot point by the symbol, so compare box
                # centres against the footprint rather than pretending the anchor is a corner
                t = sp[0]
                fx = port_box(ax, ay, int(field(recs[i][1], 'Orientation') or 0), t,
                              'gnd' if t in GROUNDS else 'sup')
                best.append((abs((fx[0] + fx[2]) / 2 - (sp[1] + sp[3]) / 2)
                             + abs((fx[1] + fx[3]) / 2 - (sp[2] + sp[4]) / 2), i))
                continue
            px, py = predicted(sp, num(recs[i][1], 'Justification'),
                               field(recs[i][1], 'Orientation'))
            best.append((abs(px - ax) + abs(py - ay), i))
        best.sort()
        lim = 16 if best and mov[best[0][1]][0] == 17 else 5
        if best and best[0][0] < lim and (len(best) == 1 or best[1][0] - best[0][0] >= 3):
            owner[k] = best[0][1]
    return owner


def segments(recs):
    segs = []
    for h, b in recs:
        if rectype(b) == 27:
            P = points(b)
            segs += list(zip(P, P[1:]))
    return segs


def on_wire(segs, x, y):
    for (ax, ay), (bx, by) in segs:
        if ax == bx == x and min(ay, by) <= y <= max(ay, by):
            return (0, 1)
        if ay == by == y and min(ax, bx) <= x <= max(ax, bx):
            return (1, 0)
    return None


def same_wire(segs, a, b):
    par = {}

    def find(p):
        par.setdefault(p, p)
        while par[p] != p:
            par[p] = par[par[p]]
            p = par[p]
        return p

    for s, e in segs:
        ra, rb = find(s), find(e)
        if ra != rb:
            par[ra] = rb

    def root_at(x, y):
        for (ax, ay), (bx, by) in segs:
            if ax == bx == x and min(ay, by) <= y <= max(ay, by):
                return find((ax, ay))
            if ay == by == y and min(ax, bx) <= x <= max(ax, bx):
                return find((ax, ay))
        return None

    ra, rb = root_at(*a), root_at(*b)
    return ra is not None and ra == rb


def plan_sheet(name, prj, page):
    path = os.path.join(prj, name + '.SchDoc')
    recs = split(read_stream(path, 'FileHeader'))
    W, H = sheet_dims(recs)
    spans = spans_of(page, W, H)
    bad = pairs(spans)
    if not bad:
        return recs, path, {}, {}, 0, [], {}
    mov = movable(recs)
    segs = segments(recs)
    owner = match(spans, recs, mov)

    # ---- pass 0: a label drawn on top of an identical label naming the same wire ---------------
    drop, dead = {}, set()
    for i, j in bad:
        if spans[i][0] != spans[j][0] or i in dead or j in dead:
            continue
        # two labels this close cannot be told apart by their anchors, so ask the records: are
        # there exactly two net labels of this text, on one wire, whose boxes are these two?
        lo = min(spans[i][1], spans[j][1]) - 4
        hi = max(spans[i][3], spans[j][3]) + 4
        cand = [r for r, (t, x, y) in mov.items()
                if t == 25 and (field(recs[r][1], 'Text') or '') == spans[i][0]
                and lo <= x <= hi and spans[i][2] - 4 <= y <= spans[i][4] + 4]
        if len(cand) != 2 or not same_wire(segs, mov[cand[0]][1:], mov[cand[1]][1:]):
            continue
        # keep the left/bottom-justified one, which is how this project writes labels
        go = max(cand, key=lambda r: (num(recs[r][1], 'Justification') or 0) % 3)
        drop[go] = spans[i][0]
        dead.add(j if spans[j][1] > spans[i][1] else i)

    # ---- pass 1: nudge whatever still collides -------------------------------------------------
    live = [s for k, s in enumerate(spans) if k not in dead]
    moves = {}
    for i, j in bad:
        if i in dead or j in dead:
            continue
        if not overlap(spans[i], spans[j]):
            continue                              # an earlier move already cleared this pair
        opts = [k for k in (i, j) if k in owner and owner[k] not in moves and owner[k] not in drop]
        opts.sort(key=lambda k: PRIORITY[mov[owner[k]][0]])
        for k in opts:
            rec = owner[k]
            r, ax, ay = mov[rec]
            others = [s for s in live if s is not spans[k]]
            if r in SLIDERS:
                d = on_wire(segs, ax, ay)
                if d is None:
                    continue
                # ...and only within the SAME connected run. on_wire alone is not enough: the
                # UART_FT_RXD label slid 30 up its stub, past R94, and landed on the VCC3V3 rail,
                # which named the rail UART_FT_RXD. The netlist check caught it; this stops it.
                cands = [(d[0] * s, d[1] * s) for s in LABEL_STEPS]
                cands = [c for c in cands if on_wire(segs, ax + c[0], ay + c[1])
                         and same_wire(segs, (ax, ay), (ax + c[0], ay + c[1]))]
            elif field(recs[rec][1], 'Name') == 'GATE':
                # a gate pin name stays on its own row and only moves AWAY from the pin: this
                # test sees text, not the pin line and its arrowhead, and left is where those are
                cands = [(d, 0) for d in (8, 16, 26, 36, 46)]
            else:
                cands = RING
            done = False
            for dx, dy in cands:
                nb = [spans[k][0], spans[k][1] + dx, spans[k][2] + dy,
                      spans[k][3] + dx, spans[k][4] + dy]
                if hits(nb, others) is None:
                    moves[rec] = (dx, dy)
                    spans[k][1:] = nb[1:]
                    done = True
                    break
            if done:
                break
    # a port that could not slide clear may simply be pointing the wrong way: rail_ports picks the
    # first free direction, and "free" was judged against the layout as it then stood
    turns = {}
    for i, j in bad:
        if i in dead or j in dead or not overlap(spans[i], spans[j]):
            continue
        for k in (i, j):
            rec = owner.get(k)
            if rec is None or rectype(recs[rec][1]) != 17 or rec in moves or rec in turns:
                continue
            b = recs[rec][1]
            t = field(b, 'Text')
            kind = 'gnd' if t in GROUNDS else 'sup'
            ax, ay = num(b, 'Location.X'), num(b, 'Location.Y')
            taken, _ = dirs_at(segs, ax, ay)
            others = [sp for sp in live if sp is not spans[k]]
            for o in PREFER[kind]:
                if o in taken or str(o) == field(b, 'Orientation'):
                    continue
                fx = port_box(ax, ay, o, t, kind)
                if hits([t, *fx], others) is None:
                    turns[rec] = o
                    spans[k][1:] = list(fx)
                    break
            if rec in turns:
                break
    stuck = [(spans[i][0], spans[j][0], round(spans[i][1], 1), round(spans[i][2], 1))
             for i, j in bad if i not in dead and j not in dead and overlap(spans[i], spans[j])]
    return recs, path, moves, drop, len(bad), stuck, turns


def main(prj, apply):
    doc = pymupdf.open(os.path.join(prj, PDF))
    total = nmoved = ndrop = 0
    for pg, name in enumerate(SHEETS):
        recs, path, moves, drop, nbad, stuck, turns = plan_sheet(name, prj, doc[pg])
        total += nbad
        nmoved += len(moves) + len(turns)
        ndrop += len(drop)
        if not nbad:
            print(f'{name}: clean')
            continue
        print(f'{name}: {nbad} overlaps -> {len(drop)} labels deleted, {len(moves)} moved, '
              f'{len(stuck)} unresolved')
        for rec, t in sorted(drop.items()):
            print(f'    delete R25 rec{rec:<7} {t!r} at '
                  f'({num(recs[rec][1], "Location.X")},{num(recs[rec][1], "Location.Y")})')
        for rec, (dx, dy) in sorted(moves.items()):
            b = recs[rec][1]
            print(f'    move   R{rectype(b)} rec{rec:<7} {field(b, "Text")[:22]!r:24} '
                  f'({num(b, "Location.X")},{num(b, "Location.Y")}) by ({dx:+},{dy:+})')
        for rec, o in sorted(turns.items()):
            print(f'    turn   R17 rec{rec:<7} {field(recs[rec][1], "Text")!r:24} '
                  f'Orientation {field(recs[rec][1], "Orientation")} -> {o}')
        for t1, t2, x, y in stuck:
            print(f'    left   {t1[:22]!r} x {t2[:22]!r} at ({x},{y})')
        if not apply or not (moves or drop or turns):
            continue
        sig = signature(recs)
        for rec, o in turns.items():
            recs[rec][1] = set_field(recs[rec][1], 'Orientation', str(o))
        for rec, (dx, dy) in moves.items():
            b = recs[rec][1]
            b = set_field(b, 'Location.X', str(num(b, 'Location.X') + dx))
            recs[rec][1] = set_field(b, 'Location.Y', str(num(b, 'Location.Y') + dy))
        if drop:
            keep = [i for i in range(len(recs)) if i not in drop]
            newpos = {old: new for new, old in enumerate(keep)}
            out = []
            for old in keep:
                b = recs[old][1]
                o = oi(b)
                if o is not None:
                    assert o in newpos, f'record {old} is owned by a deleted record'
                    b = set_field(b, 'OwnerIndex', str(newpos[o] - 1))
                out.append([recs[old][0], b])
            out[0][1] = set_field(out[0][1], 'Weight', str(len(out) - 1))
            recs = out
        blob = join(recs)
        write_stream(path, 'FileHeader', blob)
        assert read_stream(path, 'FileHeader') == blob
        back = split(read_stream(path, 'FileHeader'))
        assert int(field(back[0][1], 'Weight')) == len(back) - 1, 'header count'
        assert all(bb.endswith(b'\x00') for hh, bb in back), 'a record lost its terminator'
        for i, (hh, bb) in enumerate(back):
            o = oi(bb)
            assert o is None or 0 <= o < len(back), f'{name}: record {i} owns nothing'
        # deleting one of two identical labels drops a duplicate member from its node, which is
        # the point; collapsing duplicates makes that invisible while still catching a label that
        # has joined a different node
        def flat(g):
            return sorted(tuple(sorted(set(n))) for n in g)
        assert flat(signature(back)) == flat(sig), f'{name}: the drawing connectivity changed'
        print('    written, connectivity unchanged')
    print(f'\n{total} overlaps: {ndrop} redundant labels deleted, {nmoved} records moved')
    if not apply:
        print('(plan only -- pass --apply, then re-export the PDF and re-measure)')


if __name__ == '__main__':
    main(sys.argv[2], '--apply' in sys.argv)
