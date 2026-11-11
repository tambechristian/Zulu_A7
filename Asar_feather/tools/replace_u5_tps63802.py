"""Replace U5 (Semtech SC189Z, fixed 3.3 V buck, SOT-23-5) with a TI TPS63802 buck-boost (VSON-HR 10, DLA0010A) on
sheet 1 of a Zulu A7 project (2026-11-09, user request: hold VCC3V3 when the LiPo sags below 3.3 V).

Circuit follows the TPS63802 datasheet (SLVSEU9D) Figure 10-1 / Table 10-5:
  VIN(10)  VU            input cap C147 10 uF stays          EN(1)  unchanged wiring (VU on Fab B, EN net on Asar)
  MODE(2)  GND           power-save mode                     AGND(3), GND(8)  GND
  L1(9)    L1 pin 1      L2(7)  L1 pin 2  (L1 becomes 0.47 uH DFE252010F-R47M=P2, same 2520 footprint, 1.0 mm)
  VOUT(6)  VCC3V3        output cap C80 22 uF stays          FB(4)  R109 511k to VCC3V3, R110 91k to GND -> 3.31 V
  PG(5)    unconnected (open drain, optional)
VIN, EN, L1 and VOUT keep the SC189's pin positions so the existing wires stay valid; the wire from L1 pin 2 to the
VCC3V3 junction is cut back to the junction. R109/R110 are clones of R105 (R0402) on the same sheet.

    python tools/replace_u5_tps63802.py <sheet-1 SchDoc>        (close the project in Altium first)
Refuses if U5 is not an SC189 or R109/R110 already exist anywhere in the project.
"""
import glob
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schdoc import del_field, field, join, owner, read_stream, set_field, split, subtree, write_stream  # noqa: E402

FP = 'VSON10-DLA0010A'
LEFT, RIGHT, DOWN = 58, 56, 59                     # PinConglomerate: pin drawn leftwards / rightwards / downwards
#        des  name    x    y   cong  len electrical (0 in, 3 open collector, 4 passive, 7 power)
PINS = [('10', 'VIN', 465, 560, LEFT, 30, 7), ('1', 'EN', 465, 540, LEFT, 30, 0), ('2', 'MODE', 465, 520, LEFT, 30, 0),
        ('9', 'L1', 545, 560, RIGHT, 30, 4), ('7', 'L2', 545, 550, RIGHT, 30, 4), ('6', 'VOUT', 545, 540, RIGHT, 30, 7),
        ('4', 'FB', 545, 530, RIGHT, 30, 0), ('5', 'PG', 545, 510, RIGHT, 30, 3),
        ('8', 'GND', 495, 500, DOWN, 20, 7), ('3', 'AGND', 515, 500, DOWN, 20, 7)]
BODY = (465, 500, 545, 570)
NOTE = ('2026-11-09: U5 SC189Z -> TI TPS63802 buck-boost, holds 3.3 V as the LiPo falls below it; L1 0.47 uH; '
        'R109/R110 511k/91k = 3.31 V; MODE = GND (power save); PG unused')
RES = [  # designator, value, MANF#, centre, pin 2 (top) net, pin 1 (bottom) net
    ('R109', '511K', 'RC0402FR-07511KL', (660, 545),
     'thick film +-1%, 1/16W, 0402 -- TPS63802 FB divider top (R1): VOUT = 0.5 V x (1 + 511k/91k) = 3.31 V'),
    ('R110', '91K', 'RC0402FR-0791KL', (660, 515),
     'thick film +-1%, 1/16W, 0402 -- TPS63802 FB divider bottom (R2); datasheet: R2 must not exceed 100k')]
WIRES = [((575, 550), (625, 550)), ((625, 550), (625, 560)),          # L2 pin -> L1 pin 2
         ((575, 530), (660, 530)),                                      # FB pin -> divider tap
         ((660, 555), (660, 560)), ((660, 535), (660, 530)),           # R109: VCC3V3 wire, tap
         ((660, 525), (660, 530)), ((660, 505), (660, 495)),           # R110: tap, GND port
         ((495, 480), (515, 480)),                                      # GND + AGND pins
         ((435, 520), (425, 520))]                                      # MODE -> GND port
JUNCTIONS = [(660, 560), (660, 530)]
GND_PORTS = [(660, 495), (425, 520)]                                   # the old U5 GND port moves to (505, 480)
PARAMS = {'PartName': 'TPS63802', 'MANF': 'Texas Instruments', 'MANF#': 'TPS63802DLAR', 'Comment': 'TPS63802DLAR'}
L1_PARAMS = {'MANF#': 'DFE252010F-R47M=P2', 'Comment': '0.47uH',
             'SPEC': '0.47uH +-20%, Isat 6 A, Irated 4.4 A, DCR 27 mOhm max, 2.5 x 2.0 x 1.0 mm -- TPS63802 inductor '
                     'between L1 and L2 (datasheet: 0.47 uH nominal)'}
C80_SPEC = ('X5R 10V +-20%, 1.45 mm max -- TPS63802 COUT on VCC3V3, next to VOUT/GND (datasheet: 22 uF nominal '
            'for VOUT <= 3.6 V)')
C147_SPEC_ADD = ' -- TPS63802 CIN, next to VIN/GND (datasheet: 10 uF)'
rng = random.Random(63802)


def num(b, k):
    v, f = field(b, k), field(b, k + '_Frac')
    return (int(v) if v else 0) + (int(f) if f else 0) / 1e5


def setxy(b, kx, ky, x, y):
    b = del_field(del_field(b, kx + '_Frac'), ky + '_Frac')
    return set_field(set_field(b, kx, '%d' % x), ky, '%d' % y)


def shift(b, dx, dy):
    for kx, ky in [('Location.X', 'Location.Y'), ('Corner.X', 'Corner.Y')] + [('X%d' % k, 'Y%d' % k) for k in range(1, 9)]:
        if field(b, kx) is not None or field(b, kx + '_Frac') is not None:
            b = set_field(b, kx, '%d' % (int(field(b, kx) or 0) + dx))
            b = set_field(b, ky, '%d' % (int(field(b, ky) or 0) + dy))
    return b


def main():
    path = sys.argv[1]
    recs = split(read_stream(path))
    sheets = glob.glob(os.path.join(os.path.dirname(path), '*.SchDoc'))
    used = {field(b, 'Text') for s in sheets for h, b in split(read_stream(s)) if field(b, 'RECORD') == '34'}
    if used & {'R109', 'R110'}:
        sys.exit('REFUSED: R109/R110 already exist')
    taken = {field(b, 'UniqueID') for h, b in recs} | {field(b, 'Text') for h, b in recs}

    def uid():
        while True:
            u = ''.join(rng.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(8))
            if u not in taken:
                taken.add(u)
                return u

    def comp(des):
        r = [owner(b) for h, b in recs if field(b, 'RECORD') == '34' and field(b, 'Text') == des]
        if len(r) != 1:
            sys.exit('REFUSED: %d parts named %s' % (len(r), des))
        return r[0]

    u5 = comp('U5')
    if field(recs[u5][1], 'LibReference') != 'SC189-SOT23-5':
        sys.exit('REFUSED: U5 is %s, not the SC189' % field(recs[u5][1], 'LibReference'))
    st = sorted(subtree(recs, [u5]))
    if st != list(range(st[0], st[-1] + 1)):
        sys.exit('REFUSED: U5 records are not contiguous')
    top = max(int(field(b, 'IndexInSheet') or 0) for h, b in recs)

    # ---- the new U5 subtree, built in the old one's slot
    old = {i: recs[i] for i in st}
    kinds = [field(old[i][1], 'RECORD') for i in st]
    lines = [i for i in st if kinds[st.index(i)] == '6']
    pins = [i for i in st if kinds[st.index(i)] == '2']
    if len(lines) != 4 or len(pins) != 5 or field(old[pins[0]][1], 'Name') != 'VIN' or \
            field(old[pins[0] + 1][1], 'Name') != 'PinUniqueId':
        sys.exit('REFUSED: U5 symbol is not the expected SC189 layout')
    pin_t, puid_t = old[pins[0]], old[pins[0] + 1]
    new = []                                            # [hdr, body, local owner position or None (= U5 root)]
    x0, y0, x1, y1 = BODY
    for i in st:
        h, b = old[i]
        r = field(b, 'RECORD')
        if i == u5:
            for k, v in (('LibReference', 'TPS63802-DLA'), ('DesignItemId', 'TPS63802-DLA'), ('AllPinCount', '10'),
                         ('ComponentDescription', '2A buck-boost converter, 1.3-5.5 V in, adjustable 1.8-5.2 V out '
                                                  '(TI TPS63802, VSON-HR 10 DLA)'),
                         ('Location.Y', str(y0))):
                b = set_field(b, k, v)
            new.append([h, b, 'ROOT'])
        elif r == '6':
            seg = [(x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)][lines.index(i)]
            for k, v in zip(('X1', 'Y1', 'X2', 'Y2'), seg):
                b = set_field(del_field(b, k + '_Frac'), k, str(v))
            new.append([h, b, 'U5'])
        elif i == pins[0]:
            for des, name, x, y, cong, ln, el in PINS:
                pb = pin_t[1]
                for k, v in (('Name', name), ('Designator', des), ('PinConglomerate', str(cong)), ('PinLength', str(ln)),
                             ('Electrical', str(el))):
                    pb = set_field(pb, k, v)
                pb = setxy(pb, 'Location.X', 'Location.Y', x, y)
                new.append([pin_t[0], pb, 'U5'])
                ub = setxy(puid_t[1], 'Location.X', 'Location.Y', x, y)
                ub = set_field(set_field(ub, 'Text', uid()), 'UniqueID', uid())
                new.append([puid_t[0], ub, len(new) - 1])
        elif r == '2' or (r == '41' and field(b, 'Name') == 'PinUniqueId'):
            continue
        else:
            if r == '41' and field(b, 'Name') in PARAMS:
                b = set_field(b, 'Text', PARAMS[field(b, 'Name')])
                if field(b, 'Name') == 'PartName':
                    b = setxy(b, 'Location.X', 'Location.Y', 505, 515)
            elif r == '45':
                b = set_field(set_field(b, 'ModelName', FP), 'ModelDatafileEntity0', FP)
            o = owner(b)
            new.append([h, b, 'U5' if o == u5 else ('OLD', o)])
    # resolve owners inside the slot
    base = st[0]
    pos_of_old = {}                                     # where each surviving old record lands inside the slot
    j = 0
    for i in st:
        h, b = old[i]
        r = field(b, 'RECORD')
        if i == pins[0]:
            j += 2 * len(PINS)
            continue
        if r == '2' or (r == '41' and field(b, 'Name') == 'PinUniqueId'):
            continue
        pos_of_old[i] = j
        j += 1
    assert j == len(new)
    slot = []
    for h, b, o in new:
        if o == 'ROOT':
            pass
        elif o == 'U5':
            b = set_field(b, 'OwnerIndex', str(base - 1))
        elif isinstance(o, tuple):
            b = set_field(b, 'OwnerIndex', str(base + pos_of_old[o[1]] - 1))
        else:
            b = set_field(b, 'OwnerIndex', str(base + o - 1))
        slot.append([h, b])
    delta = len(slot) - len(st)
    out = recs[:base] + slot
    for h, b in recs[st[-1] + 1:]:
        o = owner(b)
        if o is not None and o > st[-1]:
            b = set_field(b, 'OwnerIndex', str(o + delta - 1))
        elif o is not None and o >= base:
            sys.exit('REFUSED: a record outside U5 is owned by a U5 record')
        out.append([h, b])
    recs = out

    # ---- part values: L1, C80, C147
    def set_param(des, name, text, append=False):
        c = comp(des)
        hit = [i for i, (h, b) in enumerate(recs) if owner(b) == c and field(b, 'RECORD') == '41' and field(b, 'Name') == name]
        if len(hit) != 1:
            sys.exit('REFUSED: %s has %d %s parameters' % (des, len(hit), name))
        b = recs[hit[0]][1]
        recs[hit[0]][1] = set_field(b, 'Text', (field(b, 'Text') + text) if append else text)
    for k, v in L1_PARAMS.items():
        set_param('L1', k, v)
    set_param('C80', 'SPEC', C80_SPEC)
    set_param('C147', 'SPEC', C147_SPEC_ADD, append=True)

    # ---- cut the L1 pin 2 -> VCC3V3 junction stretch (L1 pin 2 is now the L2 node)
    cut = 0
    for i, (h, b) in enumerate(recs):
        if field(b, 'RECORD') != '27' or owner(b) not in (None, 0):
            continue
        n = int(field(b, 'LocationCount'))
        pts = [(num(b, 'X%d' % k), num(b, 'Y%d' % k)) for k in range(1, n + 1)]
        if pts[0] == (625, 560) and pts[1][1] == 560 and pts[1][0] > 625:
            if pts[1] == (650, 560) and n > 2:
                pts = pts[1:]
            else:
                pts[0] = (650, 560)
        elif pts[-1] == (625, 560) and pts[-2][1] == 560 and pts[-2][0] > 625:
            if pts[-2] == (650, 560) and n > 2:
                pts = pts[:-1]
            else:
                pts[-1] = (650, 560)
        else:
            continue
        for k in range(1, n + 1):
            b = del_field(del_field(b, 'X%d' % k), 'Y%d' % k)
        b = set_field(b, 'LocationCount', str(len(pts)))
        for k, (x, y) in enumerate(pts, 1):
            b = set_field(set_field(b, 'X%d' % k, '%d' % x), 'Y%d' % k, '%d' % y)
        recs[i][1] = b
        cut += 1
    if cut != 1:
        sys.exit('REFUSED: found %d wires leaving L1 pin 2 towards the VCC3V3 junction' % cut)

    # ---- move the old GND port under the two ground pins
    gp = [i for i, (h, b) in enumerate(recs) if field(b, 'RECORD') == '17' and field(b, 'Text') == 'GND'
          and (num(b, 'Location.X'), num(b, 'Location.Y')) == (505, 500)]
    if len(gp) != 1:
        sys.exit('REFUSED: U5 GND port not found at (505, 500)')
    recs[gp[0]][1] = setxy(recs[gp[0]][1], 'Location.X', 'Location.Y', 505, 480)
    port_t = recs[gp[0]]

    # ---- appended objects: R109/R110 (clones of R105), wires, junctions, GND ports, note
    r105 = comp('R105')
    tmpl = sorted(subtree(recs, [r105]))
    cx, cy = int(field(recs[r105][1], 'Location.X')), int(field(recs[r105][1], 'Location.Y'))
    for des, val, mpn, (x, y), spec in RES:
        base = len(recs)
        idx = {}
        for i in tmpl:
            h, b = recs[i]
            idx[i] = base + len(idx)
        for i in tmpl:
            h, b = recs[i]
            b = shift(b, x - cx, y - cy)
            if field(b, 'UniqueID'):
                b = set_field(b, 'UniqueID', uid())
            r = field(b, 'RECORD')
            if r == '41' and field(b, 'Name') == 'PinUniqueId':
                b = set_field(b, 'Text', uid())
            elif r == '41' and field(b, 'Name') in ('MANF#', 'SPEC', 'Comment'):
                b = set_field(b, 'Text', {'MANF#': mpn, 'SPEC': spec, 'Comment': val}[field(b, 'Name')])
            elif r == '34':
                b = set_field(b, 'Text', des)
            if i == r105:
                top += 1
                b = set_field(b, 'IndexInSheet', str(top))
            o = owner(b)
            if o is not None and o in idx:
                b = set_field(b, 'OwnerIndex', str(idx[o] - 1))
            recs.append([h, b])
    wire_t = next((h, b) for h, b in recs if field(b, 'RECORD') == '27' and field(b, 'LocationCount') == '2'
                  and owner(b) in (None, 0))
    junc_t = next((h, b) for h, b in recs if field(b, 'RECORD') == '29' and owner(b) in (None, 0))
    note_t = next((h, b) for h, b in recs if field(b, 'RECORD') == '4' and (field(b, 'Text') or '').startswith('2026-09-06'))
    for (ax, ay), (bx, by) in WIRES:
        h, b = wire_t
        b = setxy(setxy(b, 'X1', 'Y1', ax, ay), 'X2', 'Y2', bx, by)
        top += 1
        recs.append([h, set_field(set_field(b, 'UniqueID', uid()), 'IndexInSheet', str(top))])
    for x, y in JUNCTIONS:
        h, b = junc_t
        top += 1
        recs.append([h, set_field(set_field(setxy(b, 'Location.X', 'Location.Y', x, y), 'UniqueID', uid()),
                                  'IndexInSheet', str(top))])
    for x, y in GND_PORTS:
        h, b = port_t
        top += 1
        recs.append([h, set_field(set_field(setxy(b, 'Location.X', 'Location.Y', x, y), 'UniqueID', uid()),
                                  'IndexInSheet', str(top))])
    h, b = note_t
    top += 1
    recs.append([h, set_field(set_field(set_field(setxy(b, 'Location.X', 'Location.Y', 445, 582), 'Text', NOTE),
                                        'UniqueID', uid()), 'IndexInSheet', str(top))])
    recs[0][1] = set_field(recs[0][1], 'Weight', str(len(recs) - 1))
    write_stream(path, join(recs))
    print('U5 -> TPS63802 on %s: %d records (was %d before the edit)' % (os.path.basename(path), len(recs),
                                                                         len(recs) - delta - 2 * len(tmpl) - len(WIRES)
                                                                         - len(JUNCTIONS) - len(GND_PORTS) - 1))


if __name__ == '__main__':
    main()
