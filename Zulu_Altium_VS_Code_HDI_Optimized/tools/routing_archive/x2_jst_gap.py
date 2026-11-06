# -*- coding: utf-8 -*-
"""X2 pin field, 2026-09-09 (second pass): a three-position gap in the bottom row for the LiPo header.

Follows x2_lipo_corner.py. On the symbol's right column (the bottom row of the board) GND3 goes,
the five pins below the corner close up, and the rest move down one place, which leaves three
empty positions in the middle of the row for the JST header X4, the way the top row leaves four
for the micro-USB. Pads keep the file's convention of being numbered straight through by
position, so the signals take new pad numbers:

  before (pad: signal)   21 GND4, 22 VU, 23 -, 24 RST#, 25 +3.3V2, 26 GND3, 27 CHAN14, 28 CHAN15,
                         29 CHAN16, 30 CHAN17 ... 43 ANALOG-IO1, 44 -
  after                  21 GND4, 22 VU, 23 RST#, 24 +3.3V2, 25 CHAN14, 26 CHAN15, 27 CHAN16,
                         28-30 empty (JST), 31 CHAN17 ... 42 CHAN28, 43 ANALOG-IO0, 44 ANALOG-IO1

Mechanics on sheet 2: the GND3 gate copy, its wire and GND label are deleted and its sub-part is
removed from every gate copy (pins with their parameter children, polygons, GateName/SymbolName)
with the parts above it renumbered down by one (PartCount 44 -> 43, AllPinCount 42 -> 41) -- the
catalogue parameters (DeviceName, LibraryName, DeviceSetName, MANF, MANF#, SPEC, NOTE) are exempt
from that deletion because the importer gave them per-copy serial OwnerPartIds, the trap that
x2_lipo_corner.py fell into (repaired by x2_restore_params.py); every
pin record in every copy gets its designator remapped (24->23, 25->24, 27->25, 28->26, 29->27,
30..43 -> 31..44); the right-column gate copies with their wires and net labels shift up 10 or 20
or down 10 to sit on the row of their new pad; MANF#, SPEC and NOTE on X2 and the text frame
above the box are rewritten; on sheet 1 the U8 NOTE parameter drops its D2 sentence. The nets themselves
do not change. Refuses to run twice.

    python tools/x2_jst_gap.py tools "Imported zulu_a7.PrjPcb"
"""
import sys, os, re
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

REMAP = {24: 23, 25: 24, 27: 25, 28: 26, 29: 27}
REMAP.update({n: n + 1 for n in range(30, 44)})
ROW_DY = {1119: 10, 1109: 10, 1089: 20, 1079: 20, 1069: 20}            # RST#, +3.3V2, CHAN14, CHAN15, CHAN16
ROW_DY.update({y: -10 for y in range(1059, 920, -10)})                 # CHAN17 .. ANALOG-IO1 (1059 .. 929)
DEAD_ROW = 1099                                                        # GND3
COORD_KEYS = re.compile(rb'\|(Location\.X|Location\.Y|X\d+|Y\d+)=(-?\d+)')
MANF = 'PRPC014SAAN-RC + PRPC007SAAN-RC + PRPC009SAAN-RC + PRPC011SAAN-RC'
SPEC = ('four 0.1 in male breakaway header strips, 0.64 mm square gold-flash pins, 2.54 mm pitch, through-hole, mounted from the '
        'underside: PRPC007SAAN-RC 1x7 (pads 21-27) and PRPC014SAAN-RC 1x14 (pads 31-44) on the bottom row, PRPC009SAAN-RC 1x9 '
        '(pads 1-9) and PRPC011SAAN-RC 1x11 (pads 10-20) on the top row; one of each per board; strips added 2026-09-08, bottom row '
        're-cut 2026-09-09 around the three-position gap for the LiPo header')
NOTE = ('Pin field ZULU-DIP37: 41 holes of 1.016 mm on 2.54 mm pitch in a 44-position pattern, two rows 22.86 mm (0.900 in) apart; '
        'top row 1-9 and 10-20 with a four-position gap for X1 (micro-USB), bottom row 21-27 and 31-44 with a three-position gap '
        '(28-30, x 41.91 / 39.37 / 36.83) for the LiPo header X4 on the top side, opposite the USB. Reworked 2026-09-09: +5V-INPUT '
        'with D2/D3, GND5 and GND3 removed, RST#, +3.3V and CHAN14-16 closed up to pads 23-27, CHAN17..ANALOG-IO1 moved down to '
        '31-44, CHAN12/CHAN13 on pads 2/3; pads are numbered straight through by position, so the corner reads GND, VU, RST#, +3.3V. '
        'Three grounds: 1, 20, 21. Sullins PRPC strips fit the holes (0.64 mm square pins, Sullins recommends 1.02 mm). Digi-Key '
        '2026-09-09: PRPC007SAAN-RC 6,643 at $0.15, PRPC014SAAN-RC 663 at $0.28; 2026-09-08: PRPC009SAAN-RC 1,201 at $0.18, '
        'PRPC011SAAN-RC 428 at $0.22. Alternate: any 2.54 mm 1x40 breakaway strip (LCSC Boomele C2337, 81,690) cut to 14 + 11 + 9 + 7.')
FRAME = ('X2: 41 pins on a 2.54 mm grid in a 44-position pattern, rows 22.86 mm (0.900 in) apart. ~1'
         'Numbered right to left and straight through by position: top row 1-20, bottom row 21-44. ~1'
         'TOP ROW, x 59.69 down to 1.27: GND, CHAN12, CHAN13, then CHAN-CLK and CHAN0..CHAN3 ~1'
         '  (pins 4-8), CHAN4 (pin 9), CHAN5..CHAN11 (10-16), +3.3V, +1.8V, +1.0V, GND. ~1'
         '  FOUR positions between pin 9 and pin 10 -- x 36.83, 34.29, 31.75, 29.21 -- are ~1'
         '  RESERVED, not spare: the landing for the edge-mounted micro-USB X1, 7.80 mm of ~1'
         '  copper in 11.176 mm clear, centred with 1.69 mm each side. ~1'
         'BOTTOM ROW, x 59.69 down to 1.27: GND, VU, RST#, +3.3V, CHAN14, CHAN15, CHAN16 (pins 21-27), ~1'
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


def shift(b, dy):
    def rep(m):
        k, v = m.group(1), int(m.group(2))
        if k == b'Location.Y' or k.startswith(b'Y'):
            v += dy
        return b'|' + k + b'=' + str(v).encode()
    return COORD_KEYS.sub(rep, b)


def sub_part(b, old, new):
    b = re.sub(rb'\|OwnerPartId=' + str(old).encode() + rb'(?=\|)', b'|OwnerPartId=' + str(new).encode(), b)
    b = re.sub(rb'\|Name=(GateName|SymbolName)_' + str(old).encode() + rb'(?=\|)', lambda m: b'|Name=' + m.group(1) + b'_' + str(new).encode(), b)
    return b


def main(path):
    recs = split(read_stream(path, 'FileHeader'))
    N = len(recs)
    copies = [i for i, (h, b) in enumerate(recs) if b.startswith(b'|RECORD=1|') and field(b, 'LibReference') == 'ZULU-CONN']
    assert len(copies) == 43, len(copies)
    if int(field(recs[copies[0]][1], 'PartCount')) != 44:
        raise SystemExit('X2 already has 42 sub-parts; nothing done')
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
    dead = [ci for ci in copies if gate_of.get(ci) == 'GND3']
    assert len(dead) == 1 and num(recs[dead[0]][1], 'Location.Y') == DEAD_ROW, dead
    dead_part = part_of[dead[0]]
    kill = {i for i in range(N) if root.get(i) == dead[0]}
    found = set()
    for i, (h, b) in enumerate(recs):
        if owner_list_index(b) is not None:
            continue
        p = wire_pts(b)
        if p == ((325, DEAD_ROW), (355, DEAD_ROW)):
            kill.add(i); found.add('wire')
        elif b.startswith(b'|RECORD=25|') and (num(b, 'Location.X'), num(b, 'Location.Y')) == (355, DEAD_ROW) and field(b, 'Text') == 'GND':
            kill.add(i); found.add('label')
    assert found == {'wire', 'label'}, found
    live = [ci for ci in copies if ci != dead[0]]
    # per-copy: drop the dead sub-part, renumber parts above it, remap pin designators, rewrite the X2 parameters
    edited = 0
    for i in range(N):
        if i in kill or root.get(i) not in live:
            continue
        h, b = recs[i]
        if i in live:
            pid = part_of[i]
            b = set_field(set_field(set_field(b, 'CurrentPartId', str(pid - 1 if pid > dead_part else pid)), 'PartCount', '43'), 'AllPinCount', '41')
            recs[i][1] = b; edited += 1
            continue
        pid = num(b, 'OwnerPartId')
        name = field(b, 'Name') or ''
        catalogue = b.startswith(b'|RECORD=41|') and not re.match(r'(GateName|SymbolName)_\d+$', name)
        if pid == dead_part and not catalogue:                          # the catalogue parameters carry unrelated serial OwnerPartIds
            kill.add(i); continue
        if b.startswith(b'|RECORD=2|'):
            d = int(field(b, 'Designator'))
            assert d != 26, 'pin 26 must belong to the dead sub-part'
            if d in REMAP:
                b = set_field(b, 'Designator', str(REMAP[d]))
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
    # row shifts: right-column gate copies (x = 325) with their subtrees, wires and labels
    moved = 0
    row_of_copy = {ci: num(recs[ci][1], 'Location.Y') for ci in live if num(recs[ci][1], 'Location.X') == 325}
    for i in range(N):
        if i in kill:
            continue
        h, b = recs[i]
        r = root.get(i)
        if r in row_of_copy and row_of_copy[r] in ROW_DY:
            recs[i][1] = shift(b, ROW_DY[row_of_copy[r]]); moved += 1
        elif owner_list_index(b) is None:
            p = wire_pts(b)
            if p and len(p) == 2 and p[0][0] == 325 and p[1][0] == 355 and p[0][1] == p[1][1] and p[0][1] in ROW_DY:
                recs[i][1] = shift(b, ROW_DY[p[0][1]]); moved += 1
            elif b.startswith(b'|RECORD=25|') and num(b, 'Location.X') == 355 and num(b, 'Location.Y') in ROW_DY:
                recs[i][1] = shift(b, ROW_DY[num(b, 'Location.Y')]); moved += 1
    assert moved > 0
    # text frame
    frames = [i for i, (h, b) in enumerate(recs) if b.startswith(b'|RECORD=28|') and (field(b, 'Text') or '').startswith('X2: 42 pins')]
    assert len(frames) == 1, frames
    recs[frames[0]][1] = set_field(recs[frames[0]][1], 'Text', FRAME)
    # rebuild
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
    print(f'sheet 2: {N} -> {len(out)} records ({len(kill)} deleted, {edited} edited, {moved} shifted)')
    verify(path)


def verify(path):
    recs = split(read_stream(path, 'FileHeader'))
    copies = [i for i, (h, b) in enumerate(recs) if b.startswith(b'|RECORD=1|') and field(b, 'LibReference') == 'ZULU-CONN']
    assert len(copies) == 42, len(copies)
    parts = sorted(int(field(recs[ci][1], 'CurrentPartId')) for ci in copies)
    assert parts == list(range(1, 43)), parts
    kids = {}
    for i, (h, b) in enumerate(recs):
        oi = owner_list_index(b)
        if oi in copies: kids.setdefault(oi, []).append(b)
    expect = [n for n in range(1, 45) if n not in (28, 29, 30)]
    table, rows = [], {}
    for ci in copies:
        pins = [b for b in kids[ci] if b.startswith(b'|RECORD=2|')]
        assert sorted(int(field(b, 'Designator')) for b in pins) == expect
        owners = {num(b, 'OwnerPartId') for b in kids[ci]} - {None}
        assert sorted(owners) == [-1] + list(range(1, 43)), owners
        names = {field(b, 'Name') for b in kids[ci] if b.startswith(b'|RECORD=41|')}
        assert {f'GateName_{n}' for n in range(1, 43)} <= names and 'GateName_43' not in names
        assert field(recs[ci][1], 'PartCount') == '43' and field(recs[ci][1], 'AllPinCount') == '41'
        pid = field(recs[ci][1], 'CurrentPartId')
        vis = [b for b in pins if field(b, 'OwnerPartId') == pid]
        gate = [field(b, 'Text') for b in kids[ci] if b.startswith(b'|RECORD=41|') and field(b, 'Name') == 'GATE']
        if vis:
            pad = int(field(vis[0], 'Designator'))
            table.append((pad, gate[0]))
            if num(recs[ci][1], 'Location.X') == 325:
                rows[pad] = (num(recs[ci][1], 'Location.Y'), num(vis[0], 'Location.Y'))
    for pad, name in sorted(table):
        print(f'   pad {pad:>2} {name}')
    for pad, (gy, py) in rows.items():
        assert gy == py == 1149 - 10 * (pad - 21), (pad, gy, py)
    # every right-column gate has its wire and label on its row, and nothing sits on the empty rows
    labels = {(num(b, 'Location.X'), num(b, 'Location.Y')): field(b, 'Text') for h, b in recs if b.startswith(b'|RECORD=25|') and owner_list_index(b) is None}
    wires = {wire_pts(b) for h, b in recs if b.startswith(b'|RECORD=27|') and owner_list_index(b) is None}
    for pad, (gy, py) in rows.items():
        assert ((325, gy), (355, gy)) in wires and (355, gy) in labels, pad
    for empty in (28, 29, 30):
        y = 1149 - 10 * (empty - 21)
        assert (355, y) not in labels and ((325, y), (355, y)) not in wires, empty
    t = dict(table)
    assert t[23] == 'RST#' and t[24] == '+3.3V2' and t[25] == 'CHAN14' and t[27] == 'CHAN16' and t[26] == 'CHAN15' and t[31] == 'CHAN17' and t[44] == 'ANALOG-IO1' and not (set(t) & {28, 29, 30})
    print('verify: 42 copies, 41 pins each, parts 1-42 contiguous, right column rows match the pad numbers, 28-30 empty')


U8_OLD = 'The +5V-INPUT path through D2 still drives VU directly and does not charge the battery.'
U8_NEW = 'The +5V-INPUT path with D2 and D3 was removed on 2026-09-09, so the charger is the only input.'


def sheet1(path):
    """U8's hidden NOTE parameter still described the D2 path (missed by x2_lipo_corner.py, found by the review)."""
    recs = split(read_stream(path, 'FileHeader'))
    hits = [i for i, (h, b) in enumerate(recs) if b.startswith(b'|RECORD=41|') and field(b, 'Name') == 'NOTE' and U8_OLD in (field(b, 'Text') or '')]
    assert len(hits) == 1, hits
    i = hits[0]
    recs[i][1] = set_field(recs[i][1], 'Text', field(recs[i][1], 'Text').replace(U8_OLD, U8_NEW))
    blob = join(recs)
    write_stream(path, 'FileHeader', blob)
    assert read_stream(path, 'FileHeader') == blob
    print('sheet 1: U8 NOTE parameter updated')


if __name__ == '__main__':
    main(os.path.join(sys.argv[2], 'zulu_a7_2.SchDoc'))
    sheet1(os.path.join(sys.argv[2], 'zulu_a7_1.SchDoc'))
