# -*- coding: utf-8 -*-
"""Sheet 4, 2026-09-09: the JTAG series resistors and the two configuration pull-ups become arrays.

Six discrete 100 ohm resistors -- R9 PROG#, R38 DONE, R8 TDI, R37 TDO, R4 TMS and R36 TCK -- become
elements of ONE package, and the two 4.7 K pull-ups R1 (INIT_B) and R3 (PROGRAM_B) become the two
elements of another. This is where the design came from: the component description on every one of
these parts still says "Same R1NV0 symbol the RES4 and RES8 arrays drew their elements with, so a
part split out of an array keeps the exact symbol, pin span and position it had on the sheet and not
one wire has to move". They were split out of arrays during the EAGLE work; they go back into arrays
now, and because the symbol never changed, no wire moves this time either.

THE SIX GO INTO AN EIGHT. A 6-element isolated array is a real catalogue part and not a buyable one:
CTS 753123101GP is 12 terminals, 6 isolated elements, 100 ohm, and Digi-Key holds zero, quotes 28
weeks at MOQ 1000 and $2.63 each -- and its 12-SRT body, 8.76 x 2.03 mm, is bigger than the 8-element
chip array anyway. So the six sit in a CTS 742C163101JP, 16 terminals, 8 isolated elements, with two
elements spare at the far end of the body. That is the same 74x concave family as R34, the array
already on sheet 3, and CTS publishes one recommended land pattern for the whole 742 family, so all
three arrays on this board share a pad cell: 0.45 x 0.80 mm pads on 0.80 mm pitch. The pull-up pair
is a 742C043472JP from the same family, 4 terminals, 2 isolated elements.

HOW AN ARRAY IS DRAWN IN THIS PROJECT. Copy R34: ONE RECORD=1 per placed element, all sharing a
designator, each carrying the whole pin set of the package as children and differing only in
CurrentPartId. Altium shows the pins whose OwnerPartId matches CurrentPartId and appends the gate
letter to the designator, so the six read R4A..R4F and the two read R1A/R1B. PartCount is the
element count plus one. Isolated arrays number their pads so element k joins pad k to pad 2N+1-k,
which puts every bridge-side net on pads 1..6 and every FPGA-side net on pads 16..11 -- one long side
of the package per side of the link -- and leaves the two unplaced elements holding pads 7..10.

WHICH ELEMENT IS WHICH. Gate A is the topmost on the sheet and they run down in order, as R34's do,
which is also the order they were asked for: A PROG#, B DONE, C TDI, D TDO, E TMS, F TCK. That puts
TCK, the only clock in the group, at the end of the used run, with TMS on one side and a spare
element on the other.

Every pin gets a freshly minted PinUniqueId -- the trap tools/sc189_pin_ids.py had to clean up after
-- and the imported HiddenNetName parameters are dropped rather than copied, since they are stale
EAGLE artifacts (R34 still claims all four of its elements sit on SD-DAT0) and nothing reads them.

The netlist changes by design: eight components become two and every pad on them is renamed, but the
net count and the placed pad count both come out unchanged. Deleting records renumbers every later
OwnerIndex and rewrites the header count. Refuses to run twice. Run tools/sheet4_layout.py FIRST --
it moves R3 and R1, and this script preserves whatever positions it finds.

    python tools/resistor_packs.py tools "Imported zulu_a7.PrjPcb/zulu_a7_4.SchDoc"
"""
import sys, re, random, string
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

# --------------------------------------------------------------------------- the two packages --
PACKS = [
    dict(designator='R4', elements=8, used=['R9', 'R38', 'R8', 'R37', 'R4', 'R36'],
         libref='RES8742', description='Resistor 8-pack   Package of eight resistors, six used.',
         footprint='742C163', comment='100',
         DeviceName='742', LibraryName='ctambe', DeviceSetName='RES8',
         MANF='CTS', SPEC='8 x 100 ohm +-5% isolated array, 2506 concave 6.40 x 1.60 mm, 0.80 mm '
                          'pitch, 63 mW per element; six elements used, two spare',
         NOTE='The six 100 ohm series resistors between the FT2232H and the FPGA in one package: A PROG#, B DONE, C TDI, D TDO, E TMS, F TCK, in the order they are drawn down the sheet. Pads 1-6 face the bridge and pads 16-11 face the FPGA, one long side of the body per end of the link. TWO ELEMENTS ARE SPARE (pads 7-10); they sit at the far end of the body, so the six used run contiguously from pad 1. Leave the spare pads unconnected. There is no purchasable 6-element part: CTS 753123101GP is a genuine 12-terminal, 6-isolated-element, 100 ohm array, but Digi-Key holds none, quotes 28 weeks at MOQ 1000 and $2.63 each, and its 12-SRT body is 8.76 x 2.03 mm, LARGER than this 8-element chip array. Same CTS 74x concave family as R34, so all three arrays on the board answer to one CTS land-pattern rule (0.45 x 0.80 mm pads, 0.80 mm pitch, 2.60 mm across). 5 percent like R34: the 742C163 has no 1 percent option, which series damping does not care about, and 63 mW per element is twenty times the worst case. Alternate if the layout needs the length back: Panasonic EXB-2HV101JV is the same 8 x 100 ohm isolated in 3.80 x 1.60 mm, but convex terminals on 0.50 mm pitch, so it needs its own land pattern. AT LAYOUT: all six lines now converge on one part -- put it between the bridge and the FPGA where the four JTAG lines already run together, and keep TCK, element F on pads 6/11, at the end of the body: its only live neighbour is TMS.',
         **{'MANF#': '742C163101JP'}),
    dict(designator='R1', elements=2, used=['R1', 'R3'],
         libref='RES2742', description='Resistor 2-pack   Package of two resistors.',
         footprint='742C043', comment='4.7K',
         DeviceName='742', LibraryName='ctambe', DeviceSetName='RES2',
         MANF='CTS', SPEC='2 x 4.7K +-5% isolated array, 0606 concave 1.60 x 1.60 mm, 0.80 mm '
                          'pitch, 63 mW per element',
         NOTE='The two configuration pull-ups in one package: A on INIT_B (net FPGA-INIT#), B on PROGRAM_B (net RST#). Both commons are pads 3 and 4, side by side on one long side of the body, and both go to VCC3V3. CTS publishes ONE recommended land pattern for the whole 742 package family, so this footprint is the 742C083 pad cell already validated for R34 with two pads per side instead of four. 5 percent: the 742C043 has no 1 percent option either, and a configuration pull-up does not care; 63 mW per element against the 2.3 mW that 3.3 V across 4.7 k actually dissipates. Alternate on the identical land: Panasonic EXB-V4V472JV, same 1.60 x 1.60 mm concave body on 0.80 mm pitch. Do NOT substitute EXB-34V472JV -- same size, convex terminals, different land. R99, the third 4.7 k pull-up on this sheet, stays discrete: it sits on PROG#, the far side of the 100 ohm now in R4.',
         **{'MANF#': '742C043472JP'}),
]

CATALOGUE = ('DeviceName', 'LibraryName', 'DeviceSetName', 'MANF', 'MANF#', 'SPEC', 'NOTE')


def uid():
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(8))


def new_uid(b):
    return re.sub(rb'\|UniqueID=[A-Z]{8}', lambda m: b'|UniqueID=' + uid().encode(), b)


def num(b, k):
    v = field(b, k)
    return int(v) if v is not None else None


def owner_list_index(b):
    o = field(b, 'OwnerIndex')
    return int(o) + 1 if o is not None else None


def subtree(recs, root):
    members, changed = {root}, True
    while changed:
        changed = False
        for i, (h, b) in enumerate(recs):
            if owner_list_index(b) in members and i not in members:
                members.add(i); changed = True
    return sorted(members)


def kids(recs, tree, parent):
    return [i for i in tree if owner_list_index(recs[i][1]) == parent]


def build(recs, comp_i, pack, part):
    """The record list for one placed element: [(body, parent_position_or_None), ...], where the
    parent position is an index into this same list."""
    n = pack['elements']
    tree = subtree(recs, comp_i)
    comp = recs[comp_i][1]
    lines = [recs[i][1] for i in kids(recs, tree, comp_i) if recs[i][1].startswith(b'|RECORD=6|')]
    pins = [recs[i][1] for i in kids(recs, tree, comp_i) if recs[i][1].startswith(b'|RECORD=2|')]
    assert len(lines) == 4 and len(pins) == 2, (len(lines), len(pins))
    hot = {field(b, 'Designator'): b for b in pins}
    params = {field(recs[i][1], 'Name'): recs[i][1] for i in kids(recs, tree, comp_i)
              if recs[i][1].startswith(b'|RECORD=41|')}
    desig = [recs[i][1] for i in kids(recs, tree, comp_i) if recs[i][1].startswith(b'|RECORD=34|')][0]
    m44 = [i for i in kids(recs, tree, comp_i) if recs[i][1].startswith(b'|RECORD=44|')][0]
    puid_tpl = next(recs[j][1] for i in tree if recs[i][1].startswith(b'|RECORD=2|')
                    for j in kids(recs, tree, i) if field(recs[j][1], 'Name') == 'PinUniqueId')

    body = set_field(set_field(set_field(set_field(set_field(set_field(new_uid(comp),
        'LibReference', pack['libref']), 'DesignItemId', pack['libref']),
        'ComponentDescription', pack['description']), 'PartCount', str(n + 1)),
        'CurrentPartId', str(part)), 'AllPinCount', str(2 * n))
    body = set_field(set_field(body, 'SourceLibraryName', 'ctambe.IntLib'), 'PartIDLocked', 'T')
    items = [[body, None]]

    def add(b, parent=0):
        items.append([b, parent])
        return len(items) - 1

    for j in range(1, n + 1):
        for ln in lines:
            add(set_field(new_uid(ln), 'OwnerPartId', str(j)))
        for name, pad in (('1', j), ('2', 2 * n + 1 - j)):
            p = set_field(set_field(new_uid(hot[name]), 'Designator', str(pad)), 'OwnerPartId', str(j))
            at = add(p)
            add(set_field(new_uid(puid_tpl), 'Text', uid()), at)      # fresh, distinct pin identity
        for key, text in (('GateName', chr(64 + j)), ('SymbolName', field(params['SymbolName_1'], 'Text'))):
            t = set_field(set_field(set_field(new_uid(params[f'{key}_1']),
                                             'Name', f'{key}_{j}'), 'Text', text), 'OwnerPartId', str(j))
            add(t)
    for k in CATALOGUE:
        src = params.get(k) or params['SPEC']
        add(set_field(set_field(set_field(new_uid(src), 'Name', k), 'Text', pack[k]), 'OwnerPartId', '1'))
    add(set_field(new_uid(desig), 'Text', pack['designator']))
    add(set_field(new_uid(params['Comment']), 'Text', pack['comment']))
    root44 = add(recs[m44][1])
    for i in subtree(recs, m44):
        if i == m44:
            continue
        b = new_uid(recs[i][1])
        if b.startswith(b'|RECORD=45|'):
            b = set_field(b, 'ModelName', pack['footprint'])
            if field(b, 'ModelDatafileEntity0') is not None:
                b = set_field(b, 'ModelDatafileEntity0', pack['footprint'])
            m45 = add(b, root44)
        else:
            add(b, m45)
    return items


def main(path):
    recs = split(read_stream(path, 'FileHeader'))
    N = len(recs)
    assert int(field(recs[0][1], 'Weight')) == N - 1, 'header count is already wrong'
    desig = {owner_list_index(b): field(b, 'Text') for h, b in recs if b.startswith(b'|RECORD=34|')}
    where = {}
    for i, d in desig.items():
        where.setdefault(d, []).append(i)
    for pack in PACKS:
        for d in pack['used']:
            if len(where.get(d, [])) != 1:
                raise SystemExit(f'{d} is not a single discrete component; has this already run?')

    kill, made = set(), []
    for pack in PACKS:
        assert len(pack['used']) <= pack['elements']
        for part, d in enumerate(pack['used'], 1):
            comp_i = where[d][0]
            made.append(build(recs, comp_i, pack, part))
            kill |= set(subtree(recs, comp_i))

    keep = [i for i in range(N) if i not in kill]
    newpos = {old: new for new, old in enumerate(keep)}
    out = []
    for old in keep:
        h, b = recs[old]
        oi = owner_list_index(b)
        if oi is not None:
            assert oi in newpos, f'record {old} is owned by a deleted record'
            b = set_field(b, 'OwnerIndex', str(newpos[oi] - 1))
        out.append([h, b])
    for items in made:
        base = len(out)
        for k, (b, parent) in enumerate(items):
            if parent is not None:
                b = set_field(b, 'OwnerIndex', str(base + parent - 1))
            out.append([bytes(4), b if b.endswith(b'\x00') else b + bytes(1)])
    out[0][1] = set_field(out[0][1], 'Weight', str(len(out) - 1))
    blob = join(out)
    write_stream(path, 'FileHeader', blob)
    assert read_stream(path, 'FileHeader') == blob
    print(f'sheet 4: {N} -> {len(out)} records ({len(kill)} deleted, {sum(len(m) for m in made)} added); '
          + '; '.join(f'{p["designator"]} = {p["elements"]}-pack of ' + ', '.join(p['used']) for p in PACKS))
    verify(path)


def verify(path):
    recs = split(read_stream(path, 'FileHeader'))
    assert int(field(recs[0][1], 'Weight')) == len(recs) - 1, 'header count'
    assert all(b.endswith(b'\x00') for h, b in recs), 'a record lost its terminator'
    uids = [field(b, 'UniqueID') for h, b in recs if field(b, 'UniqueID')]
    dup = sorted({u for u in uids if uids.count(u) > 1})
    assert not dup, f'duplicate UniqueIDs: {dup}'
    puid = [field(b, 'Text') for h, b in recs if field(b, 'Name') == 'PinUniqueId']
    assert len(puid) == len(set(puid)), 'duplicate PinUniqueId'
    for i, (h, b) in enumerate(recs):
        oi = owner_list_index(b)
        if oi is not None:
            assert 0 <= oi < len(recs) and recs[oi][1].startswith(
                (b'|RECORD=1|', b'|RECORD=2|', b'|RECORD=44|', b'|RECORD=45|')), (i, oi)
    desig = {owner_list_index(b): field(b, 'Text') for h, b in recs if b.startswith(b'|RECORD=34|')}
    for pack in PACKS:
        n, d = pack['elements'], pack['designator']
        comps = sorted(i for i, x in desig.items() if x == d)
        assert len(comps) == len(pack['used']), f'{d} has {len(comps)} placements'
        parts, pads = set(), set()
        for c in comps:
            b = recs[c][1]
            assert field(b, 'LibReference') == pack['libref'], d
            assert field(b, 'PartCount') == str(n + 1), d
            cp = int(field(b, 'CurrentPartId'))
            assert cp not in parts, f'{d} places gate {cp} twice'
            parts.add(cp)
            mine = [x for h2, x in recs if x.startswith(b'|RECORD=2|') and owner_list_index(x) == c]
            assert len(mine) == 2 * n, f'{d} gate {cp} has {len(mine)} pins'
            live = sorted(int(field(x, 'Designator')) for x in mine if field(x, 'OwnerPartId') == str(cp))
            assert live == sorted((cp, 2 * n + 1 - cp)), (d, cp, live)
            pads |= set(live)
            fp = [field(x, 'ModelName') for h2, x in recs if x.startswith(b'|RECORD=45|')
                  and owner_list_index(x) in {j for j, (h3, y) in enumerate(recs)
                                              if y.startswith(b'|RECORD=44|') and owner_list_index(y) == c}]
            assert fp == [pack['footprint']], (d, fp)
            got = {field(x, 'Name'): field(x, 'Text') for h2, x in recs
                   if x.startswith(b'|RECORD=41|') and owner_list_index(x) == c}
            for k in CATALOGUE:
                assert got.get(k) == pack[k], (d, k, got.get(k))
            assert got.get('Comment') == pack['comment'], d
        assert parts == set(range(1, len(pack['used']) + 1)), (d, sorted(parts))
        assert pads == set(range(1, len(pack['used']) + 1)) | {2 * n + 1 - k for k in parts}, (d, sorted(pads))
        for old in pack['used']:
            if old != d:
                assert old not in desig.values(), f'{old} is still on the sheet'
    print(f'verify: {len(recs)} records, ids unique, '
          + '; '.join(f'{p["designator"]} placed as {len(p["used"])} of {p["elements"]} elements '
                      f'on {p["footprint"]}' for p in PACKS))


if __name__ == '__main__':
    main(sys.argv[2])
