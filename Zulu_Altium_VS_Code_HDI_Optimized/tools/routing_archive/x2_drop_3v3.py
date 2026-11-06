# -*- coding: utf-8 -*-
"""X2 pin field, 2026-09-09 (third pass): +3.3V2 dropped from the right-hand end.

Follows x2_jst_gap.py. The bottom row's second supply pin, +3.3V2 on pad 24, is deleted; the
position stays in the 44-hole pattern as an empty one, like 28-30 (the LiPo landing) and the four
USB positions in the top row. Nothing slides: the remaining pins keep their pads, so the bottom
row reads 21 GND, 22 VU, 23 RST#, 24 empty, 25-27 CHAN14-16, 28-30 empty, 31-42 CHAN17-28,
43-44 ANALOG-IO0/1. The header still carries 3.3 V on pad 17 in the top row.

Sheet 2 only: the +3.3V2 gate copy with its wire and VCC3V3 label is deleted, its sub-part is
removed from every remaining copy (pins with their HiddenNetName/PinUniqueId children, polygons,
GateName/SymbolName) and the parts above it are renumbered down by one (PartCount 43 -> 42,
AllPinCount 41 -> 40); the catalogue parameters (DeviceName, LibraryName, DeviceSetName, MANF,
MANF#, SPEC, NOTE) are exempt from that deletion because the importer gave them per-copy serial
OwnerPartIds; MANF#, SPEC and NOTE on X2 and the text frame above the box are rewritten for the
row that the bottom-row strips now have to skip twice. Pin designators do not change, so the only
netlist effect is that X2-24 leaves VCC3V3. Refuses to run twice.

    python tools/x2_drop_3v3.py tools "Imported zulu_a7.PrjPcb"
"""
import sys, os, re
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

GATE = '+3.3V2'
DEAD_ROW = 1119                                                        # pad 24: y = 1149 - 10 * (pad - 21)
DEAD_LABEL = 'VCC3V3'
MANF = 'PRPC014SAAN-RC + PRPC011SAAN-RC + PRPC009SAAN-RC + 2x PRPC003SAAN-RC'
SPEC = ('five 0.1 in male breakaway header strips, 0.64 mm square gold-flash pins, 2.54 mm pitch, through-hole, mounted from the '
        'underside: PRPC003SAAN-RC 1x3 twice (pads 21-23 and 25-27) and PRPC014SAAN-RC 1x14 (pads 31-44) on the bottom row, '
        'PRPC009SAAN-RC 1x9 (pads 1-9) and PRPC011SAAN-RC 1x11 (pads 10-20) on the top row; strips added 2026-09-08, bottom row '
        're-cut 2026-09-09 around the LiPo gap and the dropped +3.3V2')
NOTE = ('Pin field ZULU-DIP37: 40 holes of 1.016 mm on 2.54 mm pitch in a 44-position pattern, two rows 22.86 mm (0.900 in) apart; '
        'top row 1-9 and 10-20 with a four-position gap for X1 (micro-USB), bottom row 21-23, 25-27 and 31-44 with a three-position '
        'gap (28-30, x 41.91 / 39.37 / 36.83) for the LiPo header X4 on the top side, opposite the USB, and position 24 empty. '
        'Reworked 2026-09-09: +5V-INPUT with D2/D3, GND5, GND3 and +3.3V2 removed, CHAN17..ANALOG-IO1 moved down to 31-44, '
        'CHAN12/CHAN13 on pads 2/3; pads are numbered straight through by position, so the corner reads GND, VU, RST#, (empty). '
        '3.3 V for the header is pad 17 in the top row; three grounds, 1, 20 and 21. Sullins PRPC strips fit the holes (0.64 mm '
        'square pins, Sullins recommends 1.02 mm). Digi-Key 2026-09-09: PRPC003SAAN-RC 48,145 at $0.10, PRPC014SAAN-RC 663 at '
        '$0.28; 2026-09-08: PRPC009SAAN-RC 1,201 at $0.18, PRPC011SAAN-RC 428 at $0.22. Alternate: any 2.54 mm 1x40 breakaway '
        'strip (LCSC Boomele C2337, 81,690) cut to 14 + 11 + 9 + 3 + 3.')
FRAME = ('X2: 40 pins on a 2.54 mm grid in a 44-position pattern, rows 22.86 mm (0.900 in) apart. ~1'
         'Numbered right to left and straight through by position: top row 1-20, bottom row 21-44. ~1'
         'TOP ROW, x 59.69 down to 1.27: GND, CHAN12, CHAN13, then CHAN-CLK and CHAN0..CHAN3 ~1'
         '  (pins 4-8), CHAN4 (pin 9), CHAN5..CHAN11 (10-16), +3.3V, +1.8V, +1.0V, GND. ~1'
         '  FOUR positions between pin 9 and pin 10 -- x 36.83, 34.29, 31.75, 29.21 -- are ~1'
         '  RESERVED, not spare: the landing for the edge-mounted micro-USB X1, 7.80 mm of ~1'
         '  copper in 11.176 mm clear, centred with 1.69 mm each side. ~1'
         'BOTTOM ROW, x 59.69 down to 1.27: GND, VU, RST# (pins 21-23), position 24 EMPTY since ~1'
         '  2026-09-09 (+3.3V2 dropped; the header takes 3.3 V from pin 17), CHAN14..CHAN16 (25-27), ~1'
         '  THREE positions 28-30 -- x 41.91, 39.37, 36.83 -- RESERVED for the top-side LiPo header X4 ~1'
         '  (JST B2B-PH-SM4-TB, opposite the USB; 10.16 mm between the neighbouring pin centres), ~1'
         '  then CHAN17..CHAN28 (pins 31-42), ANALOG-IO0, ANALOG-IO1 (43, 44). ~1'
         'THREE grounds: pins 1, 20, 21.  Pin 22 VU SOURCES the 4.4 V rail (bq24232 OUT); the +5V-INPUT pin ~1'
         '  and its D2/D3 were removed 2026-09-09 -- external power is the LiPo on X4.')


def num(b, k):
    v = field(b, k); return int(v) if v is not None else None


def owner_list_index(b):
    o = field(b, 'OwnerIndex')
    return int(o) + 1 if o is not None else None


def wire_pts(b):
    if not b.startswith(b'|RECORD=27|'):
        return None
    n = num(b, 'LocationCount') or 0
    return tuple((num(b, f'X{k}'), num(b, f'Y{k}')) for k in range(1, n + 1))


def sub_part(b, old, new):
    b = re.sub(rb'\|OwnerPartId=' + str(old).encode() + rb'(?=\|)', b'|OwnerPartId=' + str(new).encode(), b)
    b = re.sub(rb'\|Name=(GateName|SymbolName)_' + str(old).encode() + rb'(?=\|)', lambda m: b'|Name=' + m.group(1) + b'_' + str(new).encode(), b)
    return b


def main(path):
    recs = split(read_stream(path, 'FileHeader'))
    N = len(recs)
    copies = [i for i, (h, b) in enumerate(recs) if b.startswith(b'|RECORD=1|') and field(b, 'LibReference') == 'ZULU-CONN']
    assert len(copies) == 42, len(copies)
    if int(field(recs[copies[0]][1], 'PartCount')) != 43:
        raise SystemExit('X2 already has 41 sub-parts; nothing done')
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
    part_of = {ci: int(field(recs[ci][1], 'CurrentPartId')) for ci in copies}
    gate_of = {}
    for i, (h, b) in enumerate(recs):
        if b.startswith(b'|RECORD=41|') and field(b, 'Name') == 'GATE' and root.get(i) in copies:
            gate_of[root[i]] = field(b, 'Text')
    dead = [ci for ci in copies if gate_of.get(ci) == GATE]
    assert len(dead) == 1 and num(recs[dead[0]][1], 'Location.Y') == DEAD_ROW, dead
    dead_part = part_of[dead[0]]
    kill = {i for i in range(N) if root.get(i) == dead[0]}
    found = set()
    for i, (h, b) in enumerate(recs):
        if owner_list_index(b) is not None:
            continue
        if wire_pts(b) == ((325, DEAD_ROW), (355, DEAD_ROW)):
            kill.add(i); found.add('wire')
        elif b.startswith(b'|RECORD=25|') and (num(b, 'Location.X'), num(b, 'Location.Y')) == (355, DEAD_ROW) and field(b, 'Text') == DEAD_LABEL:
            kill.add(i); found.add('label')
    assert found == {'wire', 'label'}, found
    live = [ci for ci in copies if ci != dead[0]]
    edited = 0
    for i in range(N):
        if i in kill or root.get(i) not in live:
            continue
        h, b = recs[i]
        if i in live:
            pid = part_of[i]
            b = set_field(set_field(set_field(b, 'CurrentPartId', str(pid - 1 if pid > dead_part else pid)), 'PartCount', '42'), 'AllPinCount', '40')
            recs[i][1] = b; edited += 1
            continue
        pid = num(b, 'OwnerPartId')
        name = field(b, 'Name') or ''
        catalogue = b.startswith(b'|RECORD=41|') and not re.match(r'(GateName|SymbolName)_\d+$', name)
        if pid == dead_part and not catalogue:
            kill.add(i); continue
        if b.startswith(b'|RECORD=41|'):
            if name == 'MANF#': b = set_field(b, 'Text', MANF)
            elif name == 'SPEC': b = set_field(b, 'Text', SPEC)
            elif name == 'NOTE': b = set_field(b, 'Text', NOTE)
        if pid is not None and pid > dead_part:
            b = sub_part(b, pid, pid - 1)
        recs[i][1] = b; edited += 1
    for i in range(N):                                                 # children of deleted pins
        if i not in kill and owner_list_index(recs[i][1]) in kill:
            kill.add(i)
    frames = [i for i, (h, b) in enumerate(recs) if b.startswith(b'|RECORD=28|') and (field(b, 'Text') or '').startswith('X2: 41 pins')]
    assert len(frames) == 1, frames
    recs[frames[0]][1] = set_field(recs[frames[0]][1], 'Text', FRAME)
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
    out[0][1] = set_field(out[0][1], 'Weight', str(len(out) - 1))
    blob = join(out)
    write_stream(path, 'FileHeader', blob)
    assert read_stream(path, 'FileHeader') == blob
    print(f'sheet 2: {N} -> {len(out)} records ({len(kill)} deleted, {edited} edited)')
    verify(path)


CATALOGUE = ('DeviceName', 'LibraryName', 'DeviceSetName', 'MANF', 'MANF#', 'SPEC', 'NOTE')


def verify(path):
    recs = split(read_stream(path, 'FileHeader'))
    assert int(field(recs[0][1], 'Weight')) == len(recs) - 1
    copies = [i for i, (h, b) in enumerate(recs) if b.startswith(b'|RECORD=1|') and field(b, 'LibReference') == 'ZULU-CONN']
    assert len(copies) == 41, len(copies)
    assert sorted(int(field(recs[ci][1], 'CurrentPartId')) for ci in copies) == list(range(1, 42))
    kids = {}
    for i, (h, b) in enumerate(recs):
        oi = owner_list_index(b)
        if oi in copies: kids.setdefault(oi, []).append(b)
    expect = [n for n in range(1, 45) if n not in (24, 28, 29, 30)]
    table, rows = [], {}
    for ci in copies:
        pins = [b for b in kids[ci] if b.startswith(b'|RECORD=2|')]
        assert sorted(int(field(b, 'Designator')) for b in pins) == expect
        owners = {num(b, 'OwnerPartId') for b in kids[ci]} - {None}
        assert sorted(owners) == [-1] + list(range(1, 42)), owners
        names = [field(b, 'Name') for b in kids[ci] if b.startswith(b'|RECORD=41|')]
        assert {f'GateName_{n}' for n in range(1, 42)} <= set(names) and 'GateName_42' not in names
        assert all(names.count(c) == 1 for c in CATALOGUE), [c for c in CATALOGUE if names.count(c) != 1]
        assert field(recs[ci][1], 'PartCount') == '42' and field(recs[ci][1], 'AllPinCount') == '40'
        pid = field(recs[ci][1], 'CurrentPartId')
        vis = [b for b in pins if field(b, 'OwnerPartId') == pid]
        gate = [field(b, 'Text') for b in kids[ci] if b.startswith(b'|RECORD=41|') and field(b, 'Name') == 'GATE']
        if vis:
            pad = int(field(vis[0], 'Designator'))
            table.append((pad, gate[0]))
            if num(recs[ci][1], 'Location.X') == 325:
                rows[pad] = num(recs[ci][1], 'Location.Y')
    for pad, name in sorted(table):
        print(f'   pad {pad:>2} {name}')
    for pad, y in rows.items():
        assert y == 1149 - 10 * (pad - 21), (pad, y)
    labels = {(num(b, 'Location.X'), num(b, 'Location.Y')) for h, b in recs if b.startswith(b'|RECORD=25|') and owner_list_index(b) is None}
    wires = {wire_pts(b) for h, b in recs if b.startswith(b'|RECORD=27|') and owner_list_index(b) is None}
    for pad, y in rows.items():
        assert ((325, y), (355, y)) in wires and (355, y) in labels, pad
    for empty in (24, 28, 29, 30):
        y = 1149 - 10 * (empty - 21)
        assert (355, y) not in labels and ((325, y), (355, y)) not in wires, empty
    t = dict(table)
    assert t[23] == 'RST#' and t[25] == 'CHAN14' and t[27] == 'CHAN16' and t[31] == 'CHAN17' and t[17] == '+3.3V'
    assert not (set(t) & {24, 28, 29, 30})
    print('verify: 41 copies, 40 pins each, parts 1-41 contiguous, catalogue parameters intact, 24 and 28-30 empty')


if __name__ == '__main__':
    main(os.path.join(sys.argv[2], 'zulu_a7_2.SchDoc'))
