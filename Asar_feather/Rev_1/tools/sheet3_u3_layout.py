"""asar_a7_3.SchDoc (title block "Sheet 4", Memory), 2026-11-17: redraw U3 (AS4C32M16SB-7BIN, 54-ball FBGA) as one
readable block, the way Zulu_A7_no_pmod/Rev_2/tools/sheet3_u3_layout.py did for the no-PMOD board's TSOP U3.

WHY.  U3 came from EAGLE as 55 parts (part 1 = the "U3" text, parts 2-55 = one pin each, part n = TSOP pin n-1 with
the FBGA ball as the pin designator). The signal pins sat in a box at the top right and the 14 power pins in a
separate column block with C3-C9, each cap joined to its pins only by GND / VCC3V3 ports.

WHAT (no connection changes; the script proves the sheet's nets are identical before and after).
- One box, x XL..XR, y YBOT..YTOP (same frame as the no-PMOD sheet):
    right edge  DQ0-DQ7, LDQM, DQ8-DQ15, UDQM at 20-unit pitch, each on a short stub with its existing net label
                (D0-D15, LDQM, UDQM). This board has no DQ series resistors, so nothing sits between.
    left edge   A0-A12, BA0/BA1, CS#/RAS#/CAS#/WE#, CKE/CLK, NC, each with its existing net label on a short stub.
    top edge    the 7 supply balls, each WIRED up to its decoupling cap and on to one VCC3V3 rail with a single port.
    bottom edge the 7 ground balls, each directly under the supply ball it mirrors in its FBGA row (the pairing the
                sheet's U3 DECOUPLING note gives: VDD A9/E7/J9 -> VSS A1/E3/J1, VDDQ A7/B3/C7/D3 -> VSSQ
                A3/B7/C3/D7), with a GND port.
  The caps keep their pairing: Cn sits on the supply ball of its old row. Their "0.1uF" comments are hidden (a
  caption gives the value): at this pitch the text runs into the next column's GND port.
- Each U3 pin part is moved rigidly (rotated about its pin's hot end, new part Orientation), its visible pin name
  placed inside the box. Caps are translated only.
- Old stubs, labels, ports and junctions of U3 and the caps are deleted and redrawn; the four old box lines are
  reused. The microSD note frame is narrowed and the two long X3 note lines are wrapped so nothing overlaps.

    python tools/sheet3_u3_layout.py <sheet in> <sheet out>      (in == out to edit in place)
    python tools/sheet3_u3_layout.py --verify <before> <after>
"""
import hashlib
import math
import os
import random
import shutil
import string
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schdoc import delete, field, join, owner, read_stream, set_field, split, write_stream  # noqa: E402

SRC_MD5 = '053ed08cec307364ea9d9191f3cc9d84'
XL, XR, YTOP, YBOT = 555, 875, 1010, 610
PIN_L = 20
STUB = 10
RIGHT = [('DQ0', 990), ('DQ1', 970), ('DQ2', 950), ('DQ3', 930), ('DQ4', 910), ('DQ5', 890), ('DQ6', 870),
         ('DQ7', 850), ('LDQM', 830), ('DQ8', 790), ('DQ9', 770), ('DQ10', 750), ('DQ11', 730), ('DQ12', 710),
         ('DQ13', 690), ('DQ14', 670), ('DQ15', 650), ('UDQM', 630)]
LEFT = [('A0', 970), ('A1', 960), ('A2', 950), ('A3', 940), ('A4', 930), ('A5', 920), ('A6', 910), ('A7', 900),
        ('A8', 890), ('A9', 880), ('A10', 870), ('A11', 860), ('A12', 850), ('BA0', 830), ('BA1', 820), ('CS#', 810),
        ('RAS#', 800), ('CAS#', 790), ('WE#', 780), ('CKE', 770), ('CLK', 760), ('NC', 750)]  # below R6's port (525, 987)
SUPPLY = ['VDD@3', 'VDDQ@3', 'VDDQ@2', 'VDD@2', 'VDD@1', 'VDDQ@1', 'VDDQ@4']   # top edge, left to right (= C3..C9)
COL_X = [XL + 10 + 45 * k for k in range(7)]
CAP_Y, VCC_Y = YTOP + PIN_L + 35, YTOP + PIN_L + 55       # cap row, VCC3V3 rail (one port, at the east end)
CAPS = ('C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9')
CAPTION = [(XL, YBOT - PIN_L - 50, 'C3-C9: 0.1 uF VCC3V3 decoupling, drawn one per supply ball (on the PCB'),
           (XL, YBOT - PIN_L - 60, 'they sit under U3, see U3 DECOUPLING). Each ground ball is drawn under'),
           (XL, YBOT - PIN_L - 70, 'the supply ball it mirrors in its FBGA row.')]
WIRE = 'LineWidth=1|Color=32768'
SD_FRAME_CORNER_X, SD_FRAME_BOTTOM, SD_FRAME_TOP = 500, 600, 755
X3_LINES = [(70, 590, '2026-09-06: X3 is now the Hirose DM3D-SF push-pull socket'),
            (70, 580, '(HRS 609-0025-8), DM3 catalog p9. Same 8-contact pinout;'),
            (70, 570, 'shell pads G1-G4 to GND; card-detect switch A/B (closed with'),
            (70, 560, 'card) left open. PCB footprint DM3D-SF.')]   # the old "needs its own footprint" was stale


def num(b, k):
    v = field(b, k)
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def fval(b, k):
    v = num(b, k)
    if v is None:
        return None
    return v + (num(b, k + '_Frac') or 0) / 100000.0


def drop_key(b, k):
    v = field(b, k)
    return b if v is None else b.replace(b'|' + k.encode() + b'=' + v.encode(), b'')


def set_f(b, k, v):
    """Write a coordinate with its _Frac (1e-5) part; drops a stale _Frac."""
    whole = math.floor(v + 1e-9)
    frac = int(round((v - whole) * 100000))
    if frac >= 100000:
        whole, frac = whole + 1, 0
    b = set_field(b, k, str(whole))
    return set_field(b, k + '_Frac', str(frac)) if frac else drop_key(b, k + '_Frac')


def set_or_drop(b, k, v):
    """Altium omits a zero Orientation / Justification: write it only when non-zero."""
    return set_field(b, k, str(v)) if v else drop_key(b, k)


def uid():
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(8))


def hot_end(b):
    L = num(b, 'PinLength') or 0
    r = (num(b, 'PinConglomerate') or 0) & 3
    dx, dy = [(1, 0), (0, 1), (-1, 0), (0, -1)][r]
    return fval(b, 'Location.X') + dx * L, fval(b, 'Location.Y') + dy * L


def rot(p, c, q):
    """Rotate point p about c by q quarter-turns CCW (returns the offset from c)."""
    x, y = p[0] - c[0], p[1] - c[1]
    for _ in range(q % 4):
        x, y = -y, x
    return x, y


def move_part(R, root, kids, f):
    """Apply f((x, y)) -> (x, y) to the part and every child coordinate (Location, Corner, Xn/Yn)."""
    for i in [root] + kids:
        b = R[i][1]
        for kx, ky in (('Location.X', 'Location.Y'), ('Corner.X', 'Corner.Y')):
            if fval(b, kx) is not None and fval(b, ky) is not None:
                x, y = f((fval(b, kx), fval(b, ky)))
                b = set_f(set_f(b, kx, x), ky, y)
        n = num(b, 'LocationCount')
        if n:
            for j in range(1, n + 1):
                x, y = f((fval(b, 'X%d' % j), fval(b, 'Y%d' % j)))
                b = set_f(set_f(b, 'X%d' % j, x), 'Y%d' % j, y)
        R[i][1] = b


def seg_has(p, a, b):
    (x, y), (x1, y1), (x2, y2) = p, a, b
    if abs((x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)) > 1e-6:
        return False
    return min(x1, x2) - 1e-6 <= x <= max(x1, x2) + 1e-6 and min(y1, y2) - 1e-6 <= y <= max(y1, y2) + 1e-6


def connectivity(R):
    """Nets on the sheet: list of (frozenset of names, frozenset of (ref, pin)); wires join at endpoints and at points
    on segments (labels, ports, pins, junctions, other wire ends), as Altium does."""
    des = {owner(b): field(b, 'Text') for h, b in R if field(b, 'RECORD') == '34'}
    cur = {i: num(b, 'CurrentPartId') for i, (h, b) in enumerate(R) if field(b, 'RECORD') == '1'}
    nodes = []          # (point, kind, payload)
    for h, b in R:
        r = field(b, 'RECORD')
        if r == '2':
            o = owner(b)
            if o in cur and num(b, 'OwnerPartId') == cur[o]:
                nodes.append((hot_end(b), 'pin', (des.get(o), field(b, 'Designator'))))
        elif r in ('25', '17'):
            nodes.append(((fval(b, 'Location.X'), fval(b, 'Location.Y')), 'name', field(b, 'Text')))
    wires = []
    for h, b in R:
        if field(b, 'RECORD') == '27':
            p = [(fval(b, 'X%d' % j), fval(b, 'Y%d' % j)) for j in range(1, num(b, 'LocationCount') + 1)]
            wires.append(list(zip(p, p[1:])))
    parent = list(range(len(nodes) + len(wires)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        parent[find(a)] = find(b)
    W0 = len(nodes)
    ends = [{p for s in w for p in s} for w in wires]
    for k, w in enumerate(wires):
        for n, (p, kind, pay) in enumerate(nodes):
            if any(seg_has(p, a, b) for a, b in w):
                union(n, W0 + k)
        for k2 in range(k + 1, len(wires)):
            if any(any(seg_has(p, a, b) for a, b in w) for p in ends[k2]) or \
               any(any(seg_has(p, a, b) for a, b in wires[k2]) for p in ends[k]):
                union(W0 + k, W0 + k2)
    by = {}
    for n, (p, kind, pay) in enumerate(nodes):          # pins at the same point join directly
        by.setdefault((round(p[0], 3), round(p[1], 3)), []).append(n)
    for ns in by.values():
        for n in ns[1:]:
            union(ns[0], n)
    groups = {}
    for n, (p, kind, pay) in enumerate(nodes):
        g = groups.setdefault(find(n), [set(), set()])
        (g[0] if kind == 'name' else g[1]).add(pay)
    return sorted((frozenset(a), frozenset(b)) for a, b in groups.values() if b or len(a) > 0)


def net_map(R):
    """{net name or pin-set key: frozenset of pins}, merging same-named groups as Altium does on one sheet."""
    out = {}
    for names, pins in connectivity(R):
        key = '|'.join(sorted(names)) if names else 'unnamed:' + ','.join(sorted('%s-%s' % p for p in pins))
        if not pins:
            continue
        for nm in (names or [key]):
            out.setdefault(nm, set()).update(pins)
    return {k: frozenset(v) for k, v in out.items()}


def mirror(ball):
    """The ball at the mirror position in the same FBGA row (columns 1-3 <-> 9-7)."""
    return ball[0] + str(10 - int(ball[1:]))


def main(src, dst):
    if hashlib.md5(open(src, 'rb').read()).hexdigest() != SRC_MD5:
        raise SystemExit('%s is not the expected asar_a7_3 sheet (md5 %s)' % (src, SRC_MD5))
    raw = read_stream(src)
    R = split(raw)
    assert join(R) == raw and int(field(R[0][1], 'Weight')) == len(R) - 1
    before = net_map(R)
    des = {owner(b): field(b, 'Text') for h, b in R if field(b, 'RECORD') == '34'}
    kids = {}
    for i, (h, b) in enumerate(R):
        o = owner(b)
        if o is not None:
            kids.setdefault(o, []).append(i)
    comps = [i for i, (h, b) in enumerate(R) if field(b, 'RECORD') == '1']

    # ---- U3 pin parts, keyed by gate name (VDD@3, DQ0, ...) -------------------------------------------------------
    u3 = {}
    for i in comps:
        if des.get(i) != 'U3':
            continue
        pid = num(R[i][1], 'CurrentPartId')
        vis = [k for k in kids.get(i, []) if num(R[k][1], 'OwnerPartId') == pid]
        pins = [k for k in vis if field(R[k][1], 'RECORD') == '2']
        gate = [k for k in vis if field(R[k][1], 'RECORD') == '41' and field(R[k][1], 'Name') == 'GATE']
        if pid == 1:
            u3['part1'] = i
            continue
        assert len(pins) == 1 and len(gate) == 1, (pid, pins, gate)
        name = field(R[gate[0]][1], 'Text')
        assert name not in u3, name
        u3[name] = dict(root=i, pin=pins[0], gate=gate[0], ball=field(R[pins[0]][1], 'Designator'))
    assert len(u3) == 55
    by_ball = {v['ball']: g for g, v in u3.items() if g != 'part1'}
    old_hot = {g: hot_end(R[v['pin']][1]) for g, v in u3.items() if g != 'part1'}

    # what hangs on each U3 pin today: the label / port name, and the records to delete
    wires = [(i, [(fval(b, 'X%d' % j), fval(b, 'Y%d' % j)) for j in range(1, num(b, 'LocationCount') + 1)])
             for i, (h, b) in enumerate(R) if field(b, 'RECORD') == '27']
    free = [(i, (fval(b, 'Location.X'), fval(b, 'Location.Y')), field(b, 'RECORD'), field(b, 'Text'))
            for i, (h, b) in enumerate(R) if field(b, 'RECORD') in ('25', '17', '29') and owner(b) is None]

    def network(p0):
        pts, ws, grew = {p0}, set(), True
        while grew:
            grew = False
            for i, w in wires:
                if i not in ws and any(q in pts for q in w):
                    ws.add(i)
                    pts |= set(w)
                    grew = True
        segs = [s for i, w in wires if i in ws for s in zip(w, w[1:])]
        objs = [(i, kind, t) for i, p, kind, t in free if p in pts or any(seg_has(p, a, b) for a, b in segs)]
        return ws, objs
    drop = set()
    label = {}
    for g, p in old_hot.items():
        ws, objs = network(p)
        drop |= ws
        drop |= {i for i, kind, t in objs}
        names = {t for i, kind, t in objs if kind == '25'}
        assert len(names) <= 1, (g, names)
        label[g] = names.pop() if names else None

    # ---- caps C3-C9: which supply ball's row each sits on ------------------------------------------------------
    caps = {}
    for i in comps:
        ref = des.get(i)
        if ref not in CAPS:
            continue
        cpins = {field(R[k][1], 'Designator'): hot_end(R[k][1]) for k in kids[i] if field(R[k][1], 'RECORD') == '2'}
        row = [g for g in SUPPLY if abs(old_hot[g][1] - cpins['1'][1]) < 1e-6]
        assert len(row) == 1, (ref, cpins, row)
        assert cpins['1'][0] < cpins['2'][0], (ref, 'pin 2 is on the ground side; this layout puts pin 1 there')
        caps[row[0]] = dict(root=i, ref=ref, centre=((cpins['1'][0] + cpins['2'][0]) / 2, cpins['1'][1]))
    assert sorted(caps) == sorted(SUPPLY) and [caps[g]['ref'] for g in SUPPLY] == list(CAPS), caps
    ground_of = {}
    for s in SUPPLY:                                    # the U3 DECOUPLING note's mirror pairing, checked by domain
        g = by_ball[mirror(u3[s]['ball'])]
        assert g.split('@')[0] == s.split('@')[0].replace('VDD', 'VSS'), (s, u3[s]['ball'], g)
        ground_of[s] = g
    assert len(set(ground_of.values())) == 7

    # ---- move the U3 pin parts --------------------------------------------------------------------------------
    plan = {}
    for g, y in RIGHT:
        plan[g] = ((XR + PIN_L, y), 2)
    for g, y in LEFT:
        plan[g] = ((XL - PIN_L, y), 0)
    for k, s in enumerate(SUPPLY):
        plan[s] = ((COL_X[k], YTOP + PIN_L), 3)
        plan[ground_of[s]] = ((COL_X[k], YBOT - PIN_L), 1)
    assert sorted(plan) == sorted(g for g in u3 if g != 'part1')
    for g, (h_new, o_new) in plan.items():
        v = u3[g]
        o_old = num(R[v['root']][1], 'Orientation') or 0
        q = (o_new - o_old) % 4
        h_old = old_hot[g]
        move_part(R, v['root'], kids[v['root']], lambda p, h_old=h_old, h_new=h_new, q=q:
                  tuple(a + b for a, b in zip(h_new, rot(p, h_old, q))))
        R[v['root']][1] = set_or_drop(R[v['root']][1], 'Orientation', o_new)
        for k in kids[v['root']]:                       # every pin of this part record turns with it
            pb = R[k][1]
            if field(pb, 'RECORD') == '2':
                c = num(pb, 'PinConglomerate') or 0
                R[k][1] = set_field(pb, 'PinConglomerate', str((c & ~3) | (((c & 3) + q) % 4)))
        assert hot_end(R[v['pin']][1]) == h_new, (g, hot_end(R[v['pin']][1]), h_new)
        # the visible pin name, inside the box
        gb = R[v['gate']][1]
        hx, hy = h_new
        pos, orient, just = {0: ((hx + 22.5, hy - 4), 0, 0), 2: ((hx - 22.5, hy + 4), 0, 8),
                             3: ((hx + 4, hy - 22), 1, 2), 1: ((hx + 4, hy + 22), 1, 0)}[o_new]
        gb = set_f(set_f(gb, 'Location.X', pos[0]), 'Location.Y', pos[1])
        R[v['gate']][1] = set_or_drop(set_or_drop(gb, 'Orientation', orient), 'Justification', just)

    # U3 designator and comment in the middle of the box, bottom-centre justified (review: left-anchored at a guessed
    # text width they sat 16-19 units left of centre; Courier New 8 is 4.27 units per character)
    for k in kids[u3['part1']]:
        b = R[k][1]
        if field(b, 'IsHidden') == 'T' or fval(b, 'Location.X') is None:
            continue
        if field(b, 'Name') == 'PART' and field(b, 'Text') == 'U3':
            b = set_f(set_f(b, 'Location.X', (XL + XR) / 2), 'Location.Y', (YTOP + YBOT) / 2 + 6)
            R[k][1] = set_or_drop(b, 'Justification', 1)
        elif field(b, 'Name') == 'Comment':
            b = set_f(set_f(b, 'Location.X', (XL + XR) / 2), 'Location.Y', (YTOP + YBOT) / 2 - 8)
            R[k][1] = set_or_drop(b, 'Justification', 1)

    # ---- box: reuse the four old frame lines ---------------------------------------------------------------------
    box = [i for i, (h, b) in enumerate(R) if field(b, 'RECORD') == '6' and owner(b) is None
           and {(num(b, 'X1'), num(b, 'Y1')), (num(b, 'X2'), num(b, 'Y2'))} <= {(775, 1077), (775, 797), (895, 797), (895, 1077)}]
    assert len(box) == 4, box
    for i, (a, c) in zip(box, [((XR, YTOP), (XL, YTOP)), ((XL, YTOP), (XL, YBOT)), ((XR, YBOT), (XR, YTOP)), ((XL, YBOT), (XR, YBOT))]):
        b = R[i][1]
        R[i][1] = set_field(set_field(set_field(set_field(b, 'X1', str(a[0])), 'Y1', str(a[1])), 'X2', str(c[0])), 'Y2', str(c[1]))

    new = []

    def wire(a, c):
        new.append('|RECORD=27|OwnerPartId=-1|%s|UniqueID=%s|LocationCount=2|X1=%d|Y1=%d|X2=%d|Y2=%d'
                   % (WIRE, uid(), a[0], a[1], c[0], c[1]))

    def netlabel(p, text, just=0):
        new.append('|RECORD=25|OwnerPartId=-1|Location.X=%d|Location.Y=%d|%sColor=128|FontID=3|Text=%s|UniqueID=%s'
                   % (p[0], p[1], ('Justification=%d|' % just) if just else '', text, uid()))

    def port(p, text, style, orient):
        new.append('|RECORD=17|OwnerPartId=-1|Style=%d|ShowNetName=T|Location.X=%d|Location.Y=%d|Orientation=%d|'
                   'Color=128|FontID=1|Text=%s|UniqueID=%s' % (style, p[0], p[1], orient, text, uid()))

    def junction(p):
        new.append('|RECORD=29|OwnerPartId=-1|Location.X=%d|Location.Y=%d|Color=128|Locked=T|UniqueID=%s' % (p[0], p[1], uid()))

    # right edge: DQn -> Dn label, LDQM / UDQM -> label, each on a short stub (mirror of the left edge)
    for g, y in RIGHT:
        want = 'D' + g[2:] if g.startswith('DQ') else g
        assert label[g] == want, (g, label[g])
        wire((XR + PIN_L, y), (XR + PIN_L + STUB, y))
        netlabel((XR + PIN_L + STUB, y), label[g])
    # left edge: stub + label (NC stays open)
    for g, y in LEFT:
        if label[g] is None:
            assert g == 'NC', g
            continue
        wire((XL - PIN_L, y), (XL - PIN_L - STUB, y))
        netlabel((XL - PIN_L - STUB, y), label[g], 2)
    # top / bottom: caps and ports
    for k, s in enumerate(SUPPLY):
        x = COL_X[k]
        cap = caps[s]
        c_old = cap['centre']
        dx, dy = (x - 10) - c_old[0], CAP_Y - c_old[1]
        move_part(R, cap['root'], kids[cap['root']], lambda p, dx=dx, dy=dy: (p[0] + dx, p[1] + dy))
        for kk in kids[cap['root']]:                    # the value is in the caption: at 45-unit pitch the
            b = R[kk][1]                                # "0.1uF" text runs into the next column's GND port
            if field(b, 'RECORD') == '41' and field(b, 'Name') == 'Comment':
                R[kk][1] = set_field(b, 'IsHidden', 'T')
        wire((x, YTOP + PIN_L), (x, CAP_Y))
        wire((x, CAP_Y), (x, VCC_Y))
        junction((x, CAP_Y))
        if 0 < k < 6:
            junction((x, VCC_Y))                        # T into the rail
        wire((x - 20, CAP_Y), (x - 25, CAP_Y))
        port((x - 25, CAP_Y), 'GND', 4, 3)
        port((x, YBOT - PIN_L), 'GND', 4, 3)
    # one VCC3V3 rail over the seven supply columns, one port at its east end
    wire((COL_X[0], VCC_Y), (COL_X[-1], VCC_Y))
    wire((COL_X[-1], VCC_Y), (COL_X[-1], VCC_Y + 10))
    junction((COL_X[-1], VCC_Y))
    port((COL_X[-1], VCC_Y + 10), 'VCC3V3', 2, 1)

    # ---- notes ------------------------------------------------------------------------------------------------
    n_sd = 0
    for i, (h, b) in enumerate(R):
        if field(b, 'RECORD') == '4' and owner(b) is None:
            t = field(b, 'Text') or ''
            if t.startswith('2026-09-06: X3 is now') or t.startswith('shell pads G1-G4'):
                drop.add(i)
        if field(b, 'RECORD') == '28' and (field(b, 'Text') or '').startswith('microSD runs the NATIVE'):
            b = drop_key(set_field(b, 'Corner.X', str(SD_FRAME_CORNER_X)), 'Corner.X_Frac')
            b = drop_key(set_field(b, 'Corner.Y', str(SD_FRAME_TOP)), 'Corner.Y_Frac')
            R[i][1] = drop_key(set_field(b, 'Location.Y', str(SD_FRAME_BOTTOM)), 'Location.Y_Frac')
            n_sd += 1
    assert n_sd == 1 and len([i for i in drop if field(R[i][1], 'RECORD') == '4']) == 2
    for x, y, t in CAPTION + X3_LINES:
        new.append('|RECORD=4|OwnerPartId=-1|Location.X=%d|Location.Y=%d|Color=8421504|FontID=3|Text=%s|UniqueID=%s'
                   % (x, y, t, uid()))

    for body in new:
        R.append([bytes(4), body.encode('latin-1') + b'\x00'])
    R = delete(R, drop)
    R[0][1] = set_field(R[0][1], 'Weight', str(len(R) - 1))
    blob = join(R)
    if os.path.abspath(dst) != os.path.abspath(src):
        shutil.copyfile(src, dst)
    write_stream(dst, blob)
    assert read_stream(dst) == blob
    print('%s: %d records -> %d (deleted %d, added %d)' % (os.path.basename(dst), len(split(raw)), len(R), len(drop), len(new)))
    report(before, net_map(split(read_stream(dst))))


def report(before, after):
    if before == after:
        print('verify: sheet nets identical (%d nets, %d pins)' % (len(after), len({p for v in after.values() for p in v})))
        return
    for k in sorted(set(before) | set(after)):
        if before.get(k) != after.get(k):
            print('DIFF', k, sorted(before.get(k, ())), '->', sorted(after.get(k, ())))
    raise SystemExit('connectivity changed')


if __name__ == '__main__':
    if sys.argv[1] == '--verify':
        report(net_map(split(read_stream(sys.argv[2]))), net_map(split(read_stream(sys.argv[3]))))
    else:
        main(sys.argv[1], sys.argv[2])
