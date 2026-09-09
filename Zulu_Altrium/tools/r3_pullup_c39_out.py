# -*- coding: utf-8 -*-
"""Sheet 4, 2026-09-09: R3 becomes a pull-up, and one of the two core bulk capacitors goes.

TWO CHANGES.

R3 MOVES FROM GROUND TO VCC3V3. docs/connectivity_check.md solved the resistor network on every
dedicated configuration pin and found PROGRAM_B (ball V10, net RST#) resting at 1.63 V, between the
0.8 V that reads low and the 2.0 V that reads high, and within 20 mV of half rail. R3, 4.7 k, pulled
it DOWN; the only pull-up, R99, sits on the far side of R9's 100 ohm on net PROG#, and the FT2232H
pin that drives that node is tri-state until a USB host opens the bridge. UG470 requires this pin to
be pulled up to VCCO_0. Moving R3's lower end to VCC3V3 puts it at 3.3 V at rest while leaving both
ways of resetting the FPGA intact: the header pin X2-23 still pulls it down, and the bridge still
drives it down through R9. The lower end is redrawn the way R1, the INIT_B pull-up on this same
sheet, is drawn: the ground symbol is removed and a VCC3V3 net label is put on the end of the stub.

C39 GOES. FT-VCORE carried two 4.7 uF parts, C39 and C139, and no high-frequency decoupling.
C152, C153 and C154 supplied the missing 100 nF at each VCORE pin on 2026-09-09, and DS_FT2232H
Figures 4.1 and 6.1 show ONE 4.7 uF on that rail beside those, not two, so removing C39 leaves the
rail exactly as FTDI draws it. Worth knowing when reading the result: the three 0.1 uF parts are not
what makes C39 redundant -- high-frequency decoupling does not substitute for bulk -- C139 is, and
it alone carries about 3.7 uF once derated at 1.8 V, which is what the reference asks for and not
much more. Its stub, ground symbol, net label and the junction where it met the rail go with it, and
the rail is left as two collinear wires meeting at x 162.

Deleting records renumbers every later OwnerIndex and rewrites the header count. Refuses to run twice.

    python tools/r3_pullup_c39_out.py tools "Imported zulu_a7.PrjPcb/zulu_a7_4.SchDoc"
"""
import sys, random, string
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

R3_PORT = (747, 282)                     # the GND symbol on the end of R3's lower stub
R3_STUB = ((747, 282), (747, 292))       # wire from that symbol to R3 pin 2
C39_DEAD_WIRES = {((162, 967), (162, 977)), ((162, 997), (162, 1007)),
                  ((162, 1007), (162, 1017)), ((162, 1017), (162, 1032))}
C39_GND = (162, 967)
C39_LABEL = (162, 1002)
C39_JUNCTION = (162, 1032)


def uid():
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(8))


def num(b, k):
    v = field(b, k)
    return int(v) if v is not None else None


def owner_list_index(b):
    o = field(b, 'OwnerIndex')
    return int(o) + 1 if o is not None else None


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
    return members


def main(path):
    recs = split(read_stream(path, 'FileHeader'))
    N = len(recs)
    assert int(field(recs[0][1], 'Weight')) == N - 1, 'header count is already wrong'
    desig = {owner_list_index(b): field(b, 'Text') for h, b in recs if b.startswith(b'|RECORD=34|')}
    if 'C39' not in desig.values():
        raise SystemExit('C39 is already gone; nothing done')
    c39 = [i for i, d in desig.items() if d == 'C39'][0]
    r3 = [i for i, d in desig.items() if d == 'R3'][0]
    assert num(recs[r3][1], 'Location.X') == 747, 'R3 is not where this script expects it'
    label_tpl = next(b for h, b in recs if b.startswith(b'|RECORD=25|') and field(b, 'Text') == 'VCC3V3')

    kill = set(subtree(recs, c39))
    found = set()
    for i, (h, b) in enumerate(recs):
        if owner_list_index(b) is not None:
            continue
        p = wire_pts(b)
        xy = (num(b, 'Location.X'), num(b, 'Location.Y'))
        if p and len(p) == 2 and p in C39_DEAD_WIRES:
            kill.add(i); found.add(p)
        elif b.startswith(b'|RECORD=17|') and xy == C39_GND and field(b, 'Text') == 'GND':
            kill.add(i); found.add('c39 gnd')
        elif b.startswith(b'|RECORD=25|') and xy == C39_LABEL and field(b, 'Text') == 'FT-VCORE':
            kill.add(i); found.add('c39 label')
        elif b.startswith(b'|RECORD=29|') and xy == C39_JUNCTION:
            kill.add(i); found.add('c39 junction')
        elif b.startswith(b'|RECORD=17|') and xy == R3_PORT and field(b, 'Text') == 'GND':
            kill.add(i); found.add('r3 gnd')
    want = set(C39_DEAD_WIRES) | {'c39 gnd', 'c39 label', 'c39 junction', 'r3 gnd'}
    assert found == want, sorted(map(str, want ^ found))
    assert any(wire_pts(b) == R3_STUB for h, b in recs), 'R3 stub wire not found'

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
    # R3's lower end now names VCC3V3, drawn the way R1 is
    nb = set_field(set_field(set_field(label_tpl, 'Location.X', str(R3_PORT[0])),
                             'Location.Y', str(R3_PORT[1])), 'UniqueID', uid())
    out.append([bytes(4), nb if nb.endswith(b'\x00') else nb + bytes(1)])
    out[0][1] = set_field(out[0][1], 'Weight', str(len(out) - 1))
    blob = join(out)
    write_stream(path, 'FileHeader', blob)
    assert read_stream(path, 'FileHeader') == blob
    print(f'sheet 4: {N} -> {len(out)} records ({len(kill)} deleted, 1 added)')
    verify(path)


def verify(path):
    recs = split(read_stream(path, 'FileHeader'))
    assert int(field(recs[0][1], 'Weight')) == len(recs) - 1, 'header count'
    assert all(b.endswith(b'\x00') for h, b in recs), 'a record lost its terminator'
    uids = [field(b, 'UniqueID') for h, b in recs if field(b, 'UniqueID')]
    assert len(uids) == len(set(uids)), 'duplicate UniqueID'
    for i, (h, b) in enumerate(recs):
        oi = owner_list_index(b)
        if oi is not None:
            assert 0 <= oi < len(recs) and recs[oi][1].startswith(
                (b'|RECORD=1|', b'|RECORD=2|', b'|RECORD=44|', b'|RECORD=45|')), (i, oi)
    desig = {owner_list_index(b): field(b, 'Text') for h, b in recs if b.startswith(b'|RECORD=34|')}
    assert 'C39' not in desig.values(), 'C39 is still on the sheet'
    assert 'R3' in desig.values() and 'C139' in desig.values(), 'R3 or C139 went missing'
    ports = {(num(b, 'Location.X'), num(b, 'Location.Y')): field(b, 'Text')
             for h, b in recs if b.startswith(b'|RECORD=17|')}
    labels = {(num(b, 'Location.X'), num(b, 'Location.Y')): field(b, 'Text')
              for h, b in recs if b.startswith(b'|RECORD=25|') and owner_list_index(b) is None}
    assert R3_PORT not in ports, 'the ground symbol under R3 is still there'
    assert labels.get(R3_PORT) == 'VCC3V3', 'R3 does not name VCC3V3'
    wires = {wire_pts(b) for h, b in recs if b.startswith(b'|RECORD=27|')}
    assert R3_STUB in wires, 'R3 lost its stub'
    for wpt in C39_DEAD_WIRES:
        assert wpt not in wires, f'{wpt} survived'
    assert ((62, 1032), (162, 1032)) in wires and ((162, 1032), (462, 1032)) in wires, 'the core rail is broken'
    juncs = {(num(b, 'Location.X'), num(b, 'Location.Y')) for h, b in recs if b.startswith(b'|RECORD=29|')}
    assert C39_JUNCTION not in juncs and (92, 1032) in juncs and (122, 1032) in juncs, 'junctions wrong'
    print(f'verify: {len(recs)} records, ids unique, R3 now names VCC3V3, C39 and its stub gone, '
          'the core rail still whole with C152-C154 and C139 on it')


if __name__ == '__main__':
    main(sys.argv[2])
