# -*- coding: utf-8 -*-
"""Replace the LTC3569 section of the Power Supplies sheet with three fixed
SC189 bucks (Cmod A7 style), 2026-09-06.

    python tools/sc189_power_section.py <tools dir> "Imported zulu_a7.PrjPcb/zulu_a7_1.SchDoc"

Why: docs/power_budget.md.  The board is USB-A powered most of the time, so
the port, not the regulator, sets the budget; what the LTC3569 arrangement
did cost was a feedback divider per rail, an enable level the EN_BIAS network
never reached (VIH 1.2 V), and a 600 mA channel on one rail when running
from the external 5 V.  Three fixed SC189s (1.5 A each, 2.5 MHz, VIN 2.9-5.5 V)
need only an inductor and two capacitors each, and EN tied to VU.

Removed: U8 LTC3569, the dividers R65/R66, R68/R69, R71/R73 with their 20 pF
feed-forward caps C79/C81/C83, the EN_BIAS/MODE network Q3, R67, R70, R72,
R74, R75, R76, R79, and all their wiring.  PGOOD is gone; R77 now holds Q2's
gate at VCC3V3 so LD5 simply shows the 3.3 V rail.

Kept and re-used: L1/L2/L3 (all 1.5 uH, the DFE252010P-1R5M 1.8 A part; at
2.5 MHz that gives 0.21-0.30 A p-p ripple on every rail), C80/C82/C84 as the
22 uF outputs, C78 as VU bulk reduced to 10 uF (USB attach limit).  New:
U5 SC189Z 3.3 V, U6 SC189L 1.8 V, U7 SC189A 1.0 V, C147-C149 10 uF inputs.

SC189 SOT23-5 pinout as used on the Cmod A7 (SC189xSKTRT): 1 VIN, 2 GND,
3 EN, 4 VOUT (sense, tie to the output), 5 LX.  Confirm against the Semtech
datasheet before ordering; it was not reachable when this was written.

The sheet is rewritten record by record (see fix_text_orientation.py for the
format).  Component subtrees are cloned or shifted with all their children;
OwnerIndex values are renumbered after the deletions.
"""
import re, sys, random, string
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

def uid():
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(8))

def rec_type(b):
    m = re.match(rb'\|RECORD=(\d+)\|', b)
    return int(m.group(1)) if m else -1

COORD_KEYS = re.compile(rb'\|(Location\.X|Location\.Y|X\d+|Y\d+)=(-?\d+)')

def shift(b, dx, dy):
    def rep(m):
        k, v = m.group(1), int(m.group(2))
        if k == b'Location.X' or k.startswith(b'X'):
            v += dx
        else:
            v += dy
        return b'|' + k + b'=' + str(v).encode()
    return COORD_KEYS.sub(rep, b)

def new_uid(b):
    return re.sub(rb'\|UniqueID=[A-Z]{8}', b'|UniqueID=' + uid().encode(), b)

def owner_list_index(b):
    o = field(b, 'OwnerIndex')
    return int(o) + 1 if o is not None else None

def subtree(recs, comp_idx):
    """list indices of the component and every record that hangs off it"""
    members = {comp_idx}
    changed = True
    while changed:
        changed = False
        for i, (h, b) in enumerate(recs):
            oi = owner_list_index(b)
            if oi in members and i not in members:
                members.add(i); changed = True
    return sorted(members)

def main(path):
    data = read_stream(path, 'FileHeader')
    recs = split(data)
    N = len(recs)
    desig = {}
    for h, b in recs:
        if b.startswith(b'|RECORD=34|'):
            desig.setdefault(field(b, 'Text'), []).append(owner_list_index(b))
    comps_of = lambda d: desig.get(d, [])

    # ---------------------------------------------------------------- delete
    kill = set()
    for d in ('U8', 'Q3', 'R65', 'R66', 'R67', 'R68', 'R69', 'R70', 'R71', 'R72', 'R73',
              'R74', 'R75', 'R76', 'R79', 'C79', 'C81', 'C83'):
        for ci in comps_of(d):
            kill.update(subtree(recs, ci))
    loose = [1088, 1090, 1094, 1095, 1096, 1097, 1098, 1099, 1100, 1101, 1102, 1103, 1104, 1105,
             1107, 1108, 1109, 1111, 1112, 1113, 1114, 1115, 1116, 1117, 1118, 1119, 1120, 1121,
             1122, 1123, 1124, 1125, 1126, 1127, 1128, 1129, 1130, 1131, 1132, 1133, 1134, 1135,
             1136, 1137, 1138, 1139, 1140, 1141, 1142, 1143, 1144, 1145, 1146, 1147, 1148, 1149,
             1150, 1151, 1152, 1153, 1159, 1160, 1161, 1162, 1163, 1164, 1165, 1166, 1167, 1168,
             1169, 1170, 1171, 1172, 1173, 1174, 1175, 1176, 1177, 1178, 1179, 1180, 1181, 1182,
             1183, 1184, 1185, 1186, 1191, 1192, 1193, 1194, 1195, 1196, 1197, 1198, 1199, 1200,
             1201, 1202, 1203, 1204, 1205, 1206, 1207, 1208, 1209, 1210, 1211, 1212, 1213, 1214,
             1215, 1216, 1217, 1218, 1219, 1220, 1221, 1222, 1223, 1224, 1225, 1226, 1227, 1228,
             1237, 1238, 1245, 1246, 1247, 1248, 1249, 1250, 1251, 1252, 1253, 1254, 1255, 1256,
             1257, 1258, 1259, 1260, 1261, 1262, 1264, 1265, 1266, 1267, 1268, 1269, 1270, 1271,
             1272, 1273, 1274, 1275, 1276, 1277, 1278, 1282, 1283, 1284, 1285, 1286, 1287, 1293, 1294]
    for i in loose:
        t = rec_type(recs[i][1])
        assert t in (4, 17, 25, 27, 29, 22), f'record {i} is type {t}, not a loose drawing object'
        kill.add(i)
    # sanity: the loose list must not touch what we keep
    for i in (1087, 1089, 1091, 1092, 1093, 1106, 1110, 1154, 1155, 1156, 1157, 1158, 1188, 1189,
              1190, 1229, 1230, 1231, 1232, 1233, 1234, 1235, 1236, 1239, 1240, 1241, 1242, 1243,
              1244, 1263, 1279, 1280, 1281, 1295):
        assert i not in kill

    # ------------------------------------------------- templates (before renumbering)
    u8 = comps_of('U8')[0]
    pin_tpl = next(b for i, (h, b) in enumerate(recs)
                   if b.startswith(b'|RECORD=2|') and owner_list_index(b) == u8 and field(b, 'Name') == 'EN1')
    desig_tpl = next(b for h, b in recs if b.startswith(b'|RECORD=34|') and owner_list_index(b) == u8)
    l1 = comps_of('L1')[0]
    c82 = comps_of('C82')[0]
    c82_tree = [(recs[i][0], recs[i][1]) for i in subtree(recs, c82)]

    # ------------------------------------------------- edits to kept records
    def edit(i, fn):
        recs[i][1] = fn(recs[i][1])

    # L2/L3 -> 1.5 uH, C82/C84 -> 22 uF, C78 -> 10 uF, note text
    for d, old, new in (('L2', '3.3uH', '1.5uH'), ('L3', '2.2uH', '1.5uH'),
                        ('C82', '10uF', '22uF'), ('C84', '10uF', '22uF'), ('C78', '22uF 10V', '10uF 10V')):
        ci = comps_of(d)[0]
        for i in subtree(recs, ci):
            b = recs[i][1]
            if b.startswith(b'|RECORD=41|') and field(b, 'Name') == 'Comment' and field(b, 'Text') == old:
                edit(i, lambda b, new=new: set_field(b, 'Text', new))
    for i, (h, b) in enumerate(recs):
        if b.startswith(b'|RECORD=4|') and b'VCC3V3 moved to SW1' in b:
            edit(i, lambda b: set_field(b, 'Text',
                 '2026-09-06: LTC3569 section replaced by three fixed SC189 bucks (Cmod A7 style), EN tied to VU, no dividers, no sequencer; L1-L3 1.5uH, 22uF out, 10uF in; LD5 now shows VCC3V3. See docs/power_budget.md'))

    # ------------------------------------------------- block geometry
    BODY_X0, BODY_X1 = 465, 545
    blocks = [  # (index, by, rail, designator, part, suffix text, L, Cout, Cin designator)
        (0, 1030, 'VCC3V3', 'U5', 'SC189ZSKTRT', 'SC189Z', 'L1', 'C80', 'C147'),
        (1, 920,  'VCC1V8', 'U6', 'SC189LSKTRT', 'SC189L', 'L2', 'C82', 'C148'),
        (2, 810,  'VCC1V0', 'U7', 'SC189ASKTRT', 'SC189A', 'L3', 'C84', 'C149'),
    ]
    # move the inductors and output caps into place (still using old indices; shifting is index-free)
    for _, by, rail, _, _, _, L, Cout, _ in blocks:
        li = comps_of(L)[0]
        lx = int(field(recs[li][1], 'Location.X')); ly = int(field(recs[li][1], 'Location.Y'))
        for i in subtree(recs, li):
            edit(i, lambda b, dx=605 - lx, dy=(by + 30) - ly: shift(b, dx, dy))
        ci = comps_of(Cout)[0]
        cx = int(field(recs[ci][1], 'Location.X')); cy = int(field(recs[ci][1], 'Location.Y'))
        for i in subtree(recs, ci):
            edit(i, lambda b, dx=680 - cx, dy=(by + 20) - cy: shift(b, dx, dy))

    # ------------------------------------------------- renumber survivors
    keep = [i for i in range(N) if i not in kill]
    newpos = {old: new for new, old in enumerate(keep)}
    out = []
    for old in keep:
        h, b = recs[old]
        oi = owner_list_index(b)
        if oi is not None:
            assert oi in newpos, f'record {old} owned by deleted record {oi}'
            b = set_field(b, 'OwnerIndex', str(newpos[oi] - 1))
        out.append([h, b])

    # ------------------------------------------------- helpers to append records
    def add(body):
        body = body if isinstance(body, bytes) else body.encode()
        out.append([bytes(4), body + bytes(1)])   # every record ends with a NUL
        return len(out) - 1
    def owner(idx):
        return str(idx - 1)

    def wire(pts):
        s = f'|RECORD=27|OwnerPartId=-1|LineWidth=1|Color=32768|UniqueID={uid()}|LocationCount={len(pts)}'
        for k, (x, y) in enumerate(pts, 1):
            s += f'|X{k}={x}|Y{k}={y}'
        add(s)
    def label(text, x, y, just=None, font=4):
        s = f'|RECORD=25|OwnerPartId=-1|Location.X={x}|Location.Y={y}|Color=128|FontID={font}|Text={text}|UniqueID={uid()}'
        if just is not None:
            s = s.replace('|OwnerPartId', f'|Justification={just}|OwnerPartId', 1)
        add(s)
    def junction(x, y):
        add(f'|RECORD=29|OwnerPartId=-1|Location.X={x}|Location.Y={y}|Color=128|Locked=T|UniqueID={uid()}')
    def gnd(x, y):
        add(f'|RECORD=17|OwnerPartId=-1|Style=4|ShowNetName=T|Location.X={x}|Location.Y={y}|Orientation=3|Color=128|FontID=1|Text=GND|UniqueID={uid()}')

    def sc189(by, rail, d, part, name):
        ci = add(f'|RECORD=1|LibReference=SC189-SOT23-5|ComponentDescription=1.5A 2.5MHz synchronous buck, fixed output (Semtech SC189)'
                 f'|PartCount=2|DisplayModeCount=1|OwnerPartId=-1|Location.X={BODY_X0}|Location.Y={by}|CurrentPartId=1'
                 f'|LibraryPath=*|SourceLibraryName=ctambe.IntLib|SheetPartFileName=*|TargetFileName=*|UniqueID={uid()}|AreaColor=11599871|Color=128')
        o = owner(ci)
        for (x1, y1, x2, y2) in ((BODY_X0, by, BODY_X1, by), (BODY_X1, by, BODY_X1, by + 40),
                                  (BODY_X1, by + 40, BODY_X0, by + 40), (BODY_X0, by + 40, BODY_X0, by)):
            add(f'|RECORD=6|OwnerIndex={o}|IsNotAccesible=T|OwnerPartId=1|LineWidth=1|Color=128|LocationCount=2|X1={x1}|Y1={y1}|X2={x2}|Y2={y2}|UniqueID={uid()}')
        # pins: (designator, name, x, y, conglomerate, electrical)  58 = left, 56 = right, 59 = down
        for des, nm, x, y, cong, elec in (('1', 'VIN', BODY_X0, by + 30, 58, '7'), ('3', 'EN', BODY_X0, by + 10, 58, None),
                                          ('2', 'GND', BODY_X0 + 40, by, 59, '7'), ('5', 'LX', BODY_X1, by + 30, 56, '4'),
                                          ('4', 'VOUT', BODY_X1, by + 10, 56, None)):
            p = pin_tpl
            p = set_field(p, 'OwnerIndex', o)
            p = set_field(p, 'Name', nm); p = set_field(p, 'Designator', des)
            p = set_field(p, 'PinConglomerate', str(cong)); p = set_field(p, 'PinLength', '30')
            p = set_field(p, 'Location.X', str(x)); p = set_field(p, 'Location.Y', str(y))
            p = re.sub(rb'\|Electrical=\d+', b'', p)
            if elec:
                p = set_field(p, 'Electrical', elec)
            add(p)
        dd = desig_tpl
        dd = set_field(dd, 'OwnerIndex', o); dd = set_field(dd, 'Text', d)
        dd = set_field(dd, 'Location.X', str(BODY_X0)); dd = set_field(dd, 'Location.Y', str(by + 44))
        dd = re.sub(rb'\|Location\.[XY]_Frac=\d+', b'', dd)
        add(new_uid(dd))
        add(f'|RECORD=41|OwnerIndex={o}|OwnerPartId=1|Location.X={BODY_X0 + 40}|Location.Y={by + 22}|Justification=4|Color=128|FontID=4|Text={name}|Name=PartName|UniqueID={uid()}|NotAutoPosition=T')
        add(f'|RECORD=41|OwnerIndex={o}|IndexInSheet=-1|OwnerPartId=-1|Location.X={BODY_X0}|Location.Y={by - 8}|Color=8421504|FontID=3|IsHidden=T|Text={part}|Name=Comment|UniqueID={uid()}|NotAutoPosition=T')
        add(f'|RECORD=41|OwnerIndex={o}|OwnerPartId=1|Color=8421504|FontID=1|IsHidden=T|Text=Semtech|Name=MANF|UniqueID={uid()}')
        add(f'|RECORD=41|OwnerIndex={o}|OwnerPartId=1|Color=8421504|FontID=1|IsHidden=T|Text={part}|Name=MANF#|UniqueID={uid()}')
        li = add(f'|RECORD=44|OwnerIndex={o}')
        mi = add(f'|RECORD=45|OwnerIndex={owner(li)}|IndexInSheet=-1|ModelName=SOT23-5|ModelType=PCBLIB|IsCurrent=T|IntegratedModel=T|DatabaseModel=T|UniqueID={uid()}')
        add(f'|RECORD=46|OwnerIndex={owner(mi)}')
        add(f'|RECORD=48|OwnerIndex={owner(mi)}')

    def clone_cap(tree, new_desig, x, y):
        """clone C82's subtree as a 10 uF input cap at (x, y)"""
        base = tree[0][1]
        cx = int(field(base, 'Location.X')); cy = int(field(base, 'Location.Y'))
        dx, dy = x - cx, y - cy
        pos = {}
        for k, (h, b) in enumerate(tree):
            b2 = shift(new_uid(b), dx, dy)
            oi = owner_list_index(b)
            if oi is not None:
                b2 = set_field(b2, 'OwnerIndex', owner(pos[oi]))
            if b2.startswith(b'|RECORD=34|'):
                b2 = set_field(b2, 'Text', new_desig)
            if b2.startswith(b'|RECORD=41|') and field(b2, 'Name') == 'HiddenNetName':
                continue
            idx = add(b2)
            pos[c82_idx_map[k]] = idx
    c82_idx_map = subtree(recs, c82)  # original list indices of the template tree, same order as c82_tree

    # ------------------------------------------------- draw the three blocks
    for _, by, rail, d, part, name, L, Cout, Cin in blocks:
        sc189(by, rail, d, part, name)
        # left: VU -> VIN, EN tied to VIN, input cap
        wire([(405, by + 30), (435, by + 30)])
        wire([(435, by + 10), (435, by + 30)])
        junction(435, by + 30)
        label('VU', 412, by + 30)
        clone_cap(c82_tree, Cin, 405, by + 20)
        gnd(405, by + 10)
        # bottom: GND pin
        gnd(505, by - 30)
        # right: LX -> L -> rail; VOUT sense back to the rail; output cap
        wire([(575, by + 30), (585, by + 30)])
        wire([(625, by + 30), (700, by + 30)])
        wire([(575, by + 10), (650, by + 10)])
        wire([(650, by + 10), (650, by + 30)])
        junction(650, by + 30)
        junction(680, by + 30)
        gnd(680, by + 10)
        label(rail, 700, by + 30)
    # VU label on the surviving VU wire at C78
    label('VU', 340, 1037)

    hdr = out[0][1]
    out[0][1] = set_field(hdr, 'Weight', str(len(out) - 1))
    new = join(out)
    write_stream(path, 'FileHeader', new)
    assert read_stream(path, 'FileHeader') == new
    # verify ownership integrity
    chk = split(new)
    types = [rec_type(b) for h, b in chk]
    bad = 0
    for i, (h, b) in enumerate(chk):
        oi = owner_list_index(b)
        if oi is not None and not (0 < oi < len(chk)):
            bad += 1
    print(f'{N} -> {len(chk)} records ({len(kill)} deleted, {len(out) - len(keep)} added); components: {types.count(1)}; bad owners: {bad}')
    if bad:
        raise SystemExit('ownership broken')

if __name__ == '__main__':
    main(sys.argv[2])
