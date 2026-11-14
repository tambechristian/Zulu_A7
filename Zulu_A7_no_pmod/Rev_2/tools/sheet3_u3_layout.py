"""Sheet 3 (zulu_a7_3.SchDoc), 2026-11-13: redraw U3 (AS4C32M16SB SDRAM) as one readable block.

WHY.  U3 came from EAGLE as 55 parts (part 1 = the "U3" text, parts 2-55 = one pin each). The signal pins sat in a
box at the top right, the 14 power pins in a separate column block with C3-C9, and the 16 DQ series resistors R119-R134
(tools/dq_series_r_sch.py) in a grid at the lower left, joined to U3 only by SDRAM-Dn net labels.

WHAT (no connection changes; verify() proves the sheet's nets are identical before and after).
- One box, x XL..XR, y YBOT..YTOP:
    right edge  DQ0-DQ7, LDQM, DQ8-DQ15, UDQM at 20-unit pitch; each DQ pin is WIRED to pin 1 of its resistor, whose
                pin 2 carries the Dn label (U1 side, XDC name); LDQM / UDQM wired to their labels.
    left edge   A0-A12, BS0/BS1, CS#/RAS#/CAS#/WE#, CKE/CLK, NC, each with its existing net label on a short stub.
    top edge    the 7 supply pins (1, 3, 9, 14, 27, 43, 49), each wired up to its decoupling cap and on to one VCC3V3
                rail with a single port (review: seven port texts at 45-unit pitch ran together).
    bottom edge the 7 ground pins, each directly under the supply pin it faces in the TSOP (pin 55-n), with a GND port.
  The caps keep their pairing: Cn sits on the supply pin of its old row. Their "0.1uF" comments are hidden (the
  caption gives the value): at this pitch the text ran into the next column's GND port.
- Each U3 pin part is moved rigidly (rotated about its pin's hot end, new part Orientation), its visible pin name
  placed inside the box. Caps and resistors are translated only. The resistors' per-part "22" comment is hidden and
  one caption names the value; the old two-line caption is replaced.
- Old stubs, labels, ports and junctions of U3, the caps and the resistors are deleted and redrawn; the four old box
  lines are reused. The microSD note frame is narrowed and the two long X3 note lines are wrapped so nothing overlaps.

    python tools/sheet3_u3_layout.py <sheet 3 in> <sheet 3 out>      (in == out to edit in place)
    python tools/sheet3_u3_layout.py --verify <before> <after>
"""
import math
import os
import random
import string
import sys

sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1/tools')
from schdoc import delete, field, join, owner, read_stream, set_field, split, write_stream  # noqa: E402

SRC_MD5 = '79d87a7a7f9434b3a4909a7ae96bc86e'
XL, XR, YTOP, YBOT = 555, 875, 1010, 610
PIN_L = 20
RIGHT = [('2', 990), ('4', 970), ('5', 950), ('7', 930), ('8', 910), ('10', 890), ('11', 870), ('13', 850), ('15', 830),
         ('42', 790), ('44', 770), ('45', 750), ('47', 730), ('48', 710), ('50', 690), ('51', 670), ('53', 650), ('39', 630)]
LEFT = [('23', 970), ('24', 960), ('25', 950), ('26', 940), ('29', 930), ('30', 920), ('31', 910), ('32', 900),
        ('33', 890), ('34', 880), ('22', 870), ('35', 860), ('36', 850), ('20', 830), ('21', 820), ('19', 810), ('18', 800),
        ('17', 790), ('16', 780), ('37', 770), ('38', 760), ('40', 750)]      # below R6's VCC3V3 port at (525, 987)
SUPPLY = ['1', '3', '9', '14', '27', '43', '49']          # top edge, left to right
COL_X = [XL + 10 + 45 * k for k in range(7)]   # last column's vertical name clears DQ0/DQ1 and UDQM
CAP_Y, VCC_Y = YTOP + PIN_L + 35, YTOP + PIN_L + 55       # cap row, VCC3V3 rail (one port, at the east end)
DQ_BIT = {'2': 0, '4': 1, '5': 2, '7': 3, '8': 4, '10': 5, '11': 6, '13': 7,
          '42': 8, '44': 9, '45': 10, '47': 11, '48': 12, '50': 13, '51': 14, '53': 15}
R_CX = XR + PIN_L + 80          # resistor centre: pin 1 at R_CX-10, pin 2 at R_CX+10; the SDRAM-Dn label rides the
                                # 70-unit wire from the DQ pin to pin 1, so the net keeps its name
LABEL_X = R_CX + 20
CAPTION = [(XL, YBOT - PIN_L - 50, 'R119-R134: 22 ohm 0201 (RC0201FR-0722RL) DQ series resistors,'),
           (XL, YBOT - PIN_L - 60, 'pin 1 on U3 (SDRAM-Dn), pin 2 to U1 (Dn). Placement is SI-critical:'),
           (XL, YBOT - PIN_L - 70, 'see NOTE and docs/dq_series_resistors.md.'),
           (XL, YBOT - PIN_L - 85, 'C3-C9: 0.1 uF, one on each supply pin above; the ground pin below'),
           (XL, YBOT - PIN_L - 95, 'is the one it faces in the TSOP (pin 55-n).')]
WIRE = 'LineWidth=1|Color=32768'
SD_FRAME_CORNER_X, SD_FRAME_BOTTOM, SD_FRAME_TOP = 500, 600, 755
X3_LINES = [(70, 590, '2026-09-06: X3 is now the Hirose DM3D-SF push-pull socket'),
            (70, 580, '(HRS 609-0025-8), DM3 catalog p9. Same 8-contact pinout;'),
            (70, 570, 'shell pads G1-G4 to GND; card-detect switch A/B (closed with'),
            (70, 560, 'card) left open. Needs its own footprint on the PCB.')]


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


def set_f(b, k, v):
    """Write a coordinate with its _Frac (1e-5) part; drops a stale _Frac."""
    whole = math.floor(v + 1e-9)
    frac = int(round((v - whole) * 100000))
    if frac >= 100000:
        whole, frac = whole + 1, 0
    b = set_field(b, k, str(whole))
    if frac:
        b = set_field(b, k + '_Frac', str(frac))
    elif field(b, k + '_Frac') is not None:
        b = b.replace(b'|' + (k + '_Frac=').encode() + field(b, k + '_Frac').encode(), b'')
    return b


def uid():
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(8))


def hot_end(b):
    L = num(b, 'PinLength') or 0
    rot = (num(b, 'PinConglomerate') or 0) & 3
    dx, dy = [(1, 0), (0, 1), (-1, 0), (0, -1)][rot]
    return fval(b, 'Location.X') + dx * L, fval(b, 'Location.Y') + dy * L


def rot(p, c, q):
    """Rotate point p about c by q quarter-turns CCW."""
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


def main(src, dst):
    import hashlib
    if hashlib.md5(open(src, 'rb').read()).hexdigest() != SRC_MD5:
        raise SystemExit('%s is not the expected sheet 3 (md5 %s)' % (src, SRC_MD5))
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

    # ---- U3 pin parts --------------------------------------------------------------------------------------------
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
        u3[field(R[pins[0]][1], 'Designator')] = dict(root=i, pin=pins[0], gate=gate[0])
    assert len(u3) == 55
    old_hot = {d: hot_end(R[v['pin']][1]) for d, v in u3.items() if d != 'part1'}

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
    for d, p in old_hot.items():
        ws, objs = network(p)
        drop |= ws
        drop |= {i for i, kind, t in objs}
        names = {t for i, kind, t in objs if kind == '25'}
        label[d] = names.pop() if names else None

    # ---- caps C3-C9: which supply pin's row each sits on, and which cap pin is the GND side --------------------------
    caps = {}
    for i in comps:
        ref = des.get(i)
        if ref not in ('C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9'):
            continue
        cpins = {field(R[k][1], 'Designator'): hot_end(R[k][1]) for k in kids[i] if field(R[k][1], 'RECORD') == '2'}
        row = [d for d in SUPPLY if abs(old_hot[d][1] - cpins['1'][1]) < 1e-6]
        assert len(row) == 1, (ref, cpins, row)
        gnd_side = '1' if cpins['1'][0] < cpins['2'][0] else '2'
        assert gnd_side == '1', (ref, 'pin 2 is on the ground side; this layout puts pin 1 there')
        caps[row[0]] = dict(root=i, ref=ref, centre=((cpins['1'][0] + cpins['2'][0]) / 2, cpins['1'][1]))
    assert len(caps) == 7, caps.keys()
    ground_of = {s: str(55 - int(s)) for s in SUPPLY}
    for s in SUPPLY:                                   # the old rows paired supply and ground pins at the same y
        assert abs(old_hot[s][1] - old_hot[ground_of[s]][1]) < 1e-6, (s, ground_of[s])

    # ---- resistors R119-R134 ----------------------------------------------------------------------------------
    res = {}
    for i in comps:
        ref = des.get(i) or ''
        if ref.startswith('R') and ref[1:].isdigit() and 119 <= int(ref[1:]) <= 134:
            pins = {field(R[k][1], 'Designator'): hot_end(R[k][1]) for k in kids[i] if field(R[k][1], 'RECORD') == '2'}
            assert pins['1'][0] < pins['2'][0], ref
            res[int(ref[1:]) - 119] = dict(root=i, pins=pins)
            for p in pins.values():
                ws, objs = network(p)
                drop |= ws
                drop |= {k for k, kind, t in objs}
    assert len(res) == 16

    # ---- move the U3 pin parts --------------------------------------------------------------------------------
    plan = {}
    for d, y in RIGHT:
        plan[d] = ((XR + PIN_L, y), 2)
    for d, y in LEFT:
        plan[d] = ((XL - PIN_L, y), 0)
    for k, s in enumerate(SUPPLY):
        plan[s] = ((COL_X[k], YTOP + PIN_L), 3)
        plan[ground_of[s]] = ((COL_X[k], YBOT - PIN_L), 1)
    assert sorted(plan, key=int) == [str(n) for n in range(1, 55)]
    for d, (h_new, o_new) in plan.items():
        v = u3[d]
        o_old = num(R[v['root']][1], 'Orientation') or 0
        q = (o_new - o_old) % 4
        h_old = old_hot[d]
        move_part(R, v['root'], kids[v['root']], lambda p, h_old=h_old, h_new=h_new, q=q:
                  tuple(a + b for a, b in zip(h_new, rot(p, h_old, q))))
        b = R[v['root']][1]
        R[v['root']][1] = set_field(b, 'Orientation', str(o_new)) if o_new else \
            b.replace(b'|Orientation=' + (field(b, 'Orientation') or '').encode(), b'')
        for k in kids[v['root']]:                       # every pin of this part record turns with it
            pb = R[k][1]
            if field(pb, 'RECORD') == '2':
                c = num(pb, 'PinConglomerate') or 0
                R[k][1] = set_field(pb, 'PinConglomerate', str((c & ~3) | (((c & 3) + q) % 4)))
        assert hot_end(R[v['pin']][1]) == h_new, (d, hot_end(R[v['pin']][1]), h_new)
        # the visible pin name, inside the box
        g = R[v['gate']][1]
        hx, hy = h_new
        pos, orient, just = {0: ((hx + 22.5, hy - 4), 0, 0), 2: ((hx - 22.5, hy + 4), 0, 8),
                             3: ((hx + 4, hy - 22), 1, 2), 1: ((hx + 4, hy + 22), 1, 0)}[o_new]
        g = set_f(set_f(g, 'Location.X', pos[0]), 'Location.Y', pos[1])
        g = set_field(g, 'Orientation', str(orient)) if orient else g.replace(
            b'|Orientation=' + (field(g, 'Orientation') or '').encode(), b'')
        g = set_field(g, 'Justification', str(just)) if just else g.replace(
            b'|Justification=' + (field(g, 'Justification') or '').encode(), b'')
        R[v['gate']][1] = g

    # U3 designator and comment in the middle of the box
    p1 = u3['part1']
    for k in kids[p1]:
        b = R[k][1]
        if field(b, 'IsHidden') == 'T' or fval(b, 'Location.X') is None:
            continue
        if field(b, 'Name') == 'PART' and field(b, 'Text') == 'U3':
            R[k][1] = set_f(set_f(b, 'Location.X', (XL + XR) / 2 - 7), 'Location.Y', (YTOP + YBOT) / 2 + 6)
        elif field(b, 'Name') == 'Comment':
            R[k][1] = set_f(set_f(b, 'Location.X', (XL + XR) / 2 - 53), 'Location.Y', (YTOP + YBOT) / 2 - 8)

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

    # right edge: DQ -> resistor -> Dn label; LDQM / UDQM -> label
    for d, y in RIGHT:
        if d in DQ_BIT:
            bit = DQ_BIT[d]
            assert label[d] == 'SDRAM-D%d' % bit, (d, label[d])
            r = res[bit]
            c_old = ((r['pins']['1'][0] + r['pins']['2'][0]) / 2, r['pins']['1'][1])
            dx, dy = R_CX - c_old[0], y - c_old[1]
            move_part(R, r['root'], kids[r['root']], lambda p, dx=dx, dy=dy: (p[0] + dx, p[1] + dy))
            for k in kids[r['root']]:
                if field(R[k][1], 'Name') == 'Comment' and field(R[k][1], 'RECORD') == '41':
                    R[k][1] = set_field(R[k][1], 'IsHidden', 'T')
                if field(R[k][1], 'RECORD') == '34':          # designator 4 units left: clear of the Dn label
                    R[k][1] = set_f(R[k][1], 'Location.X', fval(R[k][1], 'Location.X') - 4)
            wire((XR + PIN_L, y), (R_CX - 10, y))
            netlabel((XR + PIN_L + 6, y), 'SDRAM-D%d' % bit)
            wire((R_CX + 10, y), (LABEL_X, y))
            netlabel((LABEL_X, y), 'D%d' % bit)
        else:
            wire((XR + PIN_L, y), (LABEL_X, y))
            netlabel((LABEL_X, y), label[d])
    # left edge: stub + label (NC stays open)
    for d, y in LEFT:
        if label[d] is None:
            assert d == '40', d
            continue
        wire((XL - PIN_L, y), (XL - PIN_L - 10, y))
        netlabel((XL - PIN_L - 10, y), label[d], 2)
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
    # one VCC3V3 rail over the seven supply columns, one port at its east end (seven ports' texts ran together)
    wire((COL_X[0], VCC_Y), (COL_X[-1], VCC_Y))
    wire((COL_X[-1], VCC_Y), (COL_X[-1], VCC_Y + 10))
    junction((COL_X[-1], VCC_Y))
    port((COL_X[-1], VCC_Y + 10), 'VCC3V3', 2, 1)

    # ---- notes ------------------------------------------------------------------------------------------------
    for i, (h, b) in enumerate(R):
        if field(b, 'RECORD') == '4' and owner(b) is None:
            t = field(b, 'Text') or ''
            if t.startswith('U3 DQ SERIES RESISTORS') or t.startswith('Placement is SI-critical'):
                drop.add(i)
            if t.startswith('2026-09-06: X3 is now') or t.startswith('shell pads G1-G4'):
                drop.add(i)
        if field(b, 'RECORD') == '28' and (field(b, 'Text') or '').startswith('microSD runs the NATIVE'):
            R[i][1] = set_field(b, 'Corner.X', str(SD_FRAME_CORNER_X)).replace(
                b'|Corner.X_Frac=' + (field(b, 'Corner.X_Frac') or '').encode(), b'')
            R[i][1] = set_field(R[i][1], 'Corner.Y', str(SD_FRAME_TOP)).replace(
                b'|Corner.Y_Frac=' + (field(R[i][1], 'Corner.Y_Frac') or '').encode(), b'')
            R[i][1] = set_field(R[i][1], 'Location.Y', str(SD_FRAME_BOTTOM)).replace(
                b'|Location.Y_Frac=' + (field(R[i][1], 'Location.Y_Frac') or '').encode(), b'')
    for x, y, t in CAPTION + X3_LINES:
        new.append('|RECORD=4|OwnerPartId=-1|Location.X=%d|Location.Y=%d|Color=8421504|FontID=3|Text=%s|UniqueID=%s'
                   % (x, y, t, uid()))

    for body in new:
        R.append([bytes(4), body.encode('latin-1') + b'\x00'])
    R = delete(R, drop)
    R[0][1] = set_field(R[0][1], 'Weight', str(len(R) - 1))
    blob = join(R)
    if os.path.abspath(dst) != os.path.abspath(src):
        import shutil
        shutil.copyfile(src, dst)
    write_stream(dst, blob)
    assert read_stream(dst) == blob
    print('%s: %d records -> %d (deleted %d, added %d)' % (os.path.basename(dst), len(split(raw)), len(R), len(drop), len(new)))
    after = net_map(split(read_stream(dst)))
    report(before, after)


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
