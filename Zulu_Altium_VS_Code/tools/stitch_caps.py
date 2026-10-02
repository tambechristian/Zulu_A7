# -*- coding: utf-8 -*-
"""Sheet 3, 2026-09-24: five 100 nF parts that stitch VCC3V3 to GND for the L5 plane change.

WHY.  Stage 5 (docs/stage5_l5_plane.md) turned L5 from a second ground plane into the VCC3V3 plane.
The stack is Top / L2-GND / L3-SIG / L4-SIG / L5-VCC3V3 / Bottom with copper-face gaps 0.0994 /
0.1000 / 1.1208 / 0.1000 / 0.0994 mm, so Top and L3 reference L2-GND while L4 and Bottom reference
L5-VCC3V3.  Measured on the placed board, 52 signal vias join a layer referenced to one plane to a
layer referenced to the other, and **39 of them are SDRAM**.  Their return current can now cross
between the planes only through a VCC3V3-to-GND capacitor -- and the board had none anywhere in the
band x 12-39, y 6-25.4, which is exactly where U3 sits.  The median hop to the nearest such capacitor
was 3.30 mm and the worst 12.70 mm, against a median 1.62 mm to a GND via before the change.

These five close that gap.  **Their value is in where they sit, not in their capacitance**: each one
is a return path, so the layout coordinates and the length of the via-to-via loop at each part are
the specification, and they are recorded in docs/stage5b_stitching_caps.md.  Moving one to tidy the
board undoes the reason it exists.

THE PART.  Murata GRM033R61A104KE15D, X5R 10 V 0.1 uF 0201 -- already the board's 0201 100 nF on
eleven positions, so the bill of materials gains no line; that line goes from eleven to sixteen.
C136 on sheet 4 is the clone template: a 0201 already drawn vertically between VCC3V3 and GND.

DRAWING.  The five sit in a row in the clear band on sheet 3 (nothing else is drawn between y 190 and
y 410 across the whole sheet), each hanging between its own VCC3V3 port above and GND port below.
Explicit ports and wires, not the template's HiddenNetName parameters -- the same choice
tools/ft_vcore_caps.py made for C152-C154, and the one that demonstrably produced the right nets.

Only appends, so no existing OwnerIndex moves; the header record count is rewritten.  Refuses to run
twice.  Cross-sheet: the template records are read from sheet 4 and re-owned into sheet 3.

    python tools/stitch_caps.py tools "Imported zulu_a7.PrjPcb/zulu_a7_3.SchDoc" \
                                      "Imported zulu_a7.PrjPcb/zulu_a7_4.SchDoc"
"""
import sys, re, random, string
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

NEW = [('C155', 120), ('C156', 220), ('C157', 320), ('C158', 420), ('C159', 520)]
Y = 300                 # the capacitor row; pins sit at Y-10 (pin 1, GND) and Y+10 (pin 2, VCC3V3)
GND_PORT_Y = 280
PWR_PORT_Y = 320
TEMPLATE = 'C136'
COMMENT = '0.1uF'
SPEC = ('X5R 10V +-10% 0201 0.1uF, 0.30 mm max -- VCC3V3-to-GND return-path stitch for the L5 plane '
        'change, added 2026-09-24')
NOTE = (
    'RETURN-PATH STITCHING FOR THE L5 PLANE, NOT DECOUPLING.  L5 carries VCC3V3 and L2 carries GND, '
    'so a signal via that moves between an L2-referenced layer (Top, L3) and an L5-referenced one '
    '(L4, Bottom) has nowhere for its return current to go except through a VCC3V3-to-GND capacitor.  '
    'Fifty-two vias on this board do that and thirty-nine of them are the AS4C32M16SB bus; before '
    'these five parts the nearest such capacitor was a median of 3.30 mm and up to 12.70 mm away, '
    'because all forty-six sit in the y 3.0-4.2 row, round U1, or at x 2.6-7.6, and none was anywhere '
    'in x 12-39, y 6-25.4.  These five fill that hole: C155 (26.000,20.250) Top carries UDQM, CKE and '
    'A12; C156 (29.550,20.000) Bottom carries D10 and D11; C157 (39.050,18.000) Top carries D13 and '
    'is also the best path for D3 and D6; C158 (18.100,16.650) Top carries the west address row A5, '
    'A7, A9; C159 (23.300,7.500) Top carries the south control row BS0, RAS#, A0, A1, which had the '
    'worst return paths on the board.  THEIR VALUE IS IN THE PLACEMENT AND IN THE TWO VIAS BESIDE '
    'EACH ONE, NOT IN THE CAPACITANCE: with roughly 2 nH of mounting inductance a 100 nF 0201 '
    'self-resonates near 11 MHz, so at the 143 MHz bus clock and above the capacitance is irrelevant '
    'and the impedance is set entirely by the loop -- the unavoidable barrel across the 1.3512 mm '
    'L2-to-L5 cavity plus the pad-to-via tie, which is the one term a layout can shorten.  Each of '
    'these five is tied to its two planes by its own dedicated via 0.85-1.07 mm of copper away, '
    'against a 2.43 mm median for the other forty-six.  DO NOT move these parts, do not re-route or '
    'lengthen their stubs, do not delete either via, and do not substitute a larger case size: a 0402 '
    'would push the vias apart and undo the point.  If the value must change, smaller is better than '
    'larger.  Coordinates and the full measurement are in docs/stage5b_stitching_caps.md.')

COORD = re.compile(rb'\|(Location\.X|Location\.Y|X\d+|Y\d+)=(-?\d+)')
PORT_STYLE_GND = 4        # both styles read off the ports already on sheet 3
PORT_STYLE_PWR = 2


def uid():
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(8))


def new_uid(b):
    return re.sub(rb'\|UniqueID=[A-Z]{8}', lambda m: b'|UniqueID=' + uid().encode(), b)


def shift(b, dx, dy):
    def rep(m):
        k, v = m.group(1), int(m.group(2))
        v += dx if (k == b'Location.X' or k.startswith(b'X')) else dy
        return b'|' + k + b'=' + str(v).encode()
    return COORD.sub(rep, b)


def owner_list_index(b):
    o = field(b, 'OwnerIndex')
    return int(o) + 1 if o is not None else None


def num(b, k):
    v = field(b, k)
    return int(v) if v is not None else None


def wire_pts(b):
    if not b.startswith(b'|RECORD=27|'):
        return None
    n = num(b, 'LocationCount') or 0
    return tuple((num(b, f'X{k}'), num(b, f'Y{k}')) for k in range(1, n + 1))


def subtree(recs, root):
    members, changed = {root}, True
    while changed:
        changed = False
        for i, (h, b) in enumerate(recs):
            if owner_list_index(b) in members and i not in members:
                members.add(i); changed = True
    return sorted(members)


def main(target, source):
    src = split(read_stream(source, 'FileHeader'))
    sdes = {owner_list_index(b): field(b, 'Text') for h, b in src if b.startswith(b'|RECORD=34|')}
    tpl_i = [i for i, d in sdes.items() if d == TEMPLATE]
    assert len(tpl_i) == 1, ('template %s not unique on the source sheet' % TEMPLATE, tpl_i)
    tree = subtree(src, tpl_i[0])
    tpl = [(h, bytes(b)) for h, b in (src[i] for i in tree)]
    base = tpl[0][1]
    assert field(base, 'LibReference') == 'C-GENERICC0201', field(base, 'LibReference')
    assert field(base, 'DesignItemId') == 'C-GENERICC0201', field(base, 'DesignItemId')

    recs = split(read_stream(target, 'FileHeader'))
    N = len(recs)
    assert int(field(recs[0][1], 'Weight')) == N - 1, 'header count is already wrong'
    desig = {owner_list_index(b): field(b, 'Text') for h, b in recs if b.startswith(b'|RECORD=34|')}
    if any(d in desig.values() for d, _ in NEW):
        raise SystemExit('the stitching capacitors are already on the sheet; nothing done')
    # the row must be empty: nothing on the target sheet may sit in the band we are drawing into
    for h, b in recs:
        x, y = num(b, 'Location.X'), num(b, 'Location.Y')
        if x is not None and y is not None and GND_PORT_Y - 20 <= y <= PWR_PORT_Y + 20 \
           and NEW[0][1] - 40 <= x <= NEW[-1][1] + 40:
            raise SystemExit('the target band is not clear: an object sits at (%d, %d)' % (x, y))

    out = [[h, b] for h, b in recs]

    def add(body):
        out.append([bytes(4), (body if isinstance(body, bytes) else body.encode()) + bytes(1)])
        return len(out) - 1

    def owner(idx):
        return str(idx - 1)

    made = []
    for des, cx in NEW:
        dx, dy = cx - num(base, 'Location.X'), Y - num(base, 'Location.Y')
        pos, seen = {}, set()
        for old_i, (h, b) in zip(tree, tpl):
            # the template's pins carry HiddenNetName GND / VCC3V3; we draw real ports instead, the
            # same choice ft_vcore_caps.py made for C152-C154
            if b.startswith(b'|RECORD=41|') and field(b, 'Name') == 'HiddenNetName':
                continue
            b2 = shift(new_uid(b), dx, dy)
            oi = owner_list_index(b)
            if oi is not None:
                b2 = set_field(b2, 'OwnerIndex', owner(pos[oi]))
            if b2.startswith(b'|RECORD=34|'):
                b2 = set_field(b2, 'Text', des)
            if b2.startswith(b'|RECORD=41|'):
                nm = field(b2, 'Name')
                seen.add(nm)
                for k, v in (('Comment', COMMENT), ('SPEC', SPEC), ('NOTE', NOTE)):
                    if nm == k:
                        b2 = set_field(b2, 'Text', v)
                # a clone must not inherit the template's pin identifiers.  Sheets 0-3, 5 and 6 hold
                # 38821 PinUniqueId values with no duplicate at all; only sheet 4 has 16, left behind
                # by an earlier clone that did not do this.  Sheet 3 stays clean.
                if nm == 'PinUniqueId':
                    b2 = set_field(b2, 'Text', uid())
            pos[old_i] = add(b2)
        for k, v in (('SPEC', SPEC), ('NOTE', NOTE)):
            if k not in seen:
                add('|RECORD=41|OwnerIndex=%s|IndexInSheet=-1|OwnerPartId=1|Color=8421504|FontID=3|'
                    'IsHidden=T|Text=%s|Name=%s|UniqueID=%s' % (owner(pos[tree[0]]), v, k, uid()))
        made.append((des, cx, pos[tree[0]]))
        # GND below, VCC3V3 above -- pin 1 is at (cx, Y-10) and pin 2 at (cx, Y+10)
        add('|RECORD=17|OwnerPartId=-1|Style=%d|ShowNetName=T|Location.X=%d|Location.Y=%d|'
            'Orientation=3|Color=128|FontID=1|Text=GND|UniqueID=%s' % (PORT_STYLE_GND, cx, GND_PORT_Y, uid()))
        add('|RECORD=17|OwnerPartId=-1|Style=%d|ShowNetName=T|Location.X=%d|Location.Y=%d|'
            'Orientation=1|Color=128|FontID=1|Text=VCC3V3|UniqueID=%s' % (PORT_STYLE_PWR, cx, PWR_PORT_Y, uid()))
        for pts in (((cx, GND_PORT_Y), (cx, Y - 10)), ((cx, Y + 10), (cx, PWR_PORT_Y))):
            s = ('|RECORD=27|OwnerPartId=-1|LineWidth=1|Color=32768|UniqueID=%s|LocationCount=2' % uid())
            for k, (x, y) in enumerate(pts, 1):
                s += '|X%d=%d|Y%d=%d' % (k, x, k, y)
            add(s)

    out[0][1] = set_field(out[0][1], 'Weight', str(len(out) - 1))
    blob = join(out)
    write_stream(target, 'FileHeader', blob)
    assert read_stream(target, 'FileHeader') == blob
    print('%s: %d -> %d records; added %s'
          % (target.split('/')[-1], N, len(out), ', '.join(d for d, _, _ in made)))
    verify(target)


def verify(path):
    recs = split(read_stream(path, 'FileHeader'))
    assert int(field(recs[0][1], 'Weight')) == len(recs) - 1, 'header count'
    assert all(b.endswith(b'\x00') for h, b in recs), 'a record lost its terminator'
    uids = [field(b, 'UniqueID') for h, b in recs if field(b, 'UniqueID')]
    dup = sorted({u for u in uids if uids.count(u) > 1})
    assert not dup, 'duplicate UniqueIDs: %s' % dup
    pids = [field(b, 'Text') for h, b in recs
            if b.startswith(b'|RECORD=41|') and field(b, 'Name') == 'PinUniqueId']
    pdup = sorted({u for u in pids if pids.count(u) > 1})
    assert not pdup, 'duplicate PinUniqueIds: %s' % pdup
    for i, (h, b) in enumerate(recs):
        oi = owner_list_index(b)
        if oi is not None:
            assert 0 <= oi < len(recs) and recs[oi][1].startswith(
                (b'|RECORD=1|', b'|RECORD=2|', b'|RECORD=44|', b'|RECORD=45|')), (i, oi)
    desig = {owner_list_index(b): field(b, 'Text') for h, b in recs if b.startswith(b'|RECORD=34|')}
    wires = {wire_pts(b) for h, b in recs if b.startswith(b'|RECORD=27|')}
    ports = {(num(b, 'Location.X'), num(b, 'Location.Y')): field(b, 'Text')
             for h, b in recs if b.startswith(b'|RECORD=17|')}
    for des, cx in NEW:
        ci = [i for i, d in desig.items() if d == des]
        assert len(ci) == 1, (des, ci)
        cb = recs[ci[0]][1]
        assert (num(cb, 'Location.X'), num(cb, 'Location.Y')) == (cx, Y), des
        assert field(cb, 'LibReference') == 'C-GENERICC0201', des
        pins = [b for h, b in recs if b.startswith(b'|RECORD=2|') and owner_list_index(b) == ci[0]]
        assert len(pins) == 2, (des, len(pins))
        assert ((cx, GND_PORT_Y), (cx, Y - 10)) in wires, des
        assert ((cx, Y + 10), (cx, PWR_PORT_Y)) in wires, des
        assert ports.get((cx, GND_PORT_Y)) == 'GND', des
        assert ports.get((cx, PWR_PORT_Y)) == 'VCC3V3', des
        params = {field(b, 'Name'): field(b, 'Text') for h, b in recs
                  if b.startswith(b'|RECORD=41|') and owner_list_index(b) == ci[0]}
        assert params.get('MANF#') == 'GRM033R61A104KE15D', (des, params.get('MANF#'))
        assert params.get('Comment') == COMMENT, (des, params.get('Comment'))
        assert params.get('DeviceName') == 'C0201', (des, params.get('DeviceName'))
        assert 'HiddenNetName' not in params, des
    print('verify: %d records, %d identifiers all distinct, %s each between a VCC3V3 port and a GND '
          'port with MANF# GRM033R61A104KE15D'
          % (len(recs), len(uids), ', '.join(d for d, _ in NEW)))


if __name__ == '__main__':
    main(sys.argv[2], sys.argv[3])
