"""Replace the power section on sheet 1 of a Zulu A7 project with an Analog Devices LTC3556 (2026-11-10, user request;
same edit on Zulu A7 Fab B and Asar Feather).

U8 bq24232 -> LTC3556EUFD (UFD QFN-28 4 x 5 mm): USB PowerPath + Li-ion charger + Buck1 (VCC1V0) + Buck2 (VCC1V8) +
buck-boost (VCC3V3), started in that order by SEQ = GND and ENALL (Fab B: ENALL = VU; Asar: ENALL = the Feather EN net).
U5 (TPS63802), U6/U7 (SC189), R104/R105/R106 (bq TMR/ITERM/TS) and R109/R110 (TPS63802 FB) are deleted. I2C is off
(DVCC/SCL/SDA = GND). The circuit is docs/ltc3556.md (designed from LTC3556 datasheet Rev A, two independent designs +
a judge). Parts that keep their designator keep their UniqueID, so their PCB links survive the ECO.

Method: everything of the old power section inside BOXES is removed (components except X1/X4, wires, ports, labels,
junctions, No-ERC marks, notes); dangling wire stubs are pruned; any surviving pin that lost its connection gets a net
label with its old net. The new block is drawn with net labels: U8 in the old regulator area, the passives in a grid
in the old charger area.

    python tools/apply_ltc3556.py <sheet-1 SchDoc> fabb|asar      (close the project in Altium first)
"""
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from schdoc import del_field, field, join, owner, read_stream, set_field, split, write_stream  # noqa: E402
import sch_netlist  # noqa: E402

BOXES = [(85, 735, 795, 1052), (360, 200, 775, 645)]
NOTE_BAND = (295, 675, 1000, 715)                       # only text records here (the bq24232 notes)
KEEP_COMPONENTS = {'X1', 'X4', 'R26', 'R27', 'R28'}
DELETE = {'U5', 'U6', 'U7', 'R104', 'R105', 'R106', 'R109', 'R110'}
rng = random.Random(3556)

# ---- the circuit (docs/ltc3556.md). Two-pin parts: (des, kind, value, MPN, SPEC, model, pin1 net, pin2 net)
PARTS = [
    ('L8', 'L', '3.3uH', 'DFE252012F-3R3M=P2', '3.3uH +-20%, Isat 2.5 A, Itemp 1.8 A, DCR 135 mOhm max, 2520 1.2 mm -- LTC3556 PowerPath inductor (SW to VOUT)', 'IND2520', 'PWR_SW', 'VU'),
    ('L3', 'L', '1.5uH', 'DFE252010P-1R5M=P2', '1.5uH +-20%, Isat >=1.8A, 1.00 mm max -- U7 SC189A LX inductor (VCC1V0), 2.5 MHz, <=0.31 A p-p ripple', 'IND2520', 'PWR_LX1V0', 'VCC1V0'),
    ('L9', 'L', '2.2uH', 'DFE252012F-2R2M=P2', '2.2uH +-20%, 2520 -- LTC3556 Buck1 kept running unloaded as the sequencing slot (SEQ = GND: Buck1 -> Buck2 -> buck-boost), so 1.8 V starts after U7 has brought up 1.0 V', 'IND2520', 'PWR_SW1', 'PWR_FB1'),
    ('L2', 'L', '2.2uH', 'DFE252012F-2R2M=P2', '2.2uH +-20%, Isat 3.3 A, Itemp 2.3 A, DCR 82 mOhm max, 2520 1.2 mm -- LTC3556 Buck2 (VCC1V8) inductor (2520 like L1/L3: no verified Murata land pattern for the 2016 part)', 'IND2520', 'PWR_SW2', 'VCC1V8'),
    ('L1', 'L', '2.2uH', 'DFE252012F-2R2M=P2', '2.2uH +-20%, Isat 3.3 A, Itemp 2.3 A, DCR 82 mOhm max, 2520 1.2 mm -- LTC3556 buck-boost (VCC3V3) inductor, SWAB3 to SWCD3', 'IND2520', 'PWR_SWAB3', 'PWR_SWCD3'),
    ('C150', 'C', '10uF', 'GRM188R61C106MA73D', 'X5R 16V +-20% 0603 10uF -- LTC3556 VBUS bypass (pin 25)', 'C0603', 'GND', 'USB5V0'),
    ('C151', 'C', '4.7uF', 'GRM188R61C475KE11D', 'X5R 16V +-10% 0603 4.7uF -- LTC3556 BAT bypass (pin 23), 1-22 uF ceramic', 'C0603', 'GND', 'VBATT'),
    ('C147', 'C', '10uF', 'GRM188R61A106KE69D', 'X5R 10V +-10% 0603 10uF -- LTC3556 VOUT (PowerPath output, pin 24) bypass', 'C0603', 'GND', 'VU'),
    ('C78', 'C', '10uF 10V', 'CL21A106KPFNNNG', 'X5R 10V +-10% 0805 10uF -- VU bulk', 'C0805', 'GND', 'VU'),
    ('C148', 'C', '10uF', 'GRM188R61A106KE69D', 'X5R 10V +-10% 0603 10uF -- LTC3556 VIN3 (buck-boost input, pin 11) bypass', 'C0603', 'GND', 'VU'),
    ('C149', 'C', '10uF', 'CL21A106KPFNNNG', 'X5R 10V +-10% 0805 10uF -- U7 SC189A VIN bypass (>= 4.7 uF effective)', 'C0805', 'GND', 'VU'),
    ('C167', 'C', '1uF', 'GRM155R61A105KE15D', 'X5R 10V +-10% 0402 1uF -- LTC3556 VIN1 (Buck1 input, pin 5) bypass, the 1 uF the datasheet asks for', 'C0402', 'GND', 'VU'),
    ('C168', 'C', '10uF', 'GRM188R61A106KE69D', 'X5R 10V +-10% 0603 10uF -- LTC3556 Buck1 output (sequencing slot, FB1 tied to it: 0.8 V, no load)', 'C0603', 'GND', 'PWR_FB1'),
    ('C160', 'C', '2.2uF', 'GRM155R61A225KE95D', 'X5R 10V +-10% 0402 2.2uF -- LTC3556 VIN2 (Buck2 input, pin 18) bypass', 'C0402', 'GND', 'VU'),
    ('C161', 'C', '1uF', 'GRM155R61A105KE15D', 'X5R 10V +-10% 0402 1uF -- LTC3556 CLPROG averaging capacitor (>= 0.47 uF)', 'C0402', 'GND', 'PWR_CLPROG'),
    ('C84', 'C', '22uF', 'CL10A226MP8NUNE', 'X5R 10V +-20% 0603 22uF -- U7 SC189A (VCC1V0) output capacitor', 'C0603', 'GND', 'VCC1V0'),
    ('C82', 'C', '22uF', 'CL10A226MP8NUNE', 'X5R 10V +-20% 0603 22uF -- Buck2 (VCC1V8) output capacitor', 'C0603', 'GND', 'VCC1V8'),
    ('C80', 'C', '22uF', 'GRM21BR61A226ME44L', 'X5R 10V +-20% 0805 22uF -- buck-boost (VCC3V3) output capacitor, the 22 uF the Type III values assume', 'C0805', 'GND', 'VCC3V3'),
    ('R113', 'R', '150K', 'RC0201FR-07150KL', 'thick film +-1% 0201 -- Buck2 divider top: 0.8 V x (1 + 150k/120k) = 1.800 V', 'R0201', 'VCC1V8', 'PWR_FB2'),
    ('R114', 'R', '120K', 'RC0201FR-07120KL', 'thick film +-1% 0201 -- Buck2 divider bottom', 'R0201', 'PWR_FB2', 'GND'),
    ('C163', 'C', '10pF', 'GRM0335C1H100JA01D', 'C0G 50V +-5% 0201 10pF -- Buck2 feed-forward across R113', 'C0201', 'VCC1V8', 'PWR_FB2'),
    ('R115', 'R', '324K', 'RC0201FR-07324KL', 'thick film +-1% 0201 -- buck-boost divider top / Type III R1: 0.8 V x (1 + 324k/105k) = 3.27 V', 'R0201', 'VCC3V3', 'PWR_FB3'),
    ('R116', 'R', '105K', 'RC0201FR-07105KL', 'thick film +-1% 0201 -- buck-boost divider bottom (RFB)', 'R0201', 'PWR_FB3', 'GND'),
    ('R118', 'R', '121K', 'RC0201FR-07121KL', 'thick film +-1% 0201 -- Type III R3 (with C166 across R115)', 'R0201', 'VCC3V3', 'PWR_FB3_FF'),
    ('C166', 'C', '33pF', 'GRM0335C1H330JA01D', 'C0G 50V +-5% 0201 33pF -- Type III C3', 'C0201', 'PWR_FB3_FF', 'PWR_FB3'),
    ('C164', 'C', '10pF', 'GRM0335C1H100JA01D', 'C0G 50V +-5% 0201 10pF -- Type III C1 (FB3 to VC3)', 'C0201', 'PWR_FB3', 'PWR_VC3'),
    ('R117', 'R', '15K', 'RC0201FR-0715KL', 'thick film +-1% 0201 -- Type III R2 (with C165, VC3 to FB3)', 'R0201', 'PWR_VC3', 'PWR_VC3_RC'),
    ('C165', 'C', '330pF', 'GRM0335C1H331JA01D', 'C0G 50V +-5% 0201 330pF -- Type III C2', 'C0201', 'PWR_VC3_RC', 'PWR_FB3'),
    ('R102', 'R', '4.12K', 'RC0402FR-074K12L', 'thick film +-1% 0402 -- LTC3556 PROG: 1022 V / 4.12k = 248 mA charge current', 'R0402', 'PWR_PROG', 'GND'),
    ('R103', 'R', '576', 'RC0402FR-07576RL', 'thick film +-1% 0402 -- LTC3556 CLPROG, 500 mA USB limit with I2C off (1x mode, hCLPROG 224): 1.188 V x 225 / 576 = 464 mA + 0.4 mA typ, ~425-489 mA over the datasheet spread; CLPROG pin 2.1 mA < 3 mA abs max', 'R0402', 'PWR_CLPROG', 'GND'),
    ('R107', 'R', '680', 'RC0402FR-07680RL', 'thick film +-1% 0402 -- PGOODALL pull-up and LD3 current: (3.3 - 2.0) / 680 = 1.9 mA', 'R0402', 'VCC3V3', 'PWR_PGOODALL'),
    ('R108', 'R', '1K', 'RC0402FR-071KL', 'thick film +-1% 0402 -- LD4 (CHRG) current: (3.7 - 2.0) / 1.0k = 1.7 mA', 'R0402', 'VU', 'LD4_A'),
]
U7_NETS = {'1': 'VU', '2': 'GND', '3': None, '4': 'VCC1V0', '5': 'PWR_LX1V0'}   # pin 3 EN = the ENALL net
LEDS = [('LD3', 'PWR_PGOODALL', 'GND', 'green -- LTC3556 PGOODALL: all three rails good (lights 230 ms after VCC3V3 is up)'),
        ('LD4', 'LD4_A', 'PWR_CHRG', 'red -- LTC3556 CHRG: on = charging, off = done / no USB, fast blink = bad battery')]
#        pin  name       side  electrical (0 in, 3 open collector, 4 passive, 7 power)
U8_PINS = [('25', 'VBUS', 'L', 7), ('26', 'SW', 'L', 4), ('1', 'LDO3V3', 'L', 4), ('28', 'ENALL', 'L', 0), ('27', 'SEQ', 'L', 0),
           ('2', 'CLPROG', 'L', 4), ('20', 'PROG', 'L', 4), ('3', 'NTC', 'L', 0), ('10', 'DVCC', 'L', 7), ('13', 'SCL', 'L', 0),
           ('16', 'SDA', 'L', 0), ('22', 'GATE', 'L', 4),
           ('24', 'VOUT', 'R', 7), ('23', 'BAT', 'R', 7), ('21', 'CHRG', 'R', 3), ('15', 'PGOODALL', 'R', 3), ('5', 'VIN1', 'R', 7),
           ('4', 'SW1', 'R', 4), ('6', 'FB1', 'R', 4), ('18', 'VIN2', 'R', 7), ('19', 'SW2', 'R', 4), ('17', 'FB2', 'R', 4),
           ('11', 'VIN3', 'R', 7), ('9', 'SWAB3', 'R', 4), ('14', 'SWCD3', 'R', 4), ('12', 'VOUT3', 'R', 7), ('7', 'FB3', 'R', 4),
           ('8', 'VC3', 'R', 4), ('29', 'GND', 'B', 7)]
U8_NETS = {'25': 'USB5V0', '26': 'PWR_SW', '1': 'VU', '28': None, '27': 'GND', '2': 'PWR_CLPROG', '20': 'PWR_PROG', '3': 'GND',
           '10': 'GND', '13': 'GND', '16': 'GND', '22': '', '24': 'VU', '23': 'VBATT', '21': 'PWR_CHRG', '15': 'PWR_PGOODALL',
           '5': 'VU', '4': 'PWR_SW1', '6': 'PWR_FB1', '18': 'VU', '19': 'PWR_SW2', '17': 'PWR_FB2', '11': 'VU', '9': 'PWR_SWAB3',
           '14': 'PWR_SWCD3', '12': 'VCC3V3', '7': 'PWR_FB3', '8': 'PWR_VC3', '29': 'GND'}
U8_ORIGIN = (470, 330)                                 # body lower-left; 120 wide, 180 tall
U8_PARAMS = {'PartName': 'LTC3556', 'MANF': 'Analog Devices', 'MANF#': 'LTC3556EUFD#PBF', 'Comment': 'LTC3556EUFD#PBF',
             'SPEC': 'USB PowerPath manager + 4.2 V Li-ion charger + 2 x 400 mA buck + 1 A buck-boost, I2C off (DVCC = GND), '
                     'SEQ = GND: Buck1 -> Buck2 -> buck-boost; UFD QFN-28 4 x 5 mm, exposed pad = GND'}
U8_MODEL = 'QFN28-UFD-4X5'
IND_SLOTS = [(150, 1010), (350, 1010), (550, 1010), (750, 1010)]
GRID = [(x, y) for y in (940, 870, 800, 730, 660) for x in (110, 210, 310, 410, 510, 610, 710)
        if not (y == 940 and x >= 610)]                 # X4 sits at (700, 940)
NOTES = ['2026-11-10: U8 bq24232 + U5 TPS63802 + U6 SC189L -> one Analog Devices LTC3556 (USB PowerPath, charger 248 mA,',
         'Buck2 VCC1V8 400 mA, buck-boost VCC3V3 1 A); VCC1V0 stays on U7 SC189A (1.5 A: XPE puts a half-full XC7A35T at ~0.4 A).',
         'U7 starts on ENALL; Buck1 runs unloaded as a sequencing slot (SEQ = GND), so 1V0 -> 1V8 -> 3V3. I2C off (DVCC/SCL/SDA = GND):',
         'USB input limit = 1x mode set by R103 = 576R: ~465 mA typ, 489 mA max (500 mA USB). NTC grounded, GATE open. LD3 = rails good, LD4 = charging.']
NOTE_XY = (100, 590)


def num(b, k):
    v, f = field(b, k), field(b, k + '_Frac')
    return (int(v) if v else 0) + (int(f) if f else 0) / 1e5


def setxy(b, kx, ky, x, y):
    b = del_field(del_field(b, kx + '_Frac'), ky + '_Frac')
    return set_field(set_field(b, kx, '%d' % x), ky, '%d' % y)


def shift(b, dx, dy):
    for kx, ky in [('Location.X', 'Location.Y'), ('Corner.X', 'Corner.Y')] + [('X%d' % k, 'Y%d' % k) for k in range(1, 9)]:
        if field(b, kx) is not None or field(b, kx + '_Frac') is not None:
            b = set_field(del_field(b, kx + '_Frac'), kx, '%d' % round(num(b, kx) + dx))
            b = set_field(del_field(b, ky + '_Frac'), ky, '%d' % round(num(b, ky) + dy))
    return b


def wire_pts(b):
    n = int(field(b, 'LocationCount') or 0)
    return [(num(b, 'X%d' % k), num(b, 'Y%d' % k)) for k in range(1, n + 1)]


def inbox(x, y, box):
    return box[0] <= x <= box[2] and box[1] <= y <= box[3]


def pin_end(b):
    x, y = num(b, 'Location.X'), num(b, 'Location.Y')
    c = int(field(b, 'PinConglomerate') or 0)
    ln = num(b, 'PinLength')
    dx, dy = [(1, 0), (0, 1), (-1, 0), (0, -1)][c & 3]
    return (round(x + dx * ln, 3), round(y + dy * ln, 3))


def on_seg(p, a, c, eps=1e-3):
    if abs((c[0] - a[0]) * (p[1] - a[1]) - (c[1] - a[1]) * (p[0] - a[0])) > eps:
        return False
    return min(a[0], c[0]) - eps <= p[0] <= max(a[0], c[0]) + eps and min(a[1], c[1]) - eps <= p[1] <= max(a[1], c[1]) + eps


class Sheet:
    def __init__(self, path):
        self.path = path
        self.recs = split(read_stream(path))
        self.reindex()
        self.taken = {field(b, 'UniqueID') for h, b in self.recs} | {field(b, 'Text') for h, b in self.recs}
        self.top = max(int(field(b, 'IndexInSheet') or 0) for h, b in self.recs)

    def reindex(self):
        self.kids = {}
        for i, (h, b) in enumerate(self.recs):
            o = owner(b)
            if o is not None:
                self.kids.setdefault(o, []).append(i)
        self.des = {owner(b): field(b, 'Text') for h, b in self.recs if field(b, 'RECORD') == '34'}
        self.byname = {v: k for k, v in self.des.items()}

    def sub(self, i):
        out, st = [i], [i]
        while st:
            for c in self.kids.get(st.pop(), []):
                out.append(c)
                st.append(c)
        return sorted(out)

    def uid(self):
        while True:
            u = ''.join(rng.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(8))
            if u not in self.taken:
                self.taken.add(u)
                return u

    def nxt(self):
        self.top += 1
        return str(self.top)

    def template(self, des):
        """Copy of a component subtree: list of [hdr, body, local owner position or None]."""
        st = self.sub(self.byname[des])
        pos = {j: k for k, j in enumerate(st)}
        return [[h, b, (pos[owner(b)] if j != st[0] else None)] for j in st for h, b in [self.recs[j]]]

    def delete(self, idxs):
        idxs = set(idxs)
        newi, out = {}, []
        for i, r in enumerate(self.recs):
            if i not in idxs:
                newi[i] = len(out)
                out.append(r)
        for k, (h, b) in enumerate(out):
            o = owner(b)
            if o is not None and field(b, 'OwnerIndex') is not None and o > 0:
                assert o in newi, 'record owned by a deleted record'
                out[k] = [h, set_field(b, 'OwnerIndex', str(newi[o] - 1))]
        self.recs = out
        self.reindex()

    def add_part(self, tmpl, des, x, y, edit, uid=None):
        base = len(self.recs)
        h0, b0, _ = tmpl[0]
        dx, dy = x - num(b0, 'Location.X'), y - num(b0, 'Location.Y')
        for k, (h, b, o) in enumerate(tmpl):
            b = shift(b, dx, dy)
            if field(b, 'UniqueID'):
                b = set_field(b, 'UniqueID', uid if (k == 0 and uid) else self.uid())
            if field(b, 'RECORD') == '41' and field(b, 'Name') == 'PinUniqueId':
                b = set_field(b, 'Text', self.uid())
            if k == 0:
                b = set_field(b, 'IndexInSheet', self.nxt())
            if field(b, 'RECORD') == '34':
                b = set_field(b, 'Text', des)
            if o is not None:
                b = set_field(b, 'OwnerIndex', str(base + o - 1))
            self.recs.append([h, edit(b)])
        self.reindex()
        return base

    def add_simple(self, tmpl, edit):
        h, b = tmpl
        b = edit(b)
        if field(b, 'UniqueID'):
            b = set_field(b, 'UniqueID', self.uid())
        self.recs.append([h, set_field(b, 'IndexInSheet', self.nxt())])


def set_params(b, d):
    if field(b, 'RECORD') == '41' and field(b, 'Name') in d:
        b = set_field(b, 'Text', d[field(b, 'Name')])
    return b


def main():
    path, board = sys.argv[1], sys.argv[2]
    assert board in ('fabb', 'asar')
    U8_NETS['28'] = 'VU' if board == 'fabb' else 'EN'
    S = Sheet(path)
    folder = os.path.dirname(path)
    old_nets = sch_netlist.build(folder)
    pin_net = {p: n for n, pins in old_nets.items() for p in pins}
    if field(S.recs[S.byname['U8']][1], 'LibReference') != 'BQ24232-RGT16':
        sys.exit('REFUSED: U8 is not the bq24232')

    # ---- templates (before anything is deleted)
    T = {'R': S.template('R105'), 'C': S.template('C82'), 'L': S.template('L1'), 'LED': S.template('LD3'),
         'IC': S.template('U5')}
    top_t = {}
    for i, (h, b) in enumerate(S.recs):
        if owner(b) in (None, 0) and field(b, 'RECORD') in ('27', '25', '22', '4', '17', '29'):
            r = field(b, 'RECORD')
            if r == '27' and field(b, 'LocationCount') != '2':
                continue
            if r == '25' and field(b, 'Orientation'):
                continue
            top_t.setdefault(r, (h, b))
    keep_uid = {}
    for des in [p[0] for p in PARTS] + ['LD3', 'LD4', 'U8']:
        if des in S.byname:
            keep_uid[des] = field(S.recs[S.byname[des]][1], 'UniqueID')

    # ---- delete the old section
    dele = set()
    for i, (h, b) in enumerate(S.recs):
        r = field(b, 'RECORD')
        if r == '1':
            d = S.des.get(i)
            x, y = num(b, 'Location.X'), num(b, 'Location.Y')
            if d in DELETE or (d not in KEEP_COMPONENTS and any(inbox(x, y, bx) for bx in BOXES)):
                dele |= set(S.sub(i))
        elif owner(b) in (None, 0) and r in ('27', '29', '17', '25', '22', '4', '28'):
            pts = wire_pts(b) if r == '27' else [(num(b, 'Location.X'), num(b, 'Location.Y'))]
            if any(inbox(x, y, bx) for x, y in pts for bx in BOXES):
                dele.add(i)
            elif r == '4' and inbox(pts[0][0], pts[0][1], NOTE_BAND):
                dele.add(i)
    gone = sorted({S.des[i] for i in dele if i in S.des})
    S.delete(dele)

    # ---- prune dangling wire stubs, then label surviving pins that lost their connection
    def anchors():
        pts, segs = set(), []
        for i, (h, b) in enumerate(S.recs):
            r = field(b, 'RECORD')
            if r == '2':
                pts.add(pin_end(b))
            elif owner(b) in (None, 0) and r in ('25', '17', '29'):
                pts.add((num(b, 'Location.X'), num(b, 'Location.Y')))
            elif owner(b) in (None, 0) and r == '27':
                w = wire_pts(b)
                segs.append((i, w))
        return pts, segs
    while True:
        pts, segs = anchors()
        kill = set()
        for i, w in segs:
            for e in (w[0], w[-1]):
                hit = e in pts or any(j != i and any(on_seg(e, a, c) for a, c in zip(v, v[1:])) for j, v in segs)
                if not hit:
                    kill.add(i)
        if not kill:
            break
        S.delete(kill)
    pts, segs = anchors()
    orphans = []
    for i, (h, b) in enumerate(S.recs):
        if field(b, 'RECORD') != '2':
            continue
        o = owner(b)
        d = S.des.get(o)
        e = pin_end(b)
        net = pin_net.get((d, field(b, 'Designator')))
        if not net or net.startswith('N$'):
            continue
        connected = any(any(on_seg(e, a, c) for a, c in zip(w, w[1:])) for j, w in segs) or \
            any((num(bb, 'Location.X'), num(bb, 'Location.Y')) == e for hh, bb in S.recs
                if owner(bb) in (None, 0) and field(bb, 'RECORD') in ('25', '17'))
        if not connected:
            orphans.append((e, net, d, field(b, 'Designator')))

    def label(x, y, text, just=None):
        def ed(b):
            b = setxy(del_field(del_field(b, 'Orientation'), 'Justification'), 'Location.X', 'Location.Y', x, y)
            b = set_field(b, 'Text', text)
            return set_field(b, 'Justification', str(just)) if just else b
        S.add_simple(top_t['25'], ed)

    def wire(a, c):
        def ed(b):
            for k in (1, 2):
                b = del_field(del_field(b, 'X%d_Frac' % k), 'Y%d_Frac' % k)
            return setxy(setxy(b, 'X1', 'Y1', *a), 'X2', 'Y2', *c)
        S.add_simple(top_t['27'], ed)
    for (x, y), net, d, p in orphans:
        label(x, y, net)

    # ---- U8: LTC3556 symbol built on the TPS63802 template (root, 4 body lines, pins, params, model)
    x0, y0 = U8_ORIGIN
    W, H = 120, 180
    tmpl = T['IC']
    pin_k = [k for k, (h, b, o) in enumerate(tmpl) if field(b, 'RECORD') == '2']
    line_k = [k for k, (h, b, o) in enumerate(tmpl) if field(b, 'RECORD') == '6']
    pin_t, puid_t = tmpl[pin_k[0]], tmpl[pin_k[0] + 1]
    items = []
    for k, (h, b, o) in enumerate(tmpl):
        r = field(b, 'RECORD')
        if r == '2' or (r == '41' and field(b, 'Name') == 'PinUniqueId'):
            if k == pin_k[0]:
                left = [p for p in U8_PINS if p[2] == 'L']
                right = [p for p in U8_PINS if p[2] == 'R']
                for pd, name, side, el in U8_PINS:
                    if side == 'L':
                        px, py, cong = x0, y0 + H - 20 - 10 * left.index((pd, name, side, el)), 58
                    elif side == 'R':
                        px, py, cong = x0 + W, y0 + H - 20 - 10 * right.index((pd, name, side, el)), 56
                    else:
                        px, py, cong = x0 + W // 2, y0, 59
                    pb = pin_t[1]
                    for kk, v in (('Name', name), ('Designator', pd), ('PinConglomerate', str(cong)),
                                  ('PinLength', '30' if side != 'B' else '20'), ('Electrical', str(el))):
                        pb = set_field(pb, kk, v)
                    items.append([pin_t[0], setxy(pb, 'Location.X', 'Location.Y', px, py), 'ROOT'])
                    ub = setxy(puid_t[1], 'Location.X', 'Location.Y', px, py)
                    items.append([puid_t[0], set_field(set_field(ub, 'Text', S.uid()), 'UniqueID', S.uid()),
                                  ('NEW', len(items) - 1)])
            continue
        if k == 0:
            for kk, v in (('LibReference', 'LTC3556-UFD28'), ('DesignItemId', 'LTC3556-UFD28'), ('AllPinCount', '29'),
                          ('ComponentDescription', 'USB power manager: PowerPath + Li-ion charger + dual 400 mA buck + '
                                                   '1 A buck-boost (Analog Devices LTC3556, UFD QFN-28 4 x 5 mm)')):
                if kk in ('DesignItemId', 'AllPinCount') and field(b, kk) is None:
                    continue
                b = set_field(b, kk, v)
            b = setxy(b, 'Location.X', 'Location.Y', x0, y0)
            b = set_field(set_field(b, 'UniqueID', keep_uid['U8']), 'IndexInSheet', S.nxt())
        elif r == '6':
            seg = [(x0, y0, x0 + W, y0), (x0 + W, y0, x0 + W, y0 + H), (x0 + W, y0 + H, x0, y0 + H),
                   (x0, y0 + H, x0, y0)][line_k.index(k)]
            for kk, v in zip(('X1', 'Y1', 'X2', 'Y2'), seg):
                b = set_field(del_field(b, kk + '_Frac'), kk, str(v))
        elif r == '34':
            b = set_field(setxy(b, 'Location.X', 'Location.Y', x0, y0 + H + 4), 'Text', 'U8')
        elif r == '41' and field(b, 'Name') in U8_PARAMS:
            b = set_field(b, 'Text', U8_PARAMS[field(b, 'Name')])
            if field(b, 'Name') == 'PartName':
                b = set_field(setxy(b, 'Location.X', 'Location.Y', x0 + W // 2, y0 + H + 4), 'Justification', '1')
            elif field(b, 'Location.X') is not None:
                b = setxy(b, 'Location.X', 'Location.Y', x0 + W, y0 + H + 4)
        elif r == '45':
            b = set_field(set_field(b, 'ModelName', U8_MODEL), 'ModelDatafileEntity0', U8_MODEL)
        if field(b, 'UniqueID') and k != 0:
            b = set_field(b, 'UniqueID', S.uid())
        items.append([h, b, ('OLD', o) if k else None])
    oldpos = {}
    j = 0
    for k, (h, b, o) in enumerate(tmpl):
        r = field(b, 'RECORD')
        if r == '2' or (r == '41' and field(b, 'Name') == 'PinUniqueId'):
            if k == pin_k[0]:
                j += 2 * len(U8_PINS)
            continue
        oldpos[k] = j
        j += 1
    base = len(S.recs)
    root_pos = oldpos[0]
    for h, b, o in items:
        if o == 'ROOT':
            b = set_field(b, 'OwnerIndex', str(base + root_pos - 1))
        elif isinstance(o, tuple) and o[0] == 'NEW':
            b = set_field(b, 'OwnerIndex', str(base + o[1] - 1))
        elif isinstance(o, tuple):
            b = set_field(b, 'OwnerIndex', str(base + oldpos[o[1]] - 1))
        S.recs.append([h, b])
    S.reindex()
    # U8 pin stubs + labels
    left = [p for p in U8_PINS if p[2] == 'L']
    right = [p for p in U8_PINS if p[2] == 'R']
    for pd, name, side, el in U8_PINS:
        net = U8_NETS[pd]
        if side == 'L':
            y = y0 + H - 20 - 10 * left.index((pd, name, side, el))
            e, f = (x0 - 30, y), (x0 - 50, y)
            just = 2
        elif side == 'R':
            y = y0 + H - 20 - 10 * right.index((pd, name, side, el))
            e, f = (x0 + W + 30, y), (x0 + W + 50, y)
            just = None
        else:
            e, f = (x0 + W // 2, y0 - 20), (x0 + W // 2, y0 - 30)
            just = None
        if net == '':
            S.add_simple(top_t['22'], lambda b, e=e: setxy(b, 'Location.X', 'Location.Y', *e))
            continue
        wire(e, f)
        label(f[0], f[1], net, just)

    # ---- passives and LEDs on the grid, each pin labelled
    slots = list(GRID)

    def edit_two(des, value, mpn, spec, model, libref):
        def ed(b):
            r = field(b, 'RECORD')
            if r == '1':
                b = set_field(b, 'LibReference', libref)
            elif r == '45':
                b = set_field(set_field(b, 'ModelName', model), 'ModelDatafileEntity0', model)
            elif r == '41' and field(b, 'Name') == 'Comment':
                b = set_field(b, 'Text', value)
            elif r == '41' and field(b, 'Name') == 'MANF#':
                b = set_field(b, 'Text', mpn)
            elif r == '41' and field(b, 'Name') == 'SPEC':
                b = set_field(b, 'Text', spec)
            elif r == '41' and field(b, 'Name') == 'DeviceName':
                b = set_field(b, 'Text', model)
            return b
        return ed
    LIB = {'R': 'R-US_SMALL', 'C': 'C-GENERIC', 'L': 'INDUCTOR-'}

    def stub_label(e, x, y, net, horizontal):
        if horizontal:
            sx = -10 if e[0] < x else 10
            f = (e[0] + sx, e[1])
            wire(e, f)
            label(f[0], f[1], net, 2 if sx < 0 else None)
        else:
            sy = 10 if e[1] > y else -10
            f = (e[0], e[1] + sy)
            wire(e, f)
            label(f[0], f[1], net)
    ind_slots = list(IND_SLOTS)
    for des, kind, value, mpn, spec, model, n1, n2 in PARTS:
        x, y = ind_slots.pop(0) if kind == 'L' else slots.pop(0)
        libref = LIB[kind] + (model if kind != 'L' else model.replace('IND', ''))
        base = S.add_part(T[kind], des, x, y, edit_two(des, value, mpn, spec, model, libref), keep_uid.get(des))
        for k in S.sub(base):
            b = S.recs[k][1]
            if field(b, 'RECORD') != '2':
                continue
            e = pin_end(b)
            net = n1 if field(b, 'Designator') == '1' else n2
            stub_label(e, x, y, net, kind == 'L')
    for des, na, nk, spec in LEDS:
        x, y = slots.pop(0)
        base = S.add_part(T['LED'], des, x, y, lambda b, s=spec: set_params(b, {'SPEC': s}), keep_uid.get(des))
        for k in S.sub(base):
            b = S.recs[k][1]
            if field(b, 'RECORD') == '2':
                stub_label(pin_end(b), x, y, na if field(b, 'Designator') == 'A' else nk, False)
    for k, t in enumerate(NOTES):
        S.add_simple(top_t['4'], lambda b, k=k, t=t: set_field(setxy(b, 'Location.X', 'Location.Y', NOTE_XY[0],
                                                                    NOTE_XY[1] - 8 * k), 'Text', t))
    S.recs[0][1] = set_field(S.recs[0][1], 'Weight', str(len(S.recs) - 1))
    write_stream(path, join(S.recs))
    print('%s: removed %s; %d orphan pins labelled %s; %d records' % (
        os.path.basename(path), gone, len(orphans), [(d, p, n) for e, n, d, p in orphans], len(S.recs)))


if __name__ == '__main__':
    main()
