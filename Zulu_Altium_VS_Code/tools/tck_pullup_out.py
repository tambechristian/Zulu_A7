# -*- coding: utf-8 -*-
"""Sheet 4, 2026-09-09: R89 comes off TCK, so the clock has one idle level instead of a divider.

THE DEFECT. TCK was biased from both ends, across the damping resistor. R89, 10 K to VCC3V3, sat on
the BRIDGE side on net TCK; R5, 5.1 K to ground, sits on the FPGA side on net FPGA-TCK; the 100 ohm
element between them meant neither end won. Whenever ADBUS0 is tri-state -- at power-up and any time
no USB host has opened the MPSSE -- the FPGA's TCK input sat at

    3.3 x 5100 / (10000 + 100 + 5100) = 1.11 V

which is between VIL 0.8 V and VIH 2.0 V. That is a clock pin held in its input buffer's linear
region: crowbar current, and the one condition in which coupled noise can manufacture an edge. The
consequence was bounded -- TMS idles high through R92, so the TAP sits in Test-Logic-Reset and stray
edges only hold it there -- but a mid-rail idle is the opposite of what UG470 Table 2-4 asks for when
it says to treat TCK as a critical clock. docs/connectivity_check.md had been reporting the 1.11 V
since the bias solver was written and excusing it on the grounds that the bridge drives the pin,
which is exactly what the bridge does not do until a host opens it.

THE FIX, and why this way round. Drop the pull-up, keep the pull-down: TCK then idles LOW, which is
the JTAG convention and the safe level for a clock -- an idle-high clock line is the one that makes
an edge when it sags. Nothing wants TCK high. R5 alone puts FPGA-TCK at 0 V, and the bridge-side net
follows through the 100 ohm. Even allowing for the FT2232H's own ~200 K internal pull-up on a
tri-state ADBUS pin, which this project's solver does not model, the divider becomes 200 K against
5.2 K and lands at 0.08 V. TCK is the only one of the four JTAG lines with a pull-down to fight:
TDI, TDO and TMS keep R90, R91 and R92 and rest cleanly at 3.3 V.

WHAT MOVES. R89 and its subtree go. Its rail drop, the wire (662,1052)-(662,1072)-(692,1072), goes
with it, and so does the junction at (692,1072), which was a three-wire branch and becomes a plain
corner where R90's drop meets the rail. The wire that carries U2 pin 16 out to the pull-up column is
NOT deleted -- it holds the TCK net label at (640,982), and without it ADBUS0 would have no name --
it is shortened from three points to two, ending at (662,982) where it used to turn down.

Deleting records renumbers every later OwnerIndex and rewrites the header count. Refuses to run twice.

    python tools/tck_pullup_out.py tools "Imported zulu_a7.PrjPcb/zulu_a7_4.SchDoc"
"""
import sys, re
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

VICTIM = 'R89'
DROP_WIRE = ((662, 1052), (662, 1072), (692, 1072))     # R89 to the VCC3V3 rail
DEAD_JUNCTION = (692, 1072)                             # three wires met here; two will
TCK_WIRE = ((607, 982), (662, 982), (662, 1032))        # U2 pin 16 -> label -> R89
TCK_WIRE_NEW = ((607, 982), (662, 982))


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
    if VICTIM not in desig.values():
        raise SystemExit(f'{VICTIM} is already gone; nothing done')
    r89 = [i for i, d in desig.items() if d == VICTIM][0]
    assert (num(recs[r89][1], 'Location.X'), num(recs[r89][1], 'Location.Y')) == (662, 1042), \
        f'{VICTIM} is not where this script expects it'

    kill, done = set(subtree(recs, r89)), set()
    survivors = []                      # (old index, body) in order, after the deletions
    for i, (h, b) in enumerate(recs):
        if i in kill:
            continue
        if owner_list_index(b) is None:
            p = wire_pts(b)
            xy = (num(b, 'Location.X'), num(b, 'Location.Y'))
            if p == DROP_WIRE:
                done.add('drop wire'); continue
            if b.startswith(b'|RECORD=29|') and xy == DEAD_JUNCTION:
                done.add('junction'); continue
            if p == TCK_WIRE:                      # shorten: U2-16 keeps its wire and its label
                b = set_field(b, 'LocationCount', str(len(TCK_WIRE_NEW)))
                b = re.sub(rb'\|X3=-?\d+', b'', re.sub(rb'\|Y3=-?\d+', b'', b))
                done.add('tck wire')
        survivors.append((i, [h, b]))

    want = {'drop wire', 'junction', 'tck wire'}
    assert done == want, sorted(want ^ done)
    newpos = {old: new for new, (old, _) in enumerate(survivors)}
    fixed = []
    for old, (h, b) in survivors:
        oi = owner_list_index(b)
        if oi is not None:
            assert oi in newpos, f'record {old} is owned by a deleted record'
            b = set_field(b, 'OwnerIndex', str(newpos[oi] - 1))
        fixed.append([h, b])
    fixed[0][1] = set_field(fixed[0][1], 'Weight', str(len(fixed) - 1))
    blob = join(fixed)
    write_stream(path, 'FileHeader', blob)
    assert read_stream(path, 'FileHeader') == blob
    print(f'sheet 4: {N} -> {len(fixed)} records ({len(kill)} for {VICTIM}, its rail drop and one junction)')
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
    assert VICTIM not in desig.values(), f'{VICTIM} is still on the sheet'
    for keep in ('R90', 'R91', 'R92', 'R99', 'R5'):
        assert keep in desig.values(), f'{keep} went missing'
    wires = {wire_pts(b) for h, b in recs if b.startswith(b'|RECORD=27|')}
    juncs = {(num(b, 'Location.X'), num(b, 'Location.Y')) for h, b in recs if b.startswith(b'|RECORD=29|')}
    labels = {(num(b, 'Location.X'), num(b, 'Location.Y')): field(b, 'Text')
              for h, b in recs if b.startswith(b'|RECORD=25|') and owner_list_index(b) is None}
    assert DROP_WIRE not in wires, 'the rail drop survived'
    assert DEAD_JUNCTION not in juncs, 'the junction survived'
    assert TCK_WIRE not in wires and TCK_WIRE_NEW in wires, 'the TCK wire was not shortened'
    assert labels.get((640, 982)) == 'TCK', 'the TCK label lost its wire'
    for w in (((692, 1052), (692, 1072)), ((692, 1072), (722, 1072)),
              ((722, 1072), (742, 1072)), ((742, 1072), (742, 1077))):
        assert w in wires, f'the VCC3V3 rail lost {w}'
    for x in (722, 742, 752):
        assert (x, 1072) in juncs, f'junction at ({x},1072) went missing'
    print(f'verify: {len(recs)} records, {VICTIM} gone with its drop and junction, U2 pin 16 still '
          'carries the TCK label, R90/R91/R92/R99 still on the rail')


if __name__ == '__main__':
    main(sys.argv[2])
