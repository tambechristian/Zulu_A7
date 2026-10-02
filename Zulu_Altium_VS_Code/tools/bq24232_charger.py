# -*- coding: utf-8 -*-
"""Sheet 1: replace D1 (the USB VBUS ORing Schottky) with a bq24232 LiPo charger and power path,
2026-09-09.

Datasheet/bq24232.pdf (TI SLUS821J, May 2017): 16-pin VQFN RGT 3 x 3 mm, IN 4.35-10.2 V, OUT
regulated at 4.4 V (LDO from the input) or VBAT - 60 mV without an input, input limit set by
EN1/EN2/ILIM, charge current by ISET, termination by ITERM, timers by TMR, NTC on TS.
Datasheet/JST_B2B_PH_SM4_TB_LF_SN_ePH.pdf: 2-pin PH 2.0 mm top-entry SMT header, 2 A.

What the block does on the board: USB5V0 goes into IN (no diode any more; the charger blocks
reverse current), OUT feeds VU, the battery on the JST connector X4 is charged from USB and
supplements or replaces the input on VU. The +5V-INPUT path through D2 onto VU is untouched.

Values (datasheet section 9.2.1): ILIM R103 3.09 k -> 495 mA input limit (EN2 = VU, EN1 = GND
selects the resistor); ISET R102 3.57 k -> 244 mA fast charge; ITERM R105 4.32 k -> 36 mA
(15 %); TMR R104 56.2 k -> 7.5 h fast-charge / 45 min precharge timers; TS R106 10 k fixed
(no thermistor on a 2-pin pack, so the pack needs its own protection); CE = GND enables
charging; PGOOD and CHG drive the green LD3 and red LD4 through 1.5 k (R107, R108) from VU;
C150 4.7 uF on IN, C151 4.7 uF on BAT (OUT already has the 40 uF on VU, inside the 47 uF
the datasheet allows).

Edits: D1's subtree and the wire that joined its cathode to VU are deleted (matched by
content); the USB5V0 wire keeps its label. Everything new is appended: U8 with its 17 pins,
X4, C150/C151 (clones of C78 re-valued to the board's 4.7 uF 0603 part), R102-R108 (clones of
R78), LD3/LD4 (clones of LD5), wires, junctions, net labels, ground ports and three note lines.
Footprints VQFN16-3X3-RGT and JST-B2B-PH-SM4-TB are for the PCB stage. Refuses to run twice.

    python tools/bq24232_charger.py tools "Imported zulu_a7.PrjPcb/zulu_a7_1.SchDoc"
"""
import sys, re, random, string
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field


def uid():
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(8))


COORD_KEYS = re.compile(rb'\|(Location\.X|Location\.Y|X\d+|Y\d+)=(-?\d+)')


def shift(b, dx, dy):
    def rep(m):
        k, v = m.group(1), int(m.group(2))
        v += dx if (k == b'Location.X' or k.startswith(b'X')) else dy
        return b'|' + k + b'=' + str(v).encode()
    return COORD_KEYS.sub(rep, b)


def new_uid(b):
    return re.sub(rb'\|UniqueID=[A-Z]{8}', b'|UniqueID=' + uid().encode(), b)


def owner_list_index(b):
    o = field(b, 'OwnerIndex')
    return int(o) + 1 if o is not None else None


def subtree(recs, comp_idx):
    members = {comp_idx}; changed = True
    while changed:
        changed = False
        for i, (h, b) in enumerate(recs):
            oi = owner_list_index(b)
            if oi in members and i not in members:
                members.add(i); changed = True
    return sorted(members)


def wire_pts(b):
    if not b.startswith(b'|RECORD=27|'):
        return None
    n = int(field(b, 'LocationCount') or 0)
    return [(int(field(b, f'X{k}')), int(field(b, f'Y{k}'))) for k in range(1, n + 1)]


# ------------------------------------------------------------------ layout --
BX0, BX1, BY0, BY1 = 300, 480, 340, 600          # charger body
LEFT = [   # (designator, name, y, electrical)  pins point left, hot end x = 270
    ('13', 'IN', 580, '7'), ('5', 'EN2', 550, '0'), ('4', 'CE', 520, '0'), ('6', 'EN1', 500, '0'),
    ('7', 'PGOOD', 460, '3'), ('9', 'CHG', 440, '3'), ('8', 'VSS', 380, '7'), ('17', 'PAD', 360, '7')]
RIGHT = [  # pins point right, hot end x = 510
    ('10', 'OUT', 580, '7'), ('11', 'OUT', 560, '7'), ('2', 'BAT', 520, '7'), ('3', 'BAT', 500, '7'),
    ('1', 'TS', 440, '4'), ('16', 'ISET', 420, '4'), ('12', 'ILIM', 400, '4'), ('14', 'TMR', 380, '4'), ('15', 'ITERM', 360, '4')]
# programming resistors: (designator, pin y, column x, value, Yageo number)
PROG = [('R105', 360, 560, '4.32K', 'RC0402FR-074K32L', 'ITERM: 0.03 A x 4.32k / 3.57k = 36 mA termination (15 % of the charge current)'),
        ('R104', 380, 610, '56.2K', 'RC0402FR-0756K2L', 'TMR: 10 x 56.2k x 48 s/k = 7.5 h fast-charge and 45 min precharge safety timers'),
        ('R103', 400, 660, '3.09K', 'RC0402FR-073K09L', 'ILIM: 1530 / 3.09k = 495 mA input current limit (EN2 = VU, EN1 = GND select the resistor)'),
        ('R102', 420, 710, '3.57K', 'RC0402FR-073K57L', 'ISET: 870 / 3.57k = 244 mA fast-charge current'),
        ('R106', 440, 760, '10K', 'RC0402FR-0710KL', 'TS: fixed 10k disables the pack-temperature check (2-pin pack, no NTC); the pack must carry its own protection')]
BUS_Y = 310

U8_SPEC = ('single-cell Li-ion/LiPo linear charger with power path, 16-pin VQFN 3 x 3 mm (RGT), IN 4.35-10.2 V with 10.5 V OVP, '
           'OUT 4.4 V regulated or VBAT - 60 mV on battery, input limit 495 mA (R103), charge 244 mA (R102), termination 36 mA (R105), '
           '7.5 h timer (R104), TS disabled with 10k (R106), CE and EN1 to GND, EN2 to VU; thetaJA 44.5 C/W; added 2026-09-09 in place of D1')
U8_NOTE = ('bq24232 (SLUS821J): USB5V0 into IN, OUT onto VU, battery on BAT/X4. With USB present OUT is 4.4 V (LDO) and the input is capped at '
           '495 mA: DPPM trims the charge current first, then the battery supplements the load; the board therefore never draws more than the '
           'limit from the port. On battery alone VU = VBAT - 60 mV, and the 3.3 V buck holds regulation down to about 3.45 V. The '
           '+5V-INPUT path through D2 still drives VU directly and does not charge the battery. Dissipation about 0.6 W worst case '
           '(0.3 W power path at 500 mA plus 0.3 W charging), a 27 C rise at 44.5 C/W. Battery-only start-up into the 40 uF on VU relies on '
           'the part\'s inrush sequence and the 250 mV / 250 us short-circuit detector: scope it on the first board. Footprint VQFN16-3X3-RGT '
           'to draw from the datasheet package drawing (3 x 3 mm, 0.5 mm pitch, 1.68 mm pad). Digi-Key 541 in stock at $1.93 on 2026-09-09.')
X4_SPEC = ('JST PH 2.0 mm, 2 circuits, top-entry SMT header with fixing tabs, 2 A, 100 V, -25..85 C, mates with PHR-2 housing; pin 1 = battery +, pin 2 = GND')
X4_NOTE = ('B2B-PH-SM4-TB(LF)(SN): 8 mm tall, wire leaves upward; the side-entry twin is S2B-PH-SM4-TB(LF)(SN) (5.5 mm). There is no polarity standard for '
           'JST-PH LiPo packs: check pin 1 = + against the pack before plugging in. Footprint JST-B2B-PH-SM4-TB to draw from the catalog page '
           '(two contact pads on 2.0 mm plus two 1.6 x 3.0 mm fixing pads). Digi-Key 57,541 in stock at $0.47 on 2026-09-09.')


def main(path):
    data = read_stream(path, 'FileHeader')
    recs = split(data)
    N = len(recs)
    desig = {owner_list_index(b): field(b, 'Text') for h, b in recs if b.startswith(b'|RECORD=34|')}

    def comp(d):
        m = [i for i, dd in desig.items() if dd == d]
        assert len(m) == 1, (d, m); return m[0]
    if 'U8' in desig.values():
        raise SystemExit('U8 already on the sheet; nothing done')
    d1 = comp('D1')
    assert field(recs[d1][1], 'LibReference') == 'DIODE'
    # ---- what goes: D1's tree and the cathode-to-VU wire ----
    kill = set(subtree(recs, d1))
    found = set()
    for i, (h, b) in enumerate(recs):
        p = wire_pts(b)
        if p and len(p) == 2 and (tuple(p[0]), tuple(p[1])) == ((260, 1037), (280, 1037)):
            kill.add(i); found.add('cathode wire')
    assert found == {'cathode wire'}, found
    # ---- templates, taken before renumbering ----
    templates = {}
    for d in ('R78', 'C78', 'LD5'):
        ci = comp(d); tree = subtree(recs, ci)
        templates[d] = (tree, [recs[i] for i in tree])
    x1 = comp('X1')
    pin_tpl = next(b for h, b in recs if b.startswith(b'|RECORD=2|') and owner_list_index(b) == x1 and field(b, 'Designator') == '3')
    # ---- renumber survivors ----
    keep = [i for i in range(N) if i not in kill]
    newpos = {old: new for new, old in enumerate(keep)}
    out = []
    for old in keep:
        h, b = recs[old]
        oi = owner_list_index(b)
        if oi is not None:
            assert oi in newpos, f'record {old} owned by a deleted record'
            b = set_field(b, 'OwnerIndex', str(newpos[oi] - 1))
        out.append([h, b])
    # ---- append helpers ----
    def add(body):
        body = body if isinstance(body, bytes) else body.encode()
        out.append([bytes(4), body + bytes(1)])
        return len(out) - 1
    def owner(idx): return str(idx - 1)
    def wire(pts):
        s = f'|RECORD=27|OwnerPartId=-1|LineWidth=1|Color=32768|UniqueID={uid()}|LocationCount={len(pts)}'
        for k, (x, y) in enumerate(pts, 1): s += f'|X{k}={x}|Y{k}={y}'
        add(s)
    def label(text, x, y, just=None):
        j = f'|Justification={just}' if just is not None else ''
        add(f'|RECORD=25{j}|OwnerPartId=-1|Location.X={x}|Location.Y={y}|Orientation=0|Color=128|FontID=4|Text={text}|UniqueID={uid()}')
    def junction(x, y):
        add(f'|RECORD=29|OwnerPartId=-1|Location.X={x}|Location.Y={y}|Color=128|Locked=T|UniqueID={uid()}')
    def gnd(x, y):
        add(f'|RECORD=17|OwnerPartId=-1|Style=4|ShowNetName=T|Location.X={x}|Location.Y={y}|Orientation=3|Color=128|FontID=1|Text=GND|UniqueID={uid()}')
    def note(text, x, y):
        add(f'|RECORD=4|OwnerPartId=-1|Location.X={x}|Location.Y={y}|Orientation=0|Color=8421504|FontID=3|Text={text}|UniqueID={uid()}')
    def pin(o, des, name, x, y, cong, elec):
        b = pin_tpl
        b = set_field(b, 'OwnerIndex', o); b = set_field(b, 'Designator', des); b = set_field(b, 'Name', name)
        b = set_field(b, 'Location.X', str(x)); b = set_field(b, 'Location.Y', str(y)); b = set_field(b, 'PinConglomerate', str(cong))
        b = set_field(b, 'PinLength', '30'); b = set_field(b, 'UniqueID', uid())
        b = set_field(b, 'Electrical', elec) if b'|Electrical=' in b else b.replace(b'|FormalType=1|', b'|FormalType=1|Electrical=' + elec.encode() + b'|', 1)
        add(b)
    def box(o, x0, y0, x1, y1):
        for (xa, ya, xb, yb) in ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)):
            add(f'|RECORD=6|OwnerIndex={o}|IsNotAccesible=T|OwnerPartId=1|LineWidth=1|Color=128|LocationCount=2|X1={xa}|Y1={ya}|X2={xb}|Y2={yb}|UniqueID={uid()}')
    def params(o, items, hidden=True):
        for nm, val in items:
            add(f'|RECORD=41|OwnerIndex={o}|IndexInSheet=-1|OwnerPartId=1|Color=8421504|FontID=3|IsHidden=T|Text={val}|Name={nm}|UniqueID={uid()}')
    def component(libref, desc, x, y, npins, designator, dx_des, dy_des, comment, dx_com, dy_com, footprint, prm):
        ci = add(f'|RECORD=1|LibReference={libref}|ComponentDescription={desc}|PartCount=2|DisplayModeCount=1|OwnerPartId=-1'
                 f'|Location.X={x}|Location.Y={y}|CurrentPartId=1|LibraryPath=*|SourceLibraryName=ctambe.IntLib|SheetPartFileName=*|TargetFileName=*'
                 f'|UniqueID={uid()}|AreaColor=11599871|Color=128|DesignatorLocked=T|PartIDLocked=T|DesignItemId={libref}|AllPinCount={npins}')
        o = owner(ci)
        params(o, prm)
        add(f'|RECORD=34|OwnerIndex={o}|IndexInSheet=-1|OwnerPartId=-1|Location.X={x + dx_des}|Location.Y={y + dy_des}|Color=8421504|FontID=3|Text={designator}|Name=Designator|ReadOnlyState=1|UniqueID={uid()}|OverrideNotAutoPosition=T')
        add(f'|RECORD=41|OwnerIndex={o}|IndexInSheet=-1|OwnerPartId=-1|Location.X={x + dx_com}|Location.Y={y + dy_com}|Color=8421504|FontID=3|Text={comment}|Name=Comment|UniqueID={uid()}|NotAutoPosition=T')
        i44 = add(f'|RECORD=44|OwnerIndex={o}')
        i45 = add(f'|RECORD=45|OwnerIndex={owner(i44)}|IndexInSheet=-1|ModelName={footprint}|ModelType=PCBLIB|IsCurrent=T|IntegratedModel=T|DatabaseModel=T|UniqueID={uid()}')
        add(f'|RECORD=46|OwnerIndex={owner(i45)}'); add(f'|RECORD=48|OwnerIndex={owner(i45)}')
        return ci, o
    def clone(tpl, new_desig, cx, cy, edits, footprint=None, libref=None):
        tree, trecs = templates[tpl]
        base = trecs[0][1]
        dx, dy = cx - int(field(base, 'Location.X')), cy - int(field(base, 'Location.Y'))
        pos = {}
        for old_i, (h, b) in zip(tree, trecs):
            if b.startswith(b'|RECORD=41|') and field(b, 'Name') == 'HiddenNetName':
                continue
            b2 = shift(new_uid(b), dx, dy)
            oi = owner_list_index(b)
            if oi is not None:
                b2 = set_field(b2, 'OwnerIndex', owner(pos[oi]))
            if b2.startswith(b'|RECORD=1|') and libref:
                b2 = set_field(set_field(b2, 'LibReference', libref), 'DesignItemId', libref) if b'|DesignItemId=' in b2 else set_field(b2, 'LibReference', libref)
            if b2.startswith(b'|RECORD=34|'):
                b2 = set_field(b2, 'Text', new_desig)
            if b2.startswith(b'|RECORD=41|'):
                nm = field(b2, 'Name')
                if nm in edits: b2 = set_field(b2, 'Text', edits[nm])
            if b2.startswith(b'|RECORD=45|') and footprint:
                b2 = set_field(b2, 'ModelName', footprint)
            pos[old_i] = add(b2)
    def resistor(des, cx, cy, value, mpn, spec):
        clone('R78', des, cx, cy, {'Comment': value, 'MANF#': mpn, 'SPEC': f'thick film +-1%, 1/16W, 0402 -- {spec}'})
    def cap(des, cx, cy):
        clone('C78', des, cx, cy, {'Comment': '4.7uF', 'MANF': 'Murata', 'MANF#': 'GRM188R61C475KE11D', 'DeviceName': 'C0603',
                                   'SPEC': 'X5R 16V +-10% 0603 4.7uF, 0.95 mm max (bq24232 IN/BAT bypass, datasheet 1-10 uF on IN and 4.7-47 uF on BAT)'},
              footprint='C0603', libref='C-GENERICC0603')
    def led(des, cx, cy, colour, mpn, spec, notetext):
        clone('LD5', des, cx, cy, {'Comment': colour, 'MANF#': mpn, 'SPEC': spec, 'NOTE': notetext})

    # ---- U8, the charger ----
    ci, o = component('BQ24232-RGT16', 'TI bq24232 single-cell Li-ion charger and power-path manager, 16-pin VQFN 3x3 (RGT) with thermal pad',
                      BX0, BY0, 17, 'U8', 0, BY1 - BY0 + 5, 'BQ24232 LiPo charger + power path', 60, BY1 - BY0 + 5, 'VQFN16-3X3-RGT',
                      [('GateName_1', 'G$1'), ('SymbolName_1', 'BQ24232'), ('DeviceName', 'RGT'), ('LibraryName', 'ctambe'), ('DeviceSetName', 'BQ24232'),
                       ('MANF', 'Texas Instruments'), ('MANF#', 'BQ24232RGTR'), ('SPEC', U8_SPEC), ('NOTE', U8_NOTE)])
    box(o, BX0, BY0, BX1, BY1)
    for des, name, y, elec in LEFT: pin(o, des, name, BX0, y, 58, elec)
    for des, name, y, elec in RIGHT: pin(o, des, name, BX1, y, 56, elec)
    # ---- X4, the battery connector ----
    ci, o = component('JST-B2B-PH-SM4-TB', 'JST PH 2.0 mm 2-pin top-entry SMT header, LiPo battery input',
                      700, 480, 2, 'X4', 0, 65, 'JST PH 2-pin, 1S LiPo', 0, -20, 'JST-B2B-PH-SM4-TB',
                      [('GateName_1', 'G$1'), ('SymbolName_1', 'CONN-2'), ('DeviceName', 'SM4-TB'), ('LibraryName', 'ctambe'), ('DeviceSetName', 'JST-PH-2'),
                       ('MANF', 'JST'), ('MANF#', 'B2B-PH-SM4-TB(LF)(SN)'), ('SPEC', X4_SPEC), ('NOTE', X4_NOTE)])
    box(o, 700, 480, 740, 540)
    pin(o, '1', 'BAT+', 700, 520, 58, '4'); pin(o, '2', 'GND', 700, 500, 58, '4')
    # ---- left side wiring ----
    wire([(270, 580), (180, 580)]); label('USB5V0', 180, 580, 2)                       # IN
    junction(210, 580); wire([(210, 580), (210, 570)]); cap('C150', 210, 560); wire([(210, 550), (210, 530)]); gnd(210, 530)
    wire([(270, 550), (240, 550)]); label('VU', 240, 550, 2)                            # EN2 high = ILIM mode
    wire([(270, 520), (250, 520)]); wire([(270, 500), (250, 500)]); wire([(250, 520), (250, 480)]); junction(250, 500); gnd(250, 480)   # CE, EN1
    wire([(270, 460), (150, 460)]); wire([(150, 460), (150, 470)])                      # PGOOD -> LD3 cathode
    led('LD3', 150, 490, 'green', 'LTST-C191KGKT', 'green indicator, 0603, Vf 2.1V max at 2mA', 'Charger power-good: bq24232 PGOOD sinks LD3 through R107 1.5k from VU when a valid USB input is present')
    wire([(150, 510), (150, 520)]); resistor('R107', 150, 530, '1.5K', 'RC0402FR-071K5L', 'PGOOD LED current: (4.4 - 2.1) / 1.5k = 1.5 mA'); wire([(150, 540), (150, 560)]); label('VU', 150, 560, 8)
    wire([(270, 440), (110, 440)]); wire([(110, 440), (110, 450)])                      # CHG -> LD4 cathode
    led('LD4', 110, 470, 'red', 'LTST-C191KRKT', 'red indicator, 0603, Vf 2.0V typ at 2mA', 'Charging: bq24232 CHG sinks LD4 through R108 1.5k from VU while the battery charges, off when done or disabled')
    wire([(110, 490), (110, 500)]); resistor('R108', 110, 510, '1.5K', 'RC0402FR-071K5L', 'CHG LED current: (4.4 - 2.0) / 1.5k = 1.6 mA'); wire([(110, 520), (110, 540)]); label('VU', 110, 540, 8)
    wire([(270, 380), (250, 380)]); wire([(270, 360), (250, 360)]); wire([(250, 380), (250, 340)]); junction(250, 360); gnd(250, 340)   # VSS, PAD
    # ---- right side wiring ----
    wire([(510, 580), (540, 580)]); wire([(510, 560), (540, 560)]); wire([(540, 560), (540, 580)]); label('VU', 540, 580)   # OUT x2
    wire([(510, 520), (670, 520)]); wire([(510, 500), (510, 520)]); junction(510, 520); label('VBATT', 530, 520)             # BAT x2 -> X4 pin 1
    junction(600, 520); wire([(600, 520), (600, 510)]); cap('C151', 600, 500); wire([(600, 490), (600, 470)]); gnd(600, 470)
    wire([(670, 500), (650, 500)]); wire([(650, 500), (650, 470)]); gnd(650, 470)      # X4 pin 2
    for des, y, cx, value, mpn, spec in PROG:
        wire([(510, y), (cx, y)]); wire([(cx, y), (cx, y - 10)]); resistor(des, cx, y - 20, value, mpn, spec); wire([(cx, y - 30), (cx, BUS_Y)])
    wire([(PROG[0][2], BUS_Y), (PROG[-1][2], BUS_Y)])
    for _, _, cx, _, _, _ in PROG[1:-1]: junction(cx, BUS_Y)
    wire([(660, BUS_Y), (660, BUS_Y - 10)]); gnd(660, BUS_Y - 10)
    # ---- notes ----
    note('2026-09-09: D1 (USB VBUS Schottky) replaced by U8, a TI bq24232 LiPo charger with power path: USB5V0 into IN, OUT onto VU (4.4 V on USB, VBAT - 60 mV on battery),', 300, 250)
    note('battery on X4 (JST PH 2.0 mm, pin 1 = +). Input limit 495 mA (R103), charge 244 mA (R102), termination 36 mA (R105), 7.5 h timer (R104), TS disabled (R106):', 300, 240)
    note('the pack needs its own protection. LD3 green = USB power good, LD4 red = charging. D2 still ORs +5V-INPUT onto VU without charging. Footprints VQFN16-3X3-RGT and JST-B2B-PH-SM4-TB to draw.', 300, 230)
    # ---- header weight, write ----
    out[0][1] = set_field(out[0][1], 'Weight', str(len(out) - 1))
    blob = join(out)
    write_stream(path, 'FileHeader', blob)
    assert read_stream(path, 'FileHeader') == blob
    print(f'{N} -> {len(out)} records ({len(kill)} deleted, {len(out) - (N - len(kill))} added)')


if __name__ == '__main__':
    main(sys.argv[2])
