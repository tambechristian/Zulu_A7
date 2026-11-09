"""Zulu_a7_no_pmod: delete the Pmod from the schematic at file level (sheets closed in Altium).

    python tools/no_pmod_schematic.py [--apply]

Sheet 2: J1, R26-R33 with their children, the note frame, and every free wire / label / power port / junction in the
block's window. Sheet 5: the eight JA net labels with their wire stubs, and the 'Pmod JA' caption heading. Sheet 0: the
'Pmod Header' block-diagram label. OwnerIndex of every surviving record is renumbered and the header Weight updated.
"""
import os
import re
import sys

sys.path.insert(0, r'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium/tools')
from fix_text_orientation import field, join, read_stream, set_field, split, write_stream  # noqa: E402

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Imported zulu_a7.PrjPcb')
APPLY = '--apply' in sys.argv
PARTS = {'J1', 'R26', 'R27', 'R28', 'R29', 'R30', 'R31', 'R32', 'R33'}
JA = {'JA%d' % i for i in (1, 2, 3, 4, 7, 8, 9, 10)}


def geti(b, k):
    v = field(b, k)
    return int(v) if v not in (None, '') else None


def rec(b):
    return geti(b, 'RECORD')


def wire_pts(b):
    n = geti(b, 'LocationCount')
    return [(geti(b, 'X%d' % k), geti(b, 'Y%d' % k)) for k in range(1, n + 1)]


def children(R, roots):
    """indices (header at 0) of the records owned, directly or not, by the given records"""
    kids = {}
    for j, (_, b) in enumerate(R):
        o = geti(b, 'OwnerIndex')
        if o is not None:
            kids.setdefault(o + 1, []).append(j)
    out, todo = set(), list(roots)
    while todo:
        j = todo.pop()
        if j not in out:
            out.add(j)
            todo.extend(kids.get(j, []))
    return out


def sheet2(R):
    roots = []
    owners = {j: b for j, (_, b) in enumerate(R) if rec(b) == 1}
    for j, (_, b) in enumerate(R):
        if rec(b) == 34 and field(b, 'Text') in PARTS and (geti(b, 'OwnerIndex') or 0) + 1 in owners:
            roots.append(geti(b, 'OwnerIndex') + 1)
    assert len(roots) == 9, roots
    kill = children(R, roots)
    win = lambda x, y: 205 <= x <= 405 and 400 <= y <= 480  # noqa: E731
    free = 0
    for j, (_, b) in enumerate(R):
        if geti(b, 'OwnerIndex') is not None:
            continue
        r = rec(b)
        if r == 28 and (field(b, 'Text') or '').startswith('Digilent 12-pin Pmod'):
            kill.add(j)
            free += 1
        elif r == 27 and all(win(*p) for p in wire_pts(b)):
            kill.add(j)
            free += 1
        elif r in (17, 25, 29) and win(geti(b, 'Location.X'), geti(b, 'Location.Y')):
            kill.add(j)
            free += 1
    print('sheet 2: %d parts, %d records, %d free objects' % (len(roots), len(kill), free))
    assert free == 46
    return kill


def sheet5(R):
    kill, spots = set(), set()
    for j, (_, b) in enumerate(R):
        if geti(b, 'OwnerIndex') is None and rec(b) == 25 and field(b, 'Text') in JA:
            kill.add(j)
            spots.add((geti(b, 'Location.X'), geti(b, 'Location.Y')))
    assert len(kill) == 8
    w = 0
    for j, (_, b) in enumerate(R):
        if geti(b, 'OwnerIndex') is None and rec(b) == 27:
            P = wire_pts(b)
            if len(P) == 2 and (P[0] in spots or P[1] in spots):
                kill.add(j)
                w += 1
        elif rec(b) == 4 and field(b, 'Text') == 'Pmod JA (bank 16 x5)':
            kill.add(j)
    assert w == 8
    print('sheet 5: %d records' % len(kill))
    return kill


def sheet0(R):
    """block diagram: the 'Pmod Header' box (fill + 4 outline lines + label) and its arrow (fill polygon + outline)"""
    box = [(665, 787), (775, 787), (775, 842), (665, 842)]
    arrow = [(622, 729), (615, 722), (622, 714), (727, 714), (727, 779), (720, 787), (712, 779), (712, 729)]
    kill = set()
    for j, (_, b) in enumerate(R):
        if geti(b, 'OwnerIndex') is not None:
            continue
        r = rec(b)
        if r == 4 and field(b, 'Text') == 'Pmod Header':
            kill.add(j)
        elif r == 14 and (geti(b, 'Location.X'), geti(b, 'Location.Y')) == (665, 787):
            kill.add(j)
        elif r in (6, 7):
            P = wire_pts(b)
            if r == 7 and P == arrow:
                kill.add(j)
            elif r == 6 and len(P) == 2 and (all(p in box for p in P) or all(p in arrow for p in P)):
                kill.add(j)
    print('sheet 0: %s' % sorted(kill))
    assert len(kill) == 3 + 4 + 8 or len(kill) >= 11
    return kill


def run(name, pick):
    p = os.path.join(DIR, name)
    d = read_stream(p, 'FileHeader')
    R = split(d)
    assert join(R) == d
    assert all(h[3] == 0 for h, _ in R), 'binary records present'
    kill = pick(R)
    newi, n = {}, 0
    for j in range(len(R)):
        if j not in kill:
            newi[j] = n
            n += 1
    out = []
    for j, (h, b) in enumerate(R):
        if j in kill:
            continue
        o = geti(b, 'OwnerIndex')
        if o is not None and o != -1 and j > 0:
            assert o + 1 in newi, (name, j, o)
            b2 = set_field(b, 'OwnerIndex', str(newi[o + 1] - 1))
            b = b2
        out.append([h, b])
    w = geti(out[0][1], 'Weight')
    assert w == len(R) - 1, (w, len(R))
    out[0][1] = set_field(out[0][1], 'Weight', str(len(out) - 1))
    print('  %s: %d -> %d records' % (name, len(R), len(out)))
    if APPLY:
        write_stream(p, 'FileHeader', join(out))
        Q = split(read_stream(p, 'FileHeader'))
        assert len(Q) == len(out)


run('zulu_a7_2.SchDoc', sheet2)
run('zulu_a7_5.SchDoc', sheet5)
run('zulu_a7_0.SchDoc', sheet0)
