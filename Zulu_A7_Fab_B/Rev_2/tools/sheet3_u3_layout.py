"""Sheet 3 (zulu_a7_3.SchDoc, title block "Memory") of Zulu A7 Fab B, 2026-11-18: redraw U3 (AS4C32M16SB-7TCN,
54-pin TSOP-II SDRAM) as one readable block -- the no-PMOD board's layout (Zulu_A7_no_pmod/Rev_2/tools/
sheet3_u3_layout.py) without its DQ series resistors.

WHY.  U3 came from EAGLE as 55 parts (part 1 = the "U3" text, parts 2-55 = one pin each). The signal pins sat in a box
at the top right and the 14 power pins in a separate column block with C3-C9, each cap joined to its pins only by
GND / VCC3V3 ports.

WHAT (no connection changes; the script proves the sheet's nets are identical before and after).
- One box, x XL..XR, y YBOT..YTOP (the no-PMOD frame, pin for pin):
    right edge  DQ0-DQ7, LDQM, DQ8-DQ15, UDQM at 20-unit pitch, each on a short stub with its existing net label
                (D0-D15, LDQM, UDQM). Fab B has no DQ series resistors (R119-R134 are a no-PMOD addition), so
                nothing sits between -- the right edge is drawn like the left one, as on the Asar Feather sheet.
    left edge   A0-A12, BS0/BS1, CS#/RAS#/CAS#/WE#, CKE/CLK, NC, each with its existing net label on a short stub.
    top edge    the 7 supply pins (1, 3, 9, 14, 27, 43, 49), each WIRED up to its decoupling cap and on to one VCC3V3
                rail with a single port.
    bottom edge the 7 ground pins, each directly under the supply pin it faces in the TSOP (pin 55-n), with a GND port.
  The caps keep their pairing: Cn sits on the supply pin of its old row. Their "0.1uF" comments are hidden (a
  caption gives the value): at this pitch the text runs into the next column's GND port.
- Each U3 pin part is moved rigidly (rotated about its pin's hot end, new part Orientation), its visible pin name
  placed inside the box. Caps are translated only. U3's designator and comment are centred in the box (bottom-centre
  justified, the Asar review fix of the no-PMOD port's left-anchored guess).
- Old stubs, labels, ports and junctions of U3 and the caps are deleted and redrawn; the four old box lines are
  reused. The microSD note frame is narrowed and the two long X3 note lines are wrapped so nothing overlaps; the X3
  note's stale "Needs its own footprint on the PCB" becomes "PCB footprint DM3D-SF" (X3 is on DM3D-SF on both Fab B
  PcbDocs).
- U4, R2, R6, R7 and C11 (today's U4 drawing fix: C11 on the jog of U4's pin-8 wire) are not touched.

The input is checked by the MD5 of its FileHeader stream, so the script runs on the Rev_1 or the Rev_2 copy (the two
files differ outside that stream).

    python tools/sheet3_u3_layout.py <sheet 3 in> <sheet 3 out>      (in == out to edit in place)
    python tools/sheet3_u3_layout.py --verify <before> <after>
"""
import hashlib
import importlib.util
import os
import shutil
import sys

ASAR_TOOLS = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1/tools'
sys.path.insert(0, ASAR_TOOLS)
from schdoc import delete, field, join, owner, read_stream, set_field, split, write_stream  # noqa: E402

# the generic helpers of the Asar port (same code as the no-PMOD script's), loaded under their own module name
_spec = importlib.util.spec_from_file_location('asar_sheet3_u3_layout', os.path.join(ASAR_TOOLS, 'sheet3_u3_layout.py'))
_asar = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_asar)
num, fval, set_f, set_or_drop, drop_key, uid = _asar.num, _asar.fval, _asar.set_f, _asar.set_or_drop, _asar.drop_key, _asar.uid
hot_end, rot, move_part, seg_has = _asar.hot_end, _asar.rot, _asar.move_part, _asar.seg_has
net_map, report = _asar.net_map, _asar.report

SRC_STREAM_MD5 = '951ed07c9226fb02004755632c1e3cbd'     # FileHeader of Fab B Rev_1 and Rev_2 zulu_a7_3.SchDoc
XL, XR, YTOP, YBOT = 555, 875, 1010, 610
PIN_L = 20
STUB = 10
RIGHT = [('2', 990), ('4', 970), ('5', 950), ('7', 930), ('8', 910), ('10', 890), ('11', 870), ('13', 850), ('15', 830),
         ('42', 790), ('44', 770), ('45', 750), ('47', 730), ('48', 710), ('50', 690), ('51', 670), ('53', 650), ('39', 630)]
LEFT = [('23', 970), ('24', 960), ('25', 950), ('26', 940), ('29', 930), ('30', 920), ('31', 910), ('32', 900),
        ('33', 890), ('34', 880), ('22', 870), ('35', 860), ('36', 850), ('20', 830), ('21', 820), ('19', 810), ('18', 800),
        ('17', 790), ('16', 780), ('37', 770), ('38', 760), ('40', 750)]      # below R6's VCC3V3 port at (525, 987)
SUPPLY = ['1', '3', '9', '14', '27', '43', '49']          # top edge, left to right
COL_X = [XL + 10 + 45 * k for k in range(7)]   # last column's vertical name clears DQ0/DQ1 and UDQM
CAP_Y, VCC_Y = YTOP + PIN_L + 35, YTOP + PIN_L + 55       # cap row, VCC3V3 rail (one port, at the east end)
CAPS = ('C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9')
DQ_BIT = {'2': 0, '4': 1, '5': 2, '7': 3, '8': 4, '10': 5, '11': 6, '13': 7,
          '42': 8, '44': 9, '45': 10, '47': 11, '48': 12, '50': 13, '51': 14, '53': 15}
RIGHT_LABEL = dict({d: 'D%d' % b for d, b in DQ_BIT.items()}, **{'15': 'LDQM', '39': 'UDQM'})
CAPTION = [(XL, YBOT - PIN_L - 50, 'C3-C9: 0.1 uF, one on each supply pin above; the ground pin below'),
           (XL, YBOT - PIN_L - 60, 'is the one it faces in the TSOP (pin 55-n).')]
WIRE = 'LineWidth=1|Color=32768'
SD_FRAME_CORNER_X, SD_FRAME_BOTTOM, SD_FRAME_TOP = 500, 600, 755
X3_LINES = [(70, 590, '2026-09-06: X3 is now the Hirose DM3D-SF push-pull socket'),
            (70, 580, '(HRS 609-0025-8), DM3 catalog p9. Same 8-contact pinout;'),
            (70, 570, 'shell pads G1-G4 to GND; card-detect switch A/B (closed with'),
            (70, 560, 'card) left open. PCB footprint DM3D-SF.')]   # the old "needs its own footprint" is stale


def main(src, dst):
    raw = read_stream(src)
    if hashlib.md5(raw).hexdigest() != SRC_STREAM_MD5:
        raise SystemExit('%s is not the expected Fab B sheet 3 (FileHeader md5 %s)' % (src, SRC_STREAM_MD5))
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
    assert not [des.get(i) for i in comps if (des.get(i) or '') in ['R%d' % n for n in range(119, 135)]], \
        'this sheet carries DQ series resistors: it is not Fab B'

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
        d = field(R[pins[0]][1], 'Designator')
        assert d not in u3, d
        u3[d] = dict(root=i, pin=pins[0], gate=gate[0])
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
        assert len(names) <= 1, (d, names)
        label[d] = names.pop() if names else None

    # ---- caps C3-C9: which supply pin's row each sits on, and which cap pin is the GND side --------------------------
    caps = {}
    for i in comps:
        ref = des.get(i)
        if ref not in CAPS:
            continue
        cpins = {field(R[k][1], 'Designator'): hot_end(R[k][1]) for k in kids[i] if field(R[k][1], 'RECORD') == '2'}
        row = [d for d in SUPPLY if abs(old_hot[d][1] - cpins['1'][1]) < 1e-6]
        assert len(row) == 1, (ref, cpins, row)
        assert cpins['1'][0] < cpins['2'][0], (ref, 'pin 2 is on the ground side; this layout puts pin 1 there')
        caps[row[0]] = dict(root=i, ref=ref, centre=((cpins['1'][0] + cpins['2'][0]) / 2, cpins['1'][1]))
    assert sorted(caps) == sorted(SUPPLY) and [caps[s]['ref'] for s in SUPPLY] == list(CAPS), caps
    ground_of = {s: str(55 - int(s)) for s in SUPPLY}
    for s in SUPPLY:                                   # the old rows paired supply and ground pins at the same y
        assert abs(old_hot[s][1] - old_hot[ground_of[s]][1]) < 1e-6, (s, ground_of[s])

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
        R[v['root']][1] = set_or_drop(R[v['root']][1], 'Orientation', o_new)
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
        R[v['gate']][1] = set_or_drop(set_or_drop(g, 'Orientation', orient), 'Justification', just)

    # U3 designator and comment in the middle of the box, bottom-centre justified (the no-PMOD script anchored them
    # left at a guessed text width, which left the comment ~19 units off centre; the Asar review fixed it this way)
    n_cen = 0
    for k in kids[u3['part1']]:
        b = R[k][1]
        if field(b, 'IsHidden') == 'T' or fval(b, 'Location.X') is None:
            continue
        if field(b, 'Name') == 'PART' and field(b, 'Text') == 'U3':
            b = set_f(set_f(b, 'Location.X', (XL + XR) / 2), 'Location.Y', (YTOP + YBOT) / 2 + 6)
            R[k][1] = set_or_drop(b, 'Justification', 1)
            n_cen += 1
        elif field(b, 'Name') == 'Comment':
            b = set_f(set_f(b, 'Location.X', (XL + XR) / 2), 'Location.Y', (YTOP + YBOT) / 2 - 8)
            R[k][1] = set_or_drop(b, 'Justification', 1)
            n_cen += 1
    assert n_cen == 2, n_cen

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
    for d, y in RIGHT:
        assert label[d] == RIGHT_LABEL[d], (d, label[d])
        wire((XR + PIN_L, y), (XR + PIN_L + STUB, y))
        netlabel((XR + PIN_L + STUB, y), label[d])
    # left edge: stub + label (NC stays open)
    for d, y in LEFT:
        if label[d] is None:
            assert d == '40', d
            continue
        wire((XL - PIN_L, y), (XL - PIN_L - STUB, y))
        netlabel((XL - PIN_L - STUB, y), label[d], 2)
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
    uids = [field(b, 'UniqueID') for h, b in R if field(b, 'UniqueID')]
    assert len(uids) == len(set(uids)), 'duplicate UniqueID'
    blob = join(R)
    if os.path.abspath(dst) != os.path.abspath(src):
        shutil.copyfile(src, dst)
    write_stream(dst, blob)
    assert read_stream(dst) == blob
    print('%s: %d records -> %d (deleted %d, added %d)' % (os.path.basename(dst), len(split(raw)), len(R), len(drop), len(new)))
    report(before, net_map(split(read_stream(dst))))


if __name__ == '__main__':
    if sys.argv[1] == '--verify':
        report(net_map(split(read_stream(sys.argv[2]))), net_map(split(read_stream(sys.argv[3]))))
    else:
        main(sys.argv[1], sys.argv[2])
