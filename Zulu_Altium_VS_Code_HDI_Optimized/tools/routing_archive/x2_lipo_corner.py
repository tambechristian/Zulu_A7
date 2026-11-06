# -*- coding: utf-8 -*-
"""X2 pin field, 2026-09-09: room for the LiPo connector at the right-hand end.

The JST battery header X4 goes on the top side at the right-hand end of the board, on the
bottom-row side (opposite the micro-USB). External 5 V now arrives only through the charger,
so the +5V-INPUT path is dropped, and the corner is reorganised into a power corner:

  sheet 2
  * +5V-INPUT (X2 pad 44), the ORing Schottky D2 and the TVS D3 are deleted with their wires,
    the VEXT label, the VU label at D2's cathode, the ground port and the junction;
  * GND5 (X2 pad 23) is deleted with its wire and GND label -- the hole stays empty;
  * +3.3V2 and GND3 swap places with CHAN12 and CHAN13: pads 2 and 3 (top row, right-hand
    end) now carry CHAN12 and CHAN13, pads 25 and 26 (bottom row, next to RST#) carry
    VCC3V3 and GND. Done as a net-label swap on the four rows plus the GATE labels inside the
    box and the GateName parameters, so the box keeps its pad order and only the names move;
  * the two dead sub-parts (35 +5V-INPUT, 45 GND5) are removed from every gate copy (pins,
    polygons, parameters) and parts 36-44 are renumbered 35-43, PartCount 46 -> 44,
    AllPinCount 44 -> 42, so the component has no unplaced sub-part;
  * MANF#, SPEC and NOTE on X2 describe the split bottom row (PRPC020 + PRPC002) and the
    text frame above the box is rewritten for the new pin-out;
  sheet 1
  * the charger note no longer says D2 ORs +5V-INPUT onto VU.

The displayed pins of pads 2/3 become passive and 25/26 power, as their new nets are.
Netlist effect, and nothing else: VEXT disappears; D2, D3, X2-23 and X2-44 disappear;
X2-2 -> CHAN12, X2-3 -> CHAN13, X2-25 -> VCC3V3, X2-26 -> GND. Refuses to run twice.

KNOWN DEFECT (found by the review of commit 338ea4e, repaired by x2_restore_params.py): the
sub-part deletion keys on OwnerPartId, but the importer gave the seven catalogue parameters of
each copy a per-copy serial OwnerPartId, so the two copies whose serial was 35 or 45 lost them.
x2_jst_gap.py exempts those parameters.

    python tools/x2_lipo_corner.py tools "Imported zulu_a7.PrjPcb"
"""
import sys, os, re
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

DEAD_PARTS = {35, 45}                                   # +5V-INPUT, GND5
SWAP_GATES = {41: 19, 42: 20}                           # +3.3V2 <-> CHAN12, GND3 <-> CHAN13 (old part ids)
LABEL_SWAPS = [((155, 1139), 'VCC3V3', 'CHAN12'), ((355, 1109), 'CHAN12', 'VCC3V3'),
               ((155, 1129), 'GND', 'CHAN13'), ((355, 1099), 'CHAN13', 'GND')]
DEAD_WIRES = {((325, 919), (390, 919)), ((390, 919), (410, 919)), ((390, 869), (390, 879)), ((450, 919), (480, 919)),
              ((325, 1129), (355, 1129))}
DEAD_OBJS = {(b'|RECORD=25|', (360, 919), 'VEXT'), (b'|RECORD=25|', (480, 919), 'VU'), (b'|RECORD=25|', (355, 1129), 'GND'),
             (b'|RECORD=17|', (390, 869), 'GND'), (b'|RECORD=29|', (390, 919), None)}
MANF = 'PRPC020SAAN-RC + PRPC002SAAN-RC + PRPC009SAAN-RC + PRPC011SAAN-RC'
SPEC = ('four 0.1 in male breakaway header strips, 0.64 mm square gold-flash pins, 2.54 mm pitch, through-hole, mounted from the '
        'underside: PRPC020SAAN-RC 1x20 on the bottom row (pads 24-43) and PRPC002SAAN-RC 1x2 (pads 21-22), PRPC009SAAN-RC 1x9 '
        '(pads 1-9) and PRPC011SAAN-RC 1x11 (pads 10-20) on the top row; one of each per board; strips added 2026-09-08, bottom row '
        'split 2026-09-09 when pads 23 and 44 were removed')
NOTE = ('Pin field ZULU-DIP37: 42 holes of 1.016 mm on 2.54 mm pitch in a 44-position pattern, two rows 22.86 mm (0.900 in) apart; '
        'top row 1-9 and 10-20 with a four-position gap for X1, bottom row 21-22 and 24-43. Positions 23 (GND5) and 44 (+5V-INPUT, '
        'with D2 and D3) were removed on 2026-09-09: external power is the LiPo on X4, which sits on the top side at this right-hand '
        'end, opposite the USB port; +3.3V2 and GND3 moved from pads 2/3 to 25/26 and CHAN12/CHAN13 took pads 2/3, so the corner '
        'reads GND, VU, (empty), RST#, +3.3V, GND. Sullins PRPC strips fit the holes (0.64 mm square pins, Sullins recommends 1.02 mm). '
        'Digi-Key 2026-09-09: PRPC020SAAN-RC 1,969 at $0.38, PRPC002SAAN-RC 49,279 at $0.10; 2026-09-08: PRPC009SAAN-RC 1,201 at '
        '$0.18, PRPC011SAAN-RC 428 at $0.22. Alternate: any 2.54 mm 1x40 breakaway strip (LCSC Boomele C2337, 81,690) cut to 20 + 11 + 9 + 2.')
FRAME = ('X2: 42 pins on a 2.54 mm grid in a 44-position pattern, rows 22.86 mm (0.900 in) apart. ~1'
         'Numbered right to left and straight through: top row 1-20, bottom row 21-44; positions 23 and 44 are empty since 2026-09-09. ~1'
         'TOP ROW, x 59.69 down to 1.27: GND, CHAN12, CHAN13, then CHAN-CLK and CHAN0..CHAN3 ~1'
         '  (pins 4-8), CHAN4 (pin 9), CHAN5..CHAN11 (10-16), +3.3V, +1.8V, +1.0V, GND. ~1'
         '  FOUR positions between pin 9 and pin 10 -- x 36.83, 34.29, 31.75, 29.21 -- are ~1'
         '  RESERVED, not spare: the landing for the edge-mounted micro-USB X1, 7.80 mm of ~1'
         '  copper in 11.176 mm clear, centred with 1.69 mm each side. ~1'
         'BOTTOM ROW, x 59.69 down to 3.81: GND, VU, (23 empty), RST#, +3.3V, GND (pins 25-26), ~1'
         '  CHAN14..CHAN28 (pins 27-41), ANALOG-IO0, ANALOG-IO1; position 44 (x 1.27) is empty. ~1'
         '  This right-hand end is the power corner: the LiPo connector X4 sits there on the top side, opposite the USB port. ~1'
         'FOUR grounds: pins 1, 20, 21, 26.  Pin 22 VU SOURCES the 4.4 V rail (bq24232 OUT); the +5V-INPUT pin 44 ~1'
         '  and its D2/D3 were removed 2026-09-09 -- external power is the LiPo on X4.')
SHEET1_OLD = 'D2 still ORs +5V-INPUT onto VU without charging.'
SHEET1_NEW = 'The +5V-INPUT pin with D2 and D3 was removed on 2026-09-09: the LiPo on X4 is the external supply.'


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


def sheet2(path):
    recs = split(read_stream(path, 'FileHeader'))
    N = len(recs)
    desig = {owner_list_index(b): field(b, 'Text') for h, b in recs if b.startswith(b'|RECORD=34|')}
    copies = [i for i, (h, b) in enumerate(recs) if b.startswith(b'|RECORD=1|') and field(b, 'LibReference') == 'ZULU-CONN']
    assert len(copies) == 45, len(copies)
    if int(field(recs[copies[0]][1], 'PartCount')) != 46:
        raise SystemExit('X2 already has fewer than 45 sub-parts; nothing done')
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
    dead_roots = {ci for ci, d in desig.items() if d in ('D2', 'D3')} | {ci for ci in copies if part_of[ci] in DEAD_PARTS}
    assert len(dead_roots) == 4, dead_roots
    kill = {i for i in range(N) if root.get(i) in dead_roots}
    found = set()
    for i, (h, b) in enumerate(recs):
        if owner_list_index(b) is not None:
            continue
        p = wire_pts(b)
        if p and len(p) == 2 and p in DEAD_WIRES:
            kill.add(i); found.add(p)
        for rec, (x, y), text in DEAD_OBJS:
            if b.startswith(rec) and (num(b, 'Location.X'), num(b, 'Location.Y')) == (x, y) and (text is None or field(b, 'Text') == text):
                kill.add(i); found.add((rec, (x, y)))
    assert len(found) == len(DEAD_WIRES) + len(DEAD_OBJS), found
    # sub-part clean-up inside every surviving copy
    live = [ci for ci in copies if ci not in dead_roots]
    gate_text = {}                                           # old part id -> gate name, read from the first copy
    for i in range(N):
        b = recs[i][1]
        if root.get(i) == live[0] and b.startswith(b'|RECORD=41|') and (field(b, 'Name') or '').startswith('GateName_'):
            gate_text[int(field(b, 'Name')[9:])] = field(b, 'Text')
    assert gate_text[41] == '+3.3V2' and gate_text[19] == 'CHAN12' and gate_text[42] == 'GND3' and gate_text[20] == 'CHAN13', gate_text
    swapped_text = {a: gate_text[b] for a, b in SWAP_GATES.items()}
    swapped_text.update({b: gate_text[a] for a, b in SWAP_GATES.items()})
    edited = 0
    for i in range(N):
        if i in kill or root.get(i) not in live:
            continue
        h, b = recs[i]
        if i in live:                                         # the RECORD=1 itself
            pid = part_of[i]
            if pid in SWAP_GATES or pid in SWAP_GATES.values():
                pass                                          # position and pin stay; the GATE label below is what changes
            newpid = pid - 1 if pid > 35 else pid
            b = set_field(set_field(set_field(b, 'CurrentPartId', str(newpid)), 'PartCount', '44'), 'AllPinCount', '42')
            recs[i][1] = b; edited += 1
            continue
        if owner_list_index(b) in live and b.startswith(b'|RECORD=41|'):
            name = field(b, 'Name') or ''
            pid = num(b, 'OwnerPartId')
            if name.startswith('GateName_') and int(name[9:]) in swapped_text:
                b = set_field(b, 'Text', swapped_text[int(name[9:])])
            elif name == 'GATE' and pid in swapped_text:
                b = set_field(b, 'Text', swapped_text[pid])
            elif name == 'MANF#': b = set_field(b, 'Text', MANF)
            elif name == 'SPEC': b = set_field(b, 'Text', SPEC)
            elif name == 'NOTE': b = set_field(b, 'Text', NOTE)
        pid = num(b, 'OwnerPartId')
        if pid in DEAD_PARTS:
            kill.add(i); continue
        if pid is not None and pid > 35:
            b = sub_part(b, pid, pid - 1)
        else:
            m = re.search(rb'\|Name=(?:GateName|SymbolName)_(\d+)\|', b)
            if m and int(m.group(1)) in DEAD_PARTS:
                kill.add(i); continue
            if m and int(m.group(1)) > 35:
                b = sub_part(b, int(m.group(1)), int(m.group(1)) - 1)
        recs[i][1] = b; edited += 1
    # a deleted pin takes its own parameter records (HiddenNetName, PinUniqueId) with it
    for i in range(N):
        if i not in kill and owner_list_index(recs[i][1]) in kill:
            kill.add(i)
    # loose label swaps and the text frame
    done = set()
    for i, (h, b) in enumerate(recs):
        if i in kill or owner_list_index(b) is not None:
            continue
        if b.startswith(b'|RECORD=25|'):
            for (x, y), old, new in LABEL_SWAPS:
                if (num(b, 'Location.X'), num(b, 'Location.Y')) == (x, y) and field(b, 'Text') == old:
                    recs[i][1] = set_field(b, 'Text', new); done.add((x, y))
        elif b.startswith(b'|RECORD=28|') and (field(b, 'Text') or '').startswith('X2: 44 pins'):
            recs[i][1] = set_field(b, 'Text', FRAME); done.add('frame')
    assert len(done) == 5, done
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
    print(f'sheet 2: {N} -> {len(out)} records ({len(kill)} deleted, {edited} edited)')
    verify(path)


def verify(path):
    recs = split(read_stream(path, 'FileHeader'))
    copies = [i for i, (h, b) in enumerate(recs) if b.startswith(b'|RECORD=1|') and field(b, 'LibReference') == 'ZULU-CONN']
    assert len(copies) == 43, len(copies)
    parts = sorted(int(field(recs[ci][1], 'CurrentPartId')) for ci in copies)
    assert parts == list(range(1, 44)), parts
    kids = {}
    for i, (h, b) in enumerate(recs):
        oi = owner_list_index(b)
        if oi in copies: kids.setdefault(oi, []).append(b)
    table = []
    for ci in copies:
        pins = [b for b in kids[ci] if b.startswith(b'|RECORD=2|')]
        d = sorted(int(field(b, 'Designator')) for b in pins)
        assert d == [n for n in range(1, 45) if n not in (23, 44)], d
        owners = {num(b, 'OwnerPartId') for b in kids[ci]} - {None}
        assert max(owners) <= 43 and min(owners) == -1 and sorted(owners)[1:] == list(range(1, 44)), owners   # 35 is now ANALOG-IO0
        names = {field(b, 'Name') for b in kids[ci] if b.startswith(b'|RECORD=41|')}
        assert {f'GateName_{n}' for n in range(1, 44)} <= names and 'GateName_44' not in names and 'GateName_45' not in names
        assert field(recs[ci][1], 'PartCount') == '44' and field(recs[ci][1], 'AllPinCount') == '42'
        pid = field(recs[ci][1], 'CurrentPartId')
        vis = [b for b in pins if field(b, 'OwnerPartId') == pid]
        gname = [field(b, 'Text') for b in kids[ci] if b.startswith(b'|RECORD=41|') and field(b, 'Name') == f'GateName_{pid}']
        gate = [field(b, 'Text') for b in kids[ci] if b.startswith(b'|RECORD=41|') and field(b, 'Name') == 'GATE']
        if vis:
            assert gname == gate, (gname, gate)
            table.append((int(field(vis[0], 'Designator')), gname[0]))
    for pad, name in sorted(table):
        print(f'   pad {pad:>2} {name}')
    assert dict(table)[2] == 'CHAN12' and dict(table)[3] == 'CHAN13' and dict(table)[25] == '+3.3V2' and dict(table)[26] == 'GND3'
    print(f'verify: 43 copies, 42 pins each, parts 1-43 contiguous, GATE labels match the gate names')


def pin_types(path):
    """The displayed pin of each gate copy carries the electrical type (7 power on the supply gates,
    4 passive on the channels; the hidden copies are all 1). Pads 2 and 3 now carry channels and pads
    25 and 26 supplies, so their types follow, or the compiler reports the channel nets as mixed."""
    recs = split(read_stream(path, 'FileHeader'))
    copies = {i for i, (h, b) in enumerate(recs) if b.startswith(b'|RECORD=1|') and field(b, 'LibReference') == 'ZULU-CONN'}
    n = 0
    for i, (h, b) in enumerate(recs):
        if b.startswith(b'|RECORD=2|') and owner_list_index(b) in copies:
            d, e = field(b, 'Designator'), field(b, 'Electrical')
            if d in ('2', '3') and e == '7':
                recs[i][1] = set_field(b, 'Electrical', '4'); n += 1
            elif d in ('25', '26') and e == '4':
                recs[i][1] = set_field(b, 'Electrical', '7'); n += 1
    assert n in (0, 4), n
    if n:
        blob = join(recs)
        write_stream(path, 'FileHeader', blob)
        assert read_stream(path, 'FileHeader') == blob
    print(f'pin types: {n} displayed pins retyped (2/3 passive, 25/26 power)')


def sheet1(path):
    recs = split(read_stream(path, 'FileHeader'))
    hits = [i for i, (h, b) in enumerate(recs) if b.startswith(b'|RECORD=4|') and SHEET1_OLD in (field(b, 'Text') or '')]
    assert len(hits) == 1, hits
    i = hits[0]
    recs[i][1] = set_field(recs[i][1], 'Text', field(recs[i][1], 'Text').replace(SHEET1_OLD, SHEET1_NEW))
    blob = join(recs)
    write_stream(path, 'FileHeader', blob)
    assert read_stream(path, 'FileHeader') == blob
    print('sheet 1: charger note updated')


if __name__ == '__main__':
    prj = sys.argv[2]
    sheet2(os.path.join(prj, 'zulu_a7_2.SchDoc'))
    pin_types(os.path.join(prj, 'zulu_a7_2.SchDoc'))
    sheet1(os.path.join(prj, 'zulu_a7_1.SchDoc'))
