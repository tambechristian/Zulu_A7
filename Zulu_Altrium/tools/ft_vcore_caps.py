# -*- coding: utf-8 -*-
"""Sheet 4, 2026-09-09: three 0.1 uF parts on the FT2232H core rail.

docs/connectivity_check.md found the only real gap in the power tree: FT-VCORE reaches four pins of
U2 (VCORE 12, 37 and 64, and VREGOUT 49, the output of the chip's own 1.8 V regulator) and carried
nothing but C39 and C139, two 4.7 uF parts. DS_FT2232H Figures 4.1 and 6.1 put a 100 nF at each
VCORE pin alongside that bulk. This adds three, one per pin.

They are GRM033R61A104KE15D in 0201, which is already the part behind the eight 0.1 uF and 100 nF
capacitors on this same sheet, so the bill of materials gains no line: that line goes from eight to
eleven. C136 is the clone template, being a 0201 already drawn vertically with vertical labels, so
the three sit in a row in the clear space to the left of C39 without disturbing anything.

Drawing: each capacitor hangs between the FT-VCORE rail at y = 1032 and its own ground port below,
exactly as C39 does. The rail, today a wire from x 162 to 462, is extended left to x 62, and
junctions are added where the three drops meet it and where the extension meets the old end. No net
label is added: the extension is one electrical wire with the rail, which existing FT-VCORE labels
already name, so there is nothing new to spell wrong.

Only appends, so no existing OwnerIndex moves; the header record count is rewritten. Refuses to
run twice.

    python tools/ft_vcore_caps.py tools "Imported zulu_a7.PrjPcb/zulu_a7_4.SchDoc"
"""
import sys, re, random, string
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

NEW = [('C152', 62), ('C153', 92), ('C154', 122)]     # designator, x; all at y 987, the C39 row
Y = 987
RAIL_Y = 1032
RAIL_LEFT_END = 162                                    # where the existing FT-VCORE wire starts today
TEMPLATE = 'C136'
COMMENT = '0.1uF'
SPEC = ('X5R 10V +-10% 0201 0.1uF, 0.30 mm max -- one per FT2232H VCORE pin, added 2026-09-09 after '
        'docs/connectivity_check.md found the core rail carrying bulk only')
NOTE = ('FT2232H core-rail decoupling. DS_FT2232H Figures 4.1 and 6.1 show a 100 nF at each VCORE pin '
        'besides the 4.7 uF bulk (C39, C139); the board had the bulk and none of these. Same part as the '
        'eight 0.1 uF and 100 nF 0201 capacitors already on this sheet, so no new BOM line. AT LAYOUT: put '
        'one beside each of pins 12, 37 and 64 with the shortest ground return you can manage -- that '
        'placement is the whole point of them.')
COORD = re.compile(rb'\|(Location\.X|Location\.Y|X\d+|Y\d+)=(-?\d+)')


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


def main(path):
    recs = split(read_stream(path, 'FileHeader'))
    N = len(recs)
    assert int(field(recs[0][1], 'Weight')) == N - 1, 'header count is already wrong'
    desig = {owner_list_index(b): field(b, 'Text') for h, b in recs if b.startswith(b'|RECORD=34|')}
    if any(d in desig.values() for d, _ in NEW):
        raise SystemExit('the FT-VCORE capacitors are already on the sheet; nothing done')
    tpl_i = [i for i, d in desig.items() if d == TEMPLATE]
    assert len(tpl_i) == 1, tpl_i
    tree = subtree(recs, tpl_i[0])
    tpl = [(h, bytes(b)) for h, b in (recs[i] for i in tree)]
    base = tpl[0][1]
    assert field(base, 'LibReference') == 'C-GENERICC0201', field(base, 'LibReference')
    # the rail we are extending must be where we think it is
    rail = [i for i, (h, b) in enumerate(recs)
            if wire_pts(b) and len(wire_pts(b)) == 2 and wire_pts(b)[0] == (RAIL_LEFT_END, RAIL_Y)]
    assert rail, f'no wire starts at ({RAIL_LEFT_END}, {RAIL_Y})'
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
            pos[old_i] = add(b2)
        for k, v in (('SPEC', SPEC), ('NOTE', NOTE)):          # the template may not carry them
            if k not in seen:
                add(f'|RECORD=41|OwnerIndex={owner(pos[tree[0]])}|IndexInSheet=-1|OwnerPartId=1|'
                    f'Color=8421504|FontID=3|IsHidden=T|Text={v}|Name={k}|UniqueID={uid()}')
        made.append((des, cx, pos[tree[0]]))
        add(f'|RECORD=17|OwnerPartId=-1|Style=4|ShowNetName=T|Location.X={cx}|Location.Y={Y - 20}|'
            f'Orientation=3|Color=128|FontID=1|Text=GND|UniqueID={uid()}')
        for pts in (((cx, Y - 20), (cx, Y - 10)), ((cx, Y + 10), (cx, RAIL_Y))):
            s = f'|RECORD=27|OwnerPartId=-1|LineWidth=1|Color=32768|UniqueID={uid()}|LocationCount=2'
            for k, (x, y) in enumerate(pts, 1):
                s += f'|X{k}={x}|Y{k}={y}'
            add(s)
    # extend the rail and pin the T-junctions
    s = (f'|RECORD=27|OwnerPartId=-1|LineWidth=1|Color=32768|UniqueID={uid()}|LocationCount=2'
         f'|X1={NEW[0][1]}|Y1={RAIL_Y}|X2={RAIL_LEFT_END}|Y2={RAIL_Y}')
    add(s)
    for x in [cx for _, cx in NEW[1:]] + [RAIL_LEFT_END]:
        add(f'|RECORD=29|OwnerPartId=-1|Location.X={x}|Location.Y={RAIL_Y}|Color=128|Locked=T|UniqueID={uid()}')
    out[0][1] = set_field(out[0][1], 'Weight', str(len(out) - 1))
    blob = join(out)
    write_stream(path, 'FileHeader', blob)
    assert read_stream(path, 'FileHeader') == blob
    print(f'sheet 4: {N} -> {len(out)} records; added {", ".join(d for d, _, _ in made)}')
    verify(path)


def verify(path):
    recs = split(read_stream(path, 'FileHeader'))
    assert int(field(recs[0][1], 'Weight')) == len(recs) - 1, 'header count'
    assert all(b.endswith(b'\x00') for h, b in recs), 'a record lost its terminator'
    uids = [field(b, 'UniqueID') for h, b in recs if field(b, 'UniqueID')]
    dup = sorted({u for u in uids if uids.count(u) > 1})
    assert not dup, f'duplicate UniqueIDs: {dup}'
    for i, (h, b) in enumerate(recs):
        oi = owner_list_index(b)
        if oi is not None:
            assert 0 <= oi < len(recs) and recs[oi][1].startswith((b'|RECORD=1|', b'|RECORD=2|', b'|RECORD=44|', b'|RECORD=45|')), (i, oi)
    desig = {owner_list_index(b): field(b, 'Text') for h, b in recs if b.startswith(b'|RECORD=34|')}
    wires = {wire_pts(b) for h, b in recs if b.startswith(b'|RECORD=27|')}
    juncs = {(num(b, 'Location.X'), num(b, 'Location.Y')) for h, b in recs if b.startswith(b'|RECORD=29|')}
    ports = {(num(b, 'Location.X'), num(b, 'Location.Y')): field(b, 'Text') for h, b in recs if b.startswith(b'|RECORD=17|')}
    for des, cx in NEW:
        ci = [i for i, d in desig.items() if d == des]
        assert len(ci) == 1, (des, ci)
        cb = recs[ci[0]][1]
        assert (num(cb, 'Location.X'), num(cb, 'Location.Y')) == (cx, Y), des
        pins = [b for h, b in recs if b.startswith(b'|RECORD=2|') and owner_list_index(b) == ci[0]]
        assert len(pins) == 2, des
        assert ((cx, Y - 20), (cx, Y - 10)) in wires and ((cx, Y + 10), (cx, RAIL_Y)) in wires, des
        assert ports.get((cx, Y - 20)) == 'GND', des
        assert field(cb, 'LibReference') == 'C-GENERICC0201', des
    assert ((NEW[0][1], RAIL_Y), (RAIL_LEFT_END, RAIL_Y)) in wires, 'the rail was not extended'
    for x in [cx for _, cx in NEW[1:]] + [RAIL_LEFT_END]:
        assert (x, RAIL_Y) in juncs, f'no junction at ({x}, {RAIL_Y})'
    print(f'verify: {len(recs)} records, {len(uids)} identifiers all distinct, '
          f'{", ".join(d for d, _ in NEW)} placed on the rail with their ground ports')


if __name__ == '__main__':
    main(sys.argv[2])
