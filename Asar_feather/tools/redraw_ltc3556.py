"""Redraw the LTC3556 power section of sheet 1 in the Digilent Cmod A7 style (2026-11-10, user request; Zulu A7 Fab B
and Asar Feather). Same circuit, same nets, same component UniqueIDs as apply_ltc3556.py produced -- only the drawing
changes, so the PCB is untouched.

U8's pins are regrouped by function: VIN1/VIN2/VIN3 on top (one VU bus with the three input capacitors), the PowerPath /
charger / control pins on the left, and each converter's SW and FB pins on the right with room between them, where the
converter is drawn wired: SW -> inductor -> output rail, output capacitor to GND, feed-forward capacitor and divider top
between the rail and the FB row, divider bottom from the FB row to GND (Buck1, Buck2); the buck-boost has its inductor
across SWAB3/SWCD3 and its Type III network between the VOUT3, FB3 and VC3 rows. Every named net keeps a net label.

    python tools/redraw_ltc3556.py <pre-swap sheet-1 backup> <current sheet-1 SchDoc> fabb|asar <out SchDoc>

The pre-swap backup is the starting point (the old power section is deleted from it as apply_ltc3556.py does, over a
larger area); the current sheet supplies every UniqueID (component and pin) of the LTC3556 block, and the X1 symbol as
tidied by tidy_x1.py. Close the sheet in Altium before overwriting it.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import apply_ltc3556 as A  # noqa: E402
from schdoc import del_field, field, join, owner, read_stream, set_field, split, write_stream  # noqa: E402
import sch_netlist  # noqa: E402

num, setxy, pin_end, on_seg, wire_pts, inbox = A.num, A.setxy, A.pin_end, A.on_seg, A.wire_pts, A.inbox

# deletion area: the whole power section, minus a hole round LD5/R78 (the VCC3V3 LED stays as drawn)
BOXES = [(40, 165, 815, 1056), (815, 390, 895, 1056), (815, 165, 895, 255)]
KEEP = {'X1', 'X4', 'R26', 'R27', 'R28', 'LD5', 'R78'}

# ---- U8 symbol: body x 360..500, y 440..1020
X0, X1B, YB, YT = 360, 500, 380, 1020
#        pin  name        side pos (y for L/R, x for T/B)
PINS = [('5', 'VIN1', 'T', 390), ('18', 'VIN2', 'T', 430), ('11', 'VIN3', 'T', 470),
        ('25', 'VBUS', 'L', 1000), ('26', 'SW', 'L', 930), ('24', 'VOUT', 'L', 890), ('23', 'BAT', 'L', 830),
        ('1', 'LDO3V3', 'L', 790), ('21', 'CHRG', 'L', 760), ('15', 'PGOODALL', 'L', 720), ('2', 'CLPROG', 'L', 620),
        ('20', 'PROG', 'L', 540), ('28', 'ENALL', 'L', 470), ('3', 'NTC', 'L', 450), ('27', 'SEQ', 'L', 440),
        ('10', 'DVCC', 'L', 430), ('13', 'SCL', 'L', 420), ('16', 'SDA', 'L', 410), ('22', 'GATE', 'L', 390),
        ('4', 'SW1', 'R', 1000), ('6', 'FB1', 'R', 960), ('19', 'SW2', 'R', 880), ('17', 'FB2', 'R', 840),
        ('9', 'SWAB3', 'R', 740), ('14', 'SWCD3', 'R', 720), ('12', 'VOUT3', 'R', 680), ('7', 'FB3', 'R', 620),
        ('8', 'VC3', 'R', 520),
        ('29', 'GND', 'B', 430)]
ELEC = {p[0]: p[3] for p in A.U8_PINS}
CONG = {'L': 58, 'R': 56, 'T': 57, 'B': 59}            # orientation bits: 0 right, 1 up, 2 left, 3 down; 0x38 = show
NOTE_XY = (60, 310)
X4_AT = (200, 210)                                     # X4 (battery JST) moves out of the converters' way


def rot_pt(x, y, ox, oy, q):
    for _ in range(q % 4):
        x, y = ox - (y - oy), oy + (x - ox)
    return x, y


def rotate_rec(b, ox, oy, q, root=False):
    """Rotate one record of a component subtree by q quarter turns (CCW) about (ox, oy)."""
    if q % 4 == 0:
        return b
    for kx, ky in [('Location.X', 'Location.Y'), ('Corner.X', 'Corner.Y')] + [('X%d' % k, 'Y%d' % k) for k in range(1, 9)]:
        if field(b, kx) is None and field(b, kx + '_Frac') is None:
            continue
        x, y = rot_pt(num(b, kx), num(b, ky), ox, oy, q)
        b = setxy(b, kx, ky, round(x), round(y))
    r = field(b, 'RECORD')
    if r == '2':
        c = int(field(b, 'PinConglomerate') or 0)
        b = set_field(b, 'PinConglomerate', str((c & ~3) | (((c & 3) + q) % 4)))
    elif r == '12':
        for k in ('StartAngle', 'EndAngle'):
            a = float(field(b, k) or 0) + 90 * q
            b = set_field(b, k, '%.3f' % (a % 360))
    elif r in ('34', '41') and q % 2:
        o = int(field(b, 'Orientation') or 0)
        b = set_field(b, 'Orientation', str(1 - (o % 2)))
    if root:
        o = int(field(b, 'Orientation') or 0)
        b = set_field(b, 'Orientation', str((o + q) % 4))
    return b


def main():
    backup, current, board, out = sys.argv[1:5]
    assert board in ('fabb', 'asar')
    nets_u8 = dict(A.U8_NETS)
    nets_u8['28'] = 'VU' if board == 'fabb' else 'EN'
    S = A.Sheet(backup)
    C = A.Sheet(current)
    S.taken |= C.taken                                    # same seeded rng as apply_ltc3556: never reuse its UIDs
    old_nets = sch_netlist.build(os.path.dirname(os.path.abspath(current)))
    pin_net = {p: n for n, pins in old_nets.items() for p in pins}

    # UniqueIDs of the LTC3556 block, from the current sheet (component and per-pin)
    # parts whose symbol comes from somewhere other than the current sheet's part of the same designator (2026-11-10:
    # U7 SC189A takes VCC1V0 back from LTC3556 Buck1; L3/C149 return to their SC189 values; L9/C167/C168 are new)
    SRC = {'U7': ('backup', 'U7'), 'L3': ('backup', 'L3'), 'C149': ('backup', 'C149'),
           'L9': ('current', 'L2'), 'C167': ('current', 'C161'), 'C168': ('current', 'C147')}
    cur_uid, cur_pin_uid = {}, {}
    for des in [p[0] for p in A.PARTS] + ['LD3', 'LD4', 'U8']:
        if des not in C.byname:
            continue
        i = C.byname[des]
        cur_uid[des] = field(C.recs[i][1], 'UniqueID')
        for k in C.sub(i):
            b = C.recs[k][1]
            if field(b, 'RECORD') == '41' and field(b, 'Name') == 'PinUniqueId':
                pb = C.recs[owner(b)][1]
                cur_pin_uid[(des, field(pb, 'Designator'))] = field(b, 'Text')
    # templates from the CURRENT sheet (already the LTC3556 parts, values, models and the tidied X1)
    T = {d: C.template(d) for d in [p[0] for p in A.PARTS] + ['LD3', 'LD4', 'U8'] if d not in SRC}
    for d, (where, src) in SRC.items():
        T[d] = (S if where == 'backup' else C).template(src)
    if 'U7' not in cur_uid:
        cur_uid['U7'] = field(S.recs[S.byname['U7']][1], 'UniqueID')     # the SC189A's own UID from before the swap
    spec = {p[0]: p for p in A.PARTS}
    x1_cur = C.template('X1')
    top_t = {}
    for h, b in C.recs:
        r = field(b, 'RECORD')
        if owner(b) in (None, 0) and r in ('27', '25', '22', '4', '29'):
            if r == '27' and field(b, 'LocationCount') != '2':
                continue
            if r == '25' and (field(b, 'Orientation') or field(b, 'Justification')):
                continue
            top_t.setdefault(r, (h, b))
        if owner(b) in (None, 0) and r == '17' and field(b, 'Text') == 'GND' and field(b, 'Orientation') == '3':
            top_t.setdefault('17', (h, b))
    assert set(top_t) == {'27', '25', '22', '4', '29', '17'}, top_t.keys()

    # ---- delete the old power section from the backup (as apply_ltc3556, over BOXES)
    dele = set()
    for i, (h, b) in enumerate(S.recs):
        r = field(b, 'RECORD')
        if r == '1':
            d = S.des.get(i)
            x, y = num(b, 'Location.X'), num(b, 'Location.Y')
            if d in A.DELETE or d == 'U8' or d in T or (d not in KEEP and any(inbox(x, y, bx) for bx in BOXES)):
                dele |= set(S.sub(i))
        elif owner(b) in (None, 0) and r in ('27', '29', '17', '25', '22', '4', '28'):
            pts = wire_pts(b) if r == '27' else [(num(b, 'Location.X'), num(b, 'Location.Y'))]
            if any(inbox(x, y, bx) for x, y in pts for bx in BOXES):
                dele.add(i)
    gone = sorted({S.des[i] for i in dele if i in S.des})
    S.delete(dele)

    # X1 takes the tidied symbol and the sheet wiring round it from the current sheet: replace the X1 subtree and every
    # top-level object in X1's neighbourhood (x 120..300, y 1056..1180) by the current sheet's
    X1BOX = (120, 1056, 300, 1180)
    dele = set(S.sub(S.byname['X1']))
    for i, (h, b) in enumerate(S.recs):
        if owner(b) in (None, 0) and field(b, 'RECORD') in ('27', '29', '17', '25', '22'):
            pts = wire_pts(b) if field(b, 'RECORD') == '27' else [(num(b, 'Location.X'), num(b, 'Location.Y'))]
            if all(inbox(x, y, X1BOX) for x, y in pts):
                dele.add(i)
    S.delete(dele)
    x1_uid = field(x1_cur[0][1], 'UniqueID')
    base = len(S.recs)
    for k, (h, b, o) in enumerate(x1_cur):
        if o is not None:
            b = set_field(b, 'OwnerIndex', str(base + o - 1))
        else:
            b = set_field(b, 'IndexInSheet', S.nxt())
        S.recs.append([h, b])
    for h, b in C.recs:
        if owner(b) in (None, 0) and field(b, 'RECORD') in ('27', '29', '17', '25', '22'):
            pts = wire_pts(b) if field(b, 'RECORD') == '27' else [(num(b, 'Location.X'), num(b, 'Location.Y'))]
            if all(inbox(x, y, X1BOX) for x, y in pts):
                S.recs.append([h, set_field(b, 'IndexInSheet', S.nxt())])
    S.reindex()

    # X4 moves out of the way (its wiring was inside BOXES and is gone; its pins get labels below)
    i4 = S.byname['X4']
    b4 = S.recs[i4][1]
    dx, dy = X4_AT[0] - num(b4, 'Location.X'), X4_AT[1] - num(b4, 'Location.Y')
    for k in S.sub(i4):
        S.recs[k][1] = A.shift(S.recs[k][1], dx, dy)

    # prune dangling wire stubs, then label surviving pins that lost their connection (as apply_ltc3556)
    def anchors():
        pts, segs = set(), []
        for i, (h, b) in enumerate(S.recs):
            r = field(b, 'RECORD')
            if r == '2':
                pts.add(pin_end(b))
            elif owner(b) in (None, 0) and r in ('25', '17', '29'):
                pts.add((num(b, 'Location.X'), num(b, 'Location.Y')))
            elif owner(b) in (None, 0) and r == '27':
                segs.append((i, wire_pts(b)))
        return pts, segs
    while True:
        pts, segs = anchors()
        kill = set()
        for i, w in segs:
            for e in (w[0], w[-1]):
                if not (e in pts or any(j != i and any(on_seg(e, a, c) for a, c in zip(v, v[1:])) for j, v in segs)):
                    kill.add(i)
        if not kill:
            break
        S.delete(kill)
    pts, segs = anchors()
    orphans = []
    for i, (h, b) in enumerate(S.recs):
        if field(b, 'RECORD') != '2':
            continue
        d = S.des.get(owner(b))
        e = pin_end(b)
        net = pin_net.get((d, field(b, 'Designator')))
        if not net or net.startswith('N$') or d in T:
            continue
        connected = any(any(on_seg(e, a, c) for a, c in zip(w, w[1:])) for j, w in segs) or \
            any((num(bb, 'Location.X'), num(bb, 'Location.Y')) == e for hh, bb in S.recs
                if owner(bb) in (None, 0) and field(bb, 'RECORD') in ('25', '17'))
        if not connected:
            orphans.append((e, net, d, field(b, 'Designator')))

    # ---- drawing primitives
    def label(x, y, text, just=None):
        def ed(b):
            b = setxy(del_field(del_field(b, 'Orientation'), 'Justification'), 'Location.X', 'Location.Y', x, y)
            b = set_field(b, 'Text', text)
            return set_field(b, 'Justification', str(just)) if just else b
        S.add_simple(top_t['25'], ed)

    def wire(*p):
        for a, c in zip(p, p[1:]):
            def ed(b, a=a, c=c):
                for k in (1, 2):
                    b = del_field(del_field(b, 'X%d_Frac' % k), 'Y%d_Frac' % k)
                return setxy(setxy(b, 'X1', 'Y1', *a), 'X2', 'Y2', *c)
            S.add_simple(top_t['27'], ed)

    def junction(x, y):
        S.add_simple(top_t['29'], lambda b: setxy(b, 'Location.X', 'Location.Y', x, y))

    def gnd(x, y):
        S.add_simple(top_t['17'], lambda b: setxy(b, 'Location.X', 'Location.Y', x, y))

    def noerc(x, y):
        S.add_simple(top_t['22'], lambda b: setxy(b, 'Location.X', 'Location.Y', x, y))

    def place(des, cx, cy, want):
        """Place des centred at (cx, cy); want = {pin: 'top'|'bottom'|'left'|'right'} picks the rotation. Returns
        {pin designator: pin end}."""
        tmpl = T[des]
        b0 = tmpl[0][1]
        ox, oy = num(b0, 'Location.X'), num(b0, 'Location.Y')
        pins0 = {field(b, 'Designator'): pin_end(b) for h, b, o in tmpl if field(b, 'RECORD') == '2'}
        mx = sum(p[0] for p in pins0.values()) / len(pins0)
        my = sum(p[1] for p in pins0.values()) / len(pins0)
        best = None
        for q in range(4):
            ok = True
            for pd, side in want.items():
                x, y = rot_pt(pins0[pd][0], pins0[pd][1], mx, my, q)
                dxp, dyp = x - mx, y - my
                if abs(dyp) >= abs(dxp):
                    got = 'top' if dyp > 0 else 'bottom'
                else:
                    got = 'right' if dxp > 0 else 'left'
                ok &= got == side
            if ok:
                best = q
                break
        assert best is not None, (des, want)
        base = len(S.recs)
        fresh = des in SRC
        for k, (h, b, o) in enumerate(tmpl):
            b = rotate_rec(b, mx, my, best, root=(k == 0))
            b = A.shift(b, cx - mx, cy - my)
            if fresh:
                if k and field(b, 'UniqueID'):
                    b = set_field(b, 'UniqueID', S.uid())
                if field(b, 'RECORD') == '41' and field(b, 'Name') == 'PinUniqueId':
                    b = set_field(b, 'Text', S.uid())
                if field(b, 'RECORD') == '34':
                    b = set_field(b, 'Text', des)
            # values, MPNs and specs always follow the parts list (apply_ltc3556.PARTS is the master)
            if des in spec and field(b, 'RECORD') == '41' and field(b, 'Name') in ('SPEC', 'Comment', 'MANF#'):
                b = set_field(b, 'Text', {'SPEC': spec[des][4], 'Comment': spec[des][2],
                                          'MANF#': spec[des][3]}[field(b, 'Name')])
            if k == 0:
                b = set_field(set_field(b, 'IndexInSheet', S.nxt()), 'UniqueID', cur_uid.get(des) or S.uid())
            if o is not None:
                b = set_field(b, 'OwnerIndex', str(base + o - 1))
            S.recs.append([h, b])
        S.reindex()
        ends = {}
        for k in S.sub(base):
            b = S.recs[k][1]
            if field(b, 'RECORD') == '2':
                e = pin_end(b)
                ends[field(b, 'Designator')] = (round(e[0]), round(e[1]))
        return ends

    # ---- U8: rebuild its subtree from the current sheet's U8 with the new pin arrangement and body
    tmpl = T['U8']
    pos = {p[0]: p for p in PINS}
    base = len(S.recs)
    for k, (h, b, o) in enumerate(tmpl):
        r = field(b, 'RECORD')
        if k == 0:
            b = set_field(setxy(b, 'Location.X', 'Location.Y', X0, YB), 'IndexInSheet', S.nxt())
        elif r == '2':
            pd = field(b, 'Designator')
            _, name, side, at = pos[pd]
            px, py = {'L': (X0, at), 'R': (X1B, at), 'T': (at, YT), 'B': (at, YB)}[side]
            b = setxy(b, 'Location.X', 'Location.Y', px, py)
            b = set_field(set_field(b, 'PinConglomerate', str(CONG[side])), 'PinLength', '30' if side != 'B' else '20')
        elif r == '41' and field(b, 'Name') == 'PinUniqueId':
            pb = tmpl[o][1]
            pd = field(pb, 'Designator')
            _, name, side, at = pos[pd]
            px, py = {'L': (X0, at), 'R': (X1B, at), 'T': (at, YT), 'B': (at, YB)}[side]
            b = setxy(b, 'Location.X', 'Location.Y', px, py)
        elif r == '6':
            seg = [(X0, YB, X1B, YB), (X1B, YB, X1B, YT), (X1B, YT, X0, YT), (X0, YT, X0, YB)][
                [kk for kk, (hh, bb, oo) in enumerate(tmpl) if field(bb, 'RECORD') == '6'].index(k)]
            for kk, v in zip(('X1', 'Y1', 'X2', 'Y2'), seg):
                b = set_field(del_field(b, kk + '_Frac'), kk, str(v))
        elif r == '34':
            b = setxy(b, 'Location.X', 'Location.Y', X1B + 10, YB - 14)
        elif r == '41' and field(b, 'Name') == 'PartName':
            b = set_field(setxy(b, 'Location.X', 'Location.Y', X1B + 10, YB - 26), 'Justification', '0')
        elif r == '41' and field(b, 'Location.X') is not None and field(b, 'IsHidden') != 'T':
            b = setxy(b, 'Location.X', 'Location.Y', X1B + 10, YB - 38)
        if o is not None:
            b = set_field(b, 'OwnerIndex', str(base + o - 1))
        S.recs.append([h, b])
    S.reindex()
    u8 = {}
    for k in S.sub(base):
        b = S.recs[k][1]
        if field(b, 'RECORD') == '2':
            e = pin_end(b)
            u8[field(b, 'Designator')] = (round(e[0]), round(e[1]))
    assert len(u8) == 29

    V = lambda d, x, y, top, bot: place(d, x, y, {top: 'top', bot: 'bottom'})          # noqa: E731
    H = lambda d, x, y, left, right: place(d, x, y, {left: 'left', right: 'right'})    # noqa: E731

    def pinmap(des):
        p = [x for x in A.PARTS if x[0] == des][0]
        return p[6], p[7]                                  # pin 1 net, pin 2 net

    def vpart(des, x, ycen, topnet):
        n1, n2 = pinmap(des)
        top, bot = ('1', '2') if n1 == topnet else ('2', '1')
        e = V(des, x, ycen, top, bot)
        return e[top], e[bot]

    def hpart(des, xcen, y, leftnet):
        n1, n2 = pinmap(des)
        left, right = ('1', '2') if n1 == leftnet else ('2', '1')
        e = H(des, xcen, y, left, right)
        return e[left], e[right]

    def hang(des, x, yrow, topnet, cy=None):
        """A two-pin part hanging below a horizontal row at x: top pin wired up to the row, bottom pin to GND.
        Returns the bottom pin end."""
        t, bt = vpart(des, x, (yrow - 20) if cy is None else cy, topnet)
        wire((x, yrow), t)
        return bt

    # ---- top: VIN1/VIN2/VIN3 on one VU bus with their input capacitors
    BUS = 1100
    vin = [u8['5'], u8['18'], u8['11']]                     # x 390, 430, 470 at y 1050
    for e in vin:
        wire(e, (e[0], BUS))
    for des, x in (('C167', 410), ('C160', 450), ('C148', 490)):
        t, bt = vpart(des, x, 1080, 'VU')                     # pins at 1090 / 1070
        wire(t, (x, BUS))
        gnd(*bt)
    # ---- U7 SC189A (fixed 1.0 V, 1.5 A) for VCC1V0, on the same VU bus, enabled with the LTC3556 (ENALL net)
    e7 = place('U7', 670, 1110, {'1': 'left', '5': 'right'})  # VIN (600,1130), EN (600,1110), GND (670,1070)
    t, bt = vpart('C149', 520, BUS - 20, 'VU')                # SC189A input capacitor, hangs from the bus
    wire(t, (520, BUS))
    gnd(*bt)
    xs = [390, 410, 430, 450, 470, 490, 520, 540]
    wire(*[(x, BUS) for x in xs], (540, e7['1'][1]), e7['1'])
    for x in xs[1:-1]:
        junction(x, BUS)
    label(390, BUS, 'VU', 2)
    if nets_u8['28'] == 'VU':
        wire(e7['3'], (e7['3'][0] - 15, e7['3'][1]), (e7['3'][0] - 15, e7['1'][1]))
        junction(e7['3'][0] - 15, e7['1'][1])
    else:
        wire(e7['3'], (e7['3'][0] - 30, e7['3'][1]))
        label(e7['3'][0] - 30, e7['3'][1], nets_u8['28'], 2)
    gnd(*e7['2'])
    l3 = H('L3', e7['5'][0] + 30, e7['5'][1], '1', '2')      # pin 1 = LX, pin 2 = VCC1V0
    wire(e7['5'], l3['1'])
    nx = l3['2'][0] + 20
    wire(l3['2'], (nx, l3['2'][1]), (nx + 20, l3['2'][1]), (nx + 40, l3['2'][1]))
    wire(e7['4'], (nx, e7['4'][1]), (nx, l3['2'][1]))
    junction(nx, l3['2'][1])
    junction(nx + 20, l3['2'][1])
    gnd(*hang('C84', nx + 20, l3['2'][1], 'VCC1V0'))
    label(nx + 40, l3['2'][1], 'VCC1V0')

    # ---- left: PowerPath, charger, control
    # VBUS
    e = u8['25']
    wire(e, (260, e[1]), (200, e[1]))
    junction(260, e[1])
    label(200, e[1], 'USB5V0', 2)
    gnd(*hang('C150', 260, e[1], 'USB5V0'))
    # SW -> L8 -> VOUT (VU)
    sw, vo = u8['26'], u8['24']
    l8 = H('L8', 270, sw[1], '2', '1')                        # pin 1 (PWR_SW) on the right, toward the SW pin
    wire(sw, l8['1'])
    label(295, sw[1], 'PWR_SW')
    wire(l8['2'], (230, sw[1]), (230, vo[1]))
    wire(vo, (230, vo[1]), (200, vo[1]), (160, vo[1]), (120, vo[1]))
    for x in (230, 200, 160):
        junction(x, vo[1])
    label(120, vo[1], 'VU', 2)
    gnd(*hang('C147', 200, vo[1], 'VU'))
    gnd(*hang('C78', 160, vo[1], 'VU'))
    # BAT
    e = u8['23']
    wire(e, (200, e[1]), (120, e[1]))
    junction(200, e[1])
    label(120, e[1], 'VBATT', 2)
    gnd(*hang('C151', 200, e[1], 'VBATT'))
    # LDO3V3 (tied to VOUT)
    e = u8['1']
    wire(e, (290, e[1]))
    label(290, e[1], 'VU', 2)
    # CHRG: VU -> R108 -> LD4 -> CHRG
    e = u8['21']
    ld4 = H('LD4', 250, e[1], 'A', 'K')                       # A 230, K 270
    wire(e, ld4['K'])
    label(275, e[1], 'PWR_CHRG')
    r108l, r108r = hpart('R108', 180, e[1], 'VU')             # 170 / 190
    wire(r108r, ld4['A'])
    label(195, e[1], 'LD4_A')
    wire(r108l, (150, e[1]))
    label(150, e[1], 'VU', 2)
    # PGOODALL: VCC3V3 -> R107 -> node -> LD3 -> GND
    e = u8['15']
    r107l, r107r = hpart('R107', 200, e[1], 'VCC3V3')         # 190 / 210
    wire(e, (300, e[1]), r107r)
    junction(300, e[1])
    label(215, e[1], 'PWR_PGOODALL')
    ld3 = V('LD3', 300, e[1] - 30, 'A', 'K')
    wire((300, e[1]), ld3['A'])
    gnd(*ld3['K'])
    wire(r107l, (160, e[1]))
    label(160, e[1], 'VCC3V3', 2)
    # CLPROG: R103 + C161 to GND
    e = u8['2']
    wire(e, (300, e[1]), (260, e[1]), (230, e[1]))
    junction(300, e[1])
    junction(260, e[1])
    label(230, e[1], 'PWR_CLPROG', 2)
    gnd(*hang('R103', 300, e[1], 'PWR_CLPROG'))
    gnd(*hang('C161', 260, e[1], 'PWR_CLPROG'))
    # PROG: R102 to GND
    e = u8['20']
    wire(e, (300, e[1]), (260, e[1]))
    junction(300, e[1])
    label(260, e[1], 'PWR_PROG', 2)
    gnd(*hang('R102', 300, e[1], 'PWR_PROG'))
    # ENALL
    e = u8['28']
    wire(e, (290, e[1]))
    label(290, e[1], nets_u8['28'], 2)
    # NTC, SEQ, DVCC, SCL, SDA all to GND on one bus
    ys = [u8[p][1] for p in ('3', '27', '10', '13', '16')]
    for p in ('3', '27', '10', '13', '16'):
        wire(u8[p], (300, u8[p][1]))
    wire(*[(300, y) for y in sorted(ys, reverse=True)])
    for y in sorted(ys)[1:-1]:
        junction(300, y)
    gnd(300, min(ys))
    # GATE: not connected
    noerc(*u8['22'])
    # exposed pad
    gnd(*u8['29'])

    # ---- right: Buck1 (VCC1V0) and Buck2 (VCC1V8), the Cmod layout
    def buck(swp, fbp, L, Cff, Rtop, Rbot, Cout, rail, sw_net, fb_net):
        s, f = u8[swp], u8[fbp]                               # x 530; f is 40 below s
        lp = H(L, 620, s[1], '1', '2')                        # pin 1 = SW net (600, left), pin 2 = rail (640)
        wire(s, lp['1'])
        label(540, s[1], sw_net)
        t, b = vpart(Cff, 670, s[1] - 20, rail)              # pins s-10 / s-30
        wire((670, s[1]), t)
        wire(b, (670, f[1]))
        t, b = vpart(Rtop, 710, s[1] - 20, rail)
        wire((710, s[1]), t)
        wire(b, (710, f[1]))
        gnd(*hang(Cout, 800, s[1], rail))
        wire(lp['2'], (670, s[1]), (710, s[1]), (800, s[1]), (840, s[1]))
        for x in (670, 710, 800):
            junction(x, s[1])
        label(840, s[1], rail)
        t, b = vpart(Rbot, 750, f[1] - 20, fb_net)
        wire(f, (670, f[1]), (710, f[1]), (750, f[1]), t)
        junction(670, f[1])
        junction(710, f[1])
        gnd(*b)
        label(560, f[1], fb_net)
    # Buck1: the sequencing slot -- SW1 -> L9 -> C168, FB1 tied to its own output (0.8 V, no load). With SEQ = GND the
    # LTC3556 starts Buck2 only after Buck1 has started, so 1.8 V follows U7's 1.0 V; PGOODALL still covers 1.8/3.3 V.
    s1, f1 = u8['4'], u8['6']
    l9 = H('L9', 620, s1[1], '1', '2')
    wire(s1, l9['1'])
    label(540, s1[1], 'PWR_SW1')
    wire(l9['2'], (680, s1[1]), (720, s1[1]))
    junction(680, s1[1])
    gnd(*hang('C168', 720, s1[1], 'PWR_FB1'))
    wire(f1, (680, f1[1]), (680, s1[1]))
    label(560, f1[1], 'PWR_FB1')
    buck('19', '17', 'L2', 'C163', 'R113', 'R114', 'C82', 'VCC1V8', 'PWR_SW2', 'PWR_FB2')

    # ---- buck-boost: L1 across SWAB3 / SWCD3, Type III network between VOUT3, FB3 and VC3
    a, c = u8['9'], u8['14']                                  # y 740, 720
    l1 = H('L1', 620, 760, '1', '2')                          # pin 1 = SWAB3 (600), pin 2 = SWCD3 (640)
    wire(a, (l1['1'][0], a[1]), l1['1'])
    wire(l1['2'], (l1['2'][0], c[1]), c)
    label(540, a[1], 'PWR_SWAB3')
    label(540, c[1], 'PWR_SWCD3')
    vo3, fb3, vc3 = u8['12'], u8['7'], u8['8']                # y 680, 620, 520
    # VOUT3 rail: C80 (610) to GND, R115 (650) to FB3, R118 (700) + C166 to FB3
    gnd(*hang('C80', 610, vo3[1], 'VCC3V3'))
    t, b = vpart('R115', 650, 650, 'VCC3V3')                  # pins 660 / 640
    wire((650, vo3[1]), t)
    wire(b, (650, fb3[1]))
    t, b = vpart('R118', 700, 660, 'VCC3V3')                  # pins 670 / 650 (FB3_FF)
    wire((700, vo3[1]), t)
    t2, b2 = vpart('C166', 700, 630, 'PWR_FB3_FF')            # pins 640 / 620
    wire(b, t2)
    label(700, 645, 'PWR_FB3_FF')
    wire(vo3, (610, vo3[1]), (650, vo3[1]), (700, vo3[1]), (760, vo3[1]))
    for x in (610, 650, 700):
        junction(x, vo3[1])
    label(760, vo3[1], 'VCC3V3')
    # FB3 row: R115 (650), C166 (700), R116 (740) to GND, C164 (780) to VC3, C165 (860) up from VC3_RC
    t, b = vpart('R116', 740, 600, 'PWR_FB3')                 # pins 610 / 590
    wire((740, fb3[1]), t)
    gnd(*b)
    t, b = vpart('C164', 780, 570, 'PWR_FB3')                 # pins 580 / 560
    wire((780, fb3[1]), t)
    wire(b, (780, vc3[1]))
    t, b = vpart('R117', 820, 540, 'PWR_VC3_RC')              # pins 550 (VC3_RC) / 530 (VC3)
    wire(b, (820, vc3[1]))
    t2, b2 = vpart('C165', 860, 590, 'PWR_FB3')               # pins 600 (FB3) / 580 (VC3_RC)
    wire(t, (820, 565), (860, 565), b2)
    label(825, 565, 'PWR_VC3_RC')
    wire(t2, (860, fb3[1]))
    wire(fb3, (650, fb3[1]), (700, fb3[1]), (740, fb3[1]), (780, fb3[1]), (860, fb3[1]))
    for x in (650, 700, 740, 780):
        junction(x, fb3[1])
    label(560, fb3[1], 'PWR_FB3')
    wire(vc3, (780, vc3[1]), (820, vc3[1]))
    junction(780, vc3[1])
    label(560, vc3[1], 'PWR_VC3')

    # ---- orphans (X4 and anything else that lost its wiring), notes
    for (x, y), net, d, p in orphans:
        label(x, y, net)
    for k, t in enumerate(A.NOTES):
        S.add_simple(top_t['4'], lambda b, k=k, t=t: set_field(setxy(b, 'Location.X', 'Location.Y', NOTE_XY[0],
                                                                    NOTE_XY[1] - 8 * k), 'Text', t))
    # pin UniqueIds back to the current sheet's
    for k, (h, b) in enumerate(S.recs):
        if field(b, 'RECORD') == '41' and field(b, 'Name') == 'PinUniqueId':
            pb = S.recs[owner(b)][1]
            d = S.des.get(owner(pb))
            if (d, field(pb, 'Designator')) in cur_pin_uid:
                S.recs[k][1] = set_field(b, 'Text', cur_pin_uid[(d, field(pb, 'Designator'))])
    S.recs[0][1] = set_field(S.recs[0][1], 'Weight', str(len(S.recs) - 1))
    import shutil
    if os.path.abspath(out) != os.path.abspath(backup):
        shutil.copyfile(backup, out)
    write_stream(out, join(S.recs))
    print('%s: removed %s; %d orphan pins labelled %s; %d records' % (
        os.path.basename(out), gone, len(orphans), [(d, p, n) for e, n, d, p in orphans], len(S.recs)))


if __name__ == '__main__':
    main()
