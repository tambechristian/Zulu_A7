# -*- coding: utf-8 -*-
"""Sheets 1, 3, 4, 5 and 6, 2026-09-09: rail names become power ports instead of bare text.

THE DEFECT (review finding 5). On five of the seven sheets a supply or ground connection is a plain
red net label sitting on a wire rather than a port symbol. The netlist is right either way -- a
label names a net perfectly well -- but the drawing stops being readable at a glance, and in three
places it reads as a different circuit from the one that was built:

  * Sheet 3 carries 24 rail labels and NOT ONE power port. Its seven-row U3 decoupling ladder renders
    as an unbroken line, `pin 54 -GND- ||C3|| -VCC3V3- pin 1`, seven times. Every row is correct --
    the cap bridges a ground ball to the supply ball opposite it -- but nothing on the row says which
    half is ground except two words of 8-point text.
  * Sheet 6's bulk column stacks three of these one under the other with 20 units between them, so
    the GND text of one stack is printed THROUGH the VCC1V8 or VCC3V3 label of the next. Measured on
    the PDF, `GND` occupies x 22..88 where `VCC1V8` occupies 65..145 on the same line.
  * Sheet 4's oscillator: the `VCC3V3` label that names C38's top plate is anchored 6 units right of
    Q1's pin-2 ground drop and right-justified, so its glyphs are struck through by that drop and
    land 3 points above the ground symbol. It reads as VDD grounded.

THE FIX. Each rail label is rewritten IN PLACE as a RECORD=17 power port -- same record index, same
IndexInSheet, same UniqueID, same Location, same text -- with Style 4 (the ground bar) for GND and
GNDADC and Style 2 (the supply arrow) for the seven supplies, matching the 52 ports the drawing
already has. Rewriting in place is the point: no record is added or removed at the label, so no
OwnerIndex anywhere has to be renumbered, which is the mistake that once left a sheet unopenable.

Where the label sits in the middle of a wire rather than at its end, a junction (RECORD=29) is
appended at the same point, because a tap is a T and a T wants a dot. Appending cannot move an
existing index either; only the header count changes.

WHICH WAY THE SYMBOL POINTS is chosen, not assumed. The wire directions leaving the point are read
off first, and the port takes the first FREE perpendicular direction from its preference order --
down, right, left, up for a ground; up, right, left, down for a supply. The symbol's own footprint
is then tested against every drawn object on the sheet, using the same Courier metric the sheet-5
margin work calibrated (0.535 * FontSize per character) plus the port footprint measured off the
exported PDF: a ground bar and its text occupy 30 units along the pointing direction, a supply arrow
20, and about +-11 across.

A label with no free direction, or whose symbol would land on something, KEEPS ITS LABEL and is
listed. That is deliberate and it is why sheet 2 is not in this run at all: most of its rail names
are rows of a connector pin list on a 10-unit pitch, where a 30-unit ground symbol cannot go and the
word GND in a column of row labels is the clearer drawing anyway. The same test skips the pin-list
rows on sheets 4 and 5 without needing to know they are pin lists.

Nothing moves and no wire changes, so the netlist must come back with the same 178 nets over 783
pads. Refuses to run twice.

    python tools/rail_ports.py tools "Imported zulu_a7.PrjPcb"
    python tools/rail_ports.py tools "Imported zulu_a7.PrjPcb" --dry
"""
import sys, os, re, random, string, collections
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field
from sheet5_right_margin import (num, fnum, oi, rectype, points, fonts_of, roots, live,
                                 drawn_boxes, signature)

SHEETS = ['zulu_a7_1', 'zulu_a7_3', 'zulu_a7_4', 'zulu_a7_5', 'zulu_a7_6']
GROUNDS = {'GND', 'GNDADC'}
SUPPLIES = {'VCC3V3', 'VCC1V8', 'VCC1V0', 'VCCADC', 'VU', 'VBATT', 'USB5V0'}
RAILS = GROUNDS | SUPPLIES

# orientation: 0 right, 1 up, 2 left, 3 down -- and the unit step each one points along
STEP = {0: (1, 0), 1: (0, 1), 2: (-1, 0), 3: (0, -1)}
PREFER = {'gnd': (3, 0, 2), 'sup': (1, 0, 2, 3)}   # a ground bar never points up
ALONG = {'gnd': 30.0, 'sup': 20.0}      # bar/arrow plus its text, measured off the PDF
MARGIN = 1.0


def uid():
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(8))


def footprint(x, y, orient, text, kind):
    """the box the port symbol and its own text will occupy, hot point at (x, y)."""
    a = ALONG[kind]
    across = max(10.5, len(text) * 2.9)      # measured: GND +-10.6, VCC3V3 +-17.8
    dx, dy = STEP[orient]
    if dx:
        return (min(x, x + dx * a), y - across, max(x, x + dx * a), y + across)
    return (x - across, min(y, y + dy * a), x + across, max(y, y + dy * a))


def hits(box, others):
    x0, y0, x1, y1 = box
    for bx in others:
        if x0 < bx[2] - MARGIN and bx[0] < x1 - MARGIN and y0 < bx[3] - MARGIN and bx[1] < y1 - MARGIN:
            return bx
    return None


def dirs_at(segs, x, y):
    """orientation codes in which a wire leaves (x, y); mid-run counts as both ways."""
    out, mid = set(), False
    for a, c in segs:
        if a == (x, y) or c == (x, y):
            p, q = (a, c) if a == (x, y) else (c, a)
            if q[0] > p[0]: out.add(0)
            elif q[0] < p[0]: out.add(2)
            elif q[1] > p[1]: out.add(1)
            elif q[1] < p[1]: out.add(3)
        elif a[0] == c[0] == x and min(a[1], c[1]) < y < max(a[1], c[1]):
            out |= {1, 3}; mid = True
        elif a[1] == c[1] == y and min(a[0], c[0]) < x < max(a[0], c[0]):
            out |= {0, 2}; mid = True
    return out, mid


def plan(recs, fonts):
    segs = []
    for h, b in recs:
        if rectype(b) == 27:
            P = points(b)
            segs += list(zip(P, P[1:]))
    boxes = []
    for e in drawn_boxes(recs, fonts):
        b = recs[e[0]][1]
        if rectype(b) == 17:                       # a port already on the sheet: use its real
            x, y = num(b, 'Location.X'), num(b, 'Location.Y')   # footprint, not its text box
            k = 'gnd' if field(b, 'Text') in GROUNDS else 'sup'
            e = (e[0], e[1], footprint(x, y, int(field(b, 'Orientation')), field(b, 'Text'), k), e[3])
        boxes.append(e)
    cand = [i for i, (h, b) in enumerate(recs)
            if rectype(b) == 25 and field(b, 'Text') in RAILS
            and num(b, 'Location.X') is not None]
    # a candidate's own text box must not block its neighbour: every one of them may be leaving.
    # What each candidate leaves BEHIND -- a port footprint if it converts, its label box if it does
    # not -- is added to the blocking set as we go, so the answer does not depend on luck.
    block = [e[2] for e in boxes if e[0] not in set(cand)]
    todo, skipped = [], []
    for i in cand:
        b = recs[i][1]
        t = field(b, 'Text')
        x, y = num(b, 'Location.X'), num(b, 'Location.Y')
        kind = 'gnd' if t in GROUNDS else 'sup'
        taken, mid = dirs_at(segs, x, y)
        if not taken:
            skipped.append((i, t, x, y, 'not on a wire'))
            block.append(next(e[2] for e in boxes if e[0] == i))
            continue
        for o in PREFER[kind]:
            if o in taken:
                continue
            fp = footprint(x, y, o, t, kind)
            if hits(fp, block) is None:
                todo.append((i, t, x, y, o, kind, mid))
                block.append(fp)
                break
        else:
            free = [o for o in PREFER[kind] if o not in taken]
            skipped.append((i, t, x, y, 'no room' if free else 'wires on every free side'))
            block.append(next(e[2] for e in boxes if e[0] == i))
    return todo, skipped


def to_port(b, orient, kind):
    style = '4' if kind == 'gnd' else '2'
    for k in ('Justification', 'Orientation', 'Location.X_Frac', 'Location.Y_Frac'):
        b = re.sub(rb'\|' + k.encode().replace(b'.', rb'\.') + rb'=[^|\x00]*', b'', b)
    b = b.replace(b'|RECORD=25|', b'|RECORD=17|', 1)
    b = set_field(b, 'FontID', '1')
    b = b.replace(b'|Text=', f'|Style={style}|ShowNetName=T|Orientation={orient}|Text='.encode(), 1)
    return b


def junction(x, y):
    return (b'|RECORD=29|OwnerPartId=1|Location.X=%d|Location.Y=%d|Color=128|Locked=T|UniqueID=%s\x00'
            % (x, y, uid().encode()))


def main(prj, dry):
    total = collections.Counter()
    for name in SHEETS:
        path = os.path.join(prj, name + '.SchDoc')
        recs = split(read_stream(path, 'FileHeader'))
        N = len(recs)
        assert int(field(recs[0][1], 'Weight')) == N - 1, f'{name}: header count is already wrong'
        fonts = fonts_of(recs)
        todo, skipped = plan(recs, fonts)
        sig = signature(recs)
        print(f'{name}: {len(todo)} labels become ports, {len(skipped)} keep their label')
        for i, t, x, y, o, kind, mid in todo:
            total[t] += 1
            print(f'    rec{i:<7} ({x:5},{y:5}) {t:8} -> Style {"4" if kind == "gnd" else "2"} '
                  f'Orientation {o} {"(+junction)" if mid else ""}')
        for i, t, x, y, why in skipped:
            total['skipped'] += 1
            print(f'    rec{i:<7} ({x:5},{y:5}) {t:8} kept: {why}')
        if dry or not todo:
            continue
        adds = []
        for i, t, x, y, o, kind, mid in todo:
            recs[i][1] = to_port(recs[i][1], o, kind)
            if mid:
                adds.append([bytes(4), junction(x, y)])
        recs += adds
        recs[0][1] = set_field(recs[0][1], 'Weight', str(len(recs) - 1))
        blob = join(recs)
        write_stream(path, 'FileHeader', blob)
        assert read_stream(path, 'FileHeader') == blob
        verify(path, sig, len(todo), len(adds))
    if not any(v for k, v in total.items() if k != 'skipped'):
        raise SystemExit('every rail name that can carry a symbol already does; nothing done')
    print('\n' + ', '.join(f'{k} x{v}' for k, v in sorted(total.items())))


def verify(path, sig_before, made, added):
    recs = split(read_stream(path, 'FileHeader'))
    assert int(field(recs[0][1], 'Weight')) == len(recs) - 1, 'header count'
    assert all(b.endswith(b'\x00') for h, b in recs), 'a record lost its terminator'
    uids = [field(b, 'UniqueID') for h, b in recs if field(b, 'UniqueID')]
    assert len(uids) == len(set(uids)), 'duplicate UniqueID'
    for i, (h, b) in enumerate(recs):
        o = oi(b)
        if o is not None:
            assert 0 <= o < len(recs), f'record {i} points at a record that is not there'
    ports = [b for h, b in recs if rectype(b) == 17]
    for b in ports:
        assert field(b, 'Style') in ('2', '4') and field(b, 'Orientation') in '0123', b[:90]
        assert field(b, 'Text'), 'a port lost its name'
    fonts = fonts_of(recs)
    boxes = drawn_boxes(recs, fonts)
    assert signature(recs) == sig_before, 'the drawing connectivity changed'
    print(f'    verify: {made} ports written, {added} junctions added, {len(ports)} ports on the '
          f'sheet now, {len(boxes)} drawn objects, connectivity unchanged')


if __name__ == '__main__':
    main(sys.argv[2], '--dry' in sys.argv)
