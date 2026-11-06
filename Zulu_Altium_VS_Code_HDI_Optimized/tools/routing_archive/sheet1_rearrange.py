# -*- coding: utf-8 -*-
"""Sheet 1 re-layout, 2026-09-09: the bq24232 charger block moves to the top under the USB
connector, the three SC189 regulator blocks and the VCC3V3 power-good circuit (LD5, R77, R78,
Q2) move to the bottom, X1's VBUS pin is wired straight into the charger's IN, and C78 (the
10 uF that sat on the old D1 cathode) becomes the OUT capacitor on U8 pins 10/11.

Mechanics: every record is classified by where it sits. The charger group (everything between
y 220 and 620 on the sheet as built by bq24232_charger.py) shifts up by 460; the regulator group
(everything at y >= 690 and x >= 330, including its dated note) shifts down by 500; the USB
connector and its wires stay. The USB5V0 stub that used to reach D1 and the VU feed stubs at
the old D1 cathode (with their junction, ground port and VU label) are deleted; C78's subtree
moves next to U8's OUT pins and is wired to them with its own ground port; X1's VBUS wire is
shortened to meet the IN wire; C151 moves 20 to the left so its ground port does not sit under
C78's. No component, parameter or net changes: the netlist must come out identical.
Refuses to run twice (looks for U8 below y 700).

    python tools/sheet1_rearrange.py tools "Imported zulu_a7.PrjPcb/zulu_a7_1.SchDoc"
"""
import sys, re, random, string
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

COORD_KEYS = re.compile(rb'\|(Location\.X|Location\.Y|X\d+|Y\d+)=(-?\d+)')


def uid():
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(8))


def shift(b, dx, dy):
    def rep(m):
        k, v = m.group(1), int(m.group(2))
        v += dx if (k == b'Location.X' or k.startswith(b'X')) else dy
        return b'|' + k + b'=' + str(v).encode()
    return COORD_KEYS.sub(rep, b)


def num(b, k):
    v = field(b, k); return int(v) if v is not None else None


def owner_list_index(b):
    o = field(b, 'OwnerIndex')
    return int(o) + 1 if o is not None else None


def wire_pts(b):
    if not b.startswith(b'|RECORD=27|'):
        return None
    n = num(b, 'LocationCount') or 0
    return [(num(b, f'X{k}'), num(b, f'Y{k}')) for k in range(1, n + 1)]


DY_CHARGER, DY_REGS = 460, -500
LOOSE = (b'|RECORD=27|', b'|RECORD=4|', b'|RECORD=28|', b'|RECORD=25|', b'|RECORD=17|', b'|RECORD=29|', b'|RECORD=22|')


def main(path):
    recs = split(read_stream(path, 'FileHeader'))
    N = len(recs)
    desig = {owner_list_index(b): field(b, 'Text') for h, b in recs if b.startswith(b'|RECORD=34|')}
    comps = {d: i for i, d in desig.items()}
    u8 = comps['U8']
    if num(recs[u8][1], 'Location.Y') >= 700:
        raise SystemExit('U8 is already at the top; nothing done')
    # subtree membership: list index -> root component index
    root = {}
    for i, (h, b) in enumerate(recs):
        oi = owner_list_index(b)
        if oi is None:
            if b.startswith(b'|RECORD=1|'): root[i] = i
            continue
        r = oi
        while owner_list_index(recs[r][1]) is not None:
            r = owner_list_index(recs[r][1])
        root[i] = r

    def region(x, y):
        if 220 <= y <= 620: return 'charger'
        if y >= 690 and x >= 330: return 'regs'
        return None
    # ---- deletions (content-matched) ----
    kill = set()
    dead_wires = {((360, 1017), (360, 1037)), ((360, 987), (360, 997)), ((280, 1037), (330, 1037)), ((330, 1037), (360, 1037)), ((160, 1037), (220, 1037))}
    found = set()
    for i, (h, b) in enumerate(recs):
        if owner_list_index(b) is not None: continue
        p = wire_pts(b)
        if p and len(p) == 2 and (tuple(p[0]), tuple(p[1])) in dead_wires:
            kill.add(i); found.add((tuple(p[0]), tuple(p[1])))
        elif b.startswith(b'|RECORD=29|') and (num(b, 'Location.X'), num(b, 'Location.Y')) == (360, 1037):
            kill.add(i); found.add('junction')
        elif b.startswith(b'|RECORD=17|') and (num(b, 'Location.X'), num(b, 'Location.Y')) == (360, 987):
            kill.add(i); found.add('c78 gnd')
        elif b.startswith(b'|RECORD=25|') and (num(b, 'Location.X'), num(b, 'Location.Y')) == (340, 1037) and field(b, 'Text') == 'VU':
            kill.add(i); found.add('vu label')
        elif b.startswith(b'|RECORD=25|') and (num(b, 'Location.X'), num(b, 'Location.Y')) == (203, 1037) and field(b, 'Text') == 'USB5V0':
            kill.add(i); found.add('usb label')
    assert len(found) == 9, found
    # ---- per-record shift vectors ----
    move = {}
    c78 = comps['C78']
    for i, (h, b) in enumerate(recs):
        if i in kill or i == 0: continue
        r = root.get(i)
        if r is not None:                                   # part of a component
            d = desig.get(r)
            if d == 'C78': move[i] = (260, 23)              # (360,1007) -> (620,1030): top pin on the OUT wire at y 1040
            elif d in ('X1', 'FRAME5') or d is None: continue
            else:
                cb = recs[r][1]; reg = region(num(cb, 'Location.X'), num(cb, 'Location.Y'))
                if reg == 'charger': move[i] = (0, DY_CHARGER)
                elif reg == 'regs': move[i] = (0, DY_REGS)
                else: raise SystemExit(f'component {d} in no group')
        elif b.startswith(LOOSE):
            p = wire_pts(b)
            pts = p if p else [(num(b, 'Location.X'), num(b, 'Location.Y'))]
            regs = {region(x, y) for x, y in pts}
            if regs == {'charger'}:
                dx = -20 if (all(x == 600 for x, y in pts) and all(y in (470, 490, 510, 520) for x, y in pts)) else 0   # C151 column
                move[i] = (dx, DY_CHARGER)
            elif regs == {'regs'}: move[i] = (0, DY_REGS)
            elif regs == {None}: continue                      # USB group and the title block stay
            else: raise SystemExit(f'loose record {i} straddles groups: {pts}')
    # C151 itself moves 20 left as well
    for i in range(N):
        if root.get(i) is not None and desig.get(root[i]) == 'C151': move[i] = (-20, DY_CHARGER)
    # ---- apply ----
    out = []
    keep = [i for i in range(N) if i not in kill]
    newpos = {old: new for new, old in enumerate(keep)}
    for old in keep:
        h, b = recs[old]
        if old in move: b = shift(b, *move[old])
        oi = owner_list_index(b)
        if oi is not None:
            assert oi in newpos, f'record {old} owned by a deleted record'
            b = set_field(b, 'OwnerIndex', str(newpos[oi] - 1))
        out.append([h, b])
    # ---- wire edits after the shift ----
    def find_wire(a, c):
        for i, (h, b) in enumerate(out):
            p = wire_pts(b)
            if p and len(p) == 2 and (tuple(p[0]), tuple(p[1])) == (a, c): return i
        raise SystemExit(f'wire {a}-{c} not found')
    def find_obj(rec, x, y, text=None):
        for i, (h, b) in enumerate(out):
            if b.startswith(rec) and (num(b, 'Location.X'), num(b, 'Location.Y')) == (x, y) and (text is None or field(b, 'Text') == text): return i
        raise SystemExit(f'object {rec} at {x},{y} not found')
    i = find_wire((160, 1037), (160, 1132)); out[i][1] = set_field(out[i][1], 'Y1', '1040')                      # X1 VBUS drop stops at the IN wire
    i = find_wire((270, 1040), (180, 1040)); out[i][1] = set_field(out[i][1], 'X2', '160')                       # IN wire meets it at the corner
    i = find_obj(b'|RECORD=25|', 180, 1040, 'USB5V0'); out[i][1] = set_field(set_field(out[i][1], 'Location.X', '200'), 'Justification', '0')
    i = find_wire((510, 1040), (540, 1040)); out[i][1] = set_field(out[i][1], 'X2', '620')                       # OUT wire runs on to C78
    i = find_obj(b'|RECORD=25|', 540, 1040, 'VU'); out[i][1] = set_field(out[i][1], 'Location.X', '550')
    def add(body):
        out.append([bytes(4), body.encode() + bytes(1)])
    add(f'|RECORD=29|OwnerPartId=-1|Location.X=540|Location.Y=1040|Color=128|Locked=T|UniqueID={uid()}')
    add(f'|RECORD=29|OwnerPartId=-1|Location.X=620|Location.Y=1040|Color=128|Locked=T|UniqueID={uid()}')
    add(f'|RECORD=27|OwnerPartId=-1|LineWidth=1|Color=32768|UniqueID={uid()}|LocationCount=2|X1=620|Y1=1020|X2=620|Y2=1010')
    add(f'|RECORD=17|OwnerPartId=-1|Style=4|ShowNetName=T|Location.X=620|Location.Y=1010|Orientation=3|Color=128|FontID=1|Text=GND|UniqueID={uid()}')
    out[0][1] = set_field(out[0][1], 'Weight', str(len(out) - 1))
    blob = join(out)
    write_stream(path, 'FileHeader', blob)
    assert read_stream(path, 'FileHeader') == blob
    print(f'{N} -> {len(out)} records ({len(kill)} deleted, 4 added, {len(move)} shifted)')


if __name__ == '__main__':
    main(sys.argv[2])
