# -*- coding: utf-8 -*-
"""C123 becomes the 0201 100 nF and goes to U1's analog balls, 2026-09-16 (the user's choice).

WHY.  Xilinx UG480 Figure 6-1 (on-chip reference) filters VCCAUX through a ferrite bead into VCCADC with
a 470 nF at the bead and a 100 nF at the package, and its Note 1 says: "Place the 100 nF capacitor as
close as possible to the package balls."  On this board the 100 nF (C123) sat at the bead L7, about
17 mm of analog pair from U1, while the 470 nF (C124) was the bead's filter capacitor -- right where the
figure draws it.  So C123 moves, C124 stays.  An 0201 is what fits among U1's fan-out vias.

THE PART.  Murata GRM033R61A104KE15D, X5R 10 V 0.1 uF 0201 -- already the board's 0201 100 nF on eleven
positions (C40, C41, C133-C138, C152-C154), so no new BOM line.  On a 1.8 V rail a 10 V X5R keeps most of
its capacitance.

THE EDIT.  Records rewritten in place on sheet 5, nothing added, nothing renumbered:
    component   LibReference and DesignItemId   C-USC0402 -> C-USC0201   (as C89 etc. on sheet 6)
    parameter   DeviceName                      C0402     -> C0201
    parameter   MANF#                           GRM155R71C104KA88D -> GRM033R61A104KE15D  (MANF stays Murata)
    parameter   SPEC                            the 0402 X7R text -> the 0201 X5R text and the reason
    model       ModelName (PCBLIB)              C0402     -> C0201
The Comment stays 100nF.  Run with sheet 5 closed in Altium:

    python tools/c123_to_0201.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

PATH = os.path.join(os.path.dirname(HERE), 'Imported zulu_a7.PrjPcb', 'zulu_a7_5.SchDoc')
PART = 'C123'
SPEC = ("X5R 10V +-10% 0201 0.1uF, 0.30 mm max -- moved 2026-09-16 from the L7 bead to U1's VCCADC/GNDADC "
        "balls: UG480 Fig 6-1 Note 1 puts the 100 nF as close as possible to the package balls, the 470 nF "
        "(C124) at the bead")


def main():
    data = read_stream(PATH, 'FileHeader')
    recs = split(data)
    hits = [int(field(b, 'OwnerIndex')) + 1 for h, b in recs
            if b.startswith(b'|RECORD=34|') and field(b, 'Text') == PART]
    if len(hits) != 1:
        raise SystemExit('%s appears %d times on sheet 5; nothing done' % (PART, len(hits)))
    ci = hits[0]
    tree, lvl = set(), [ci]
    while lvl:
        nxt = [i for i, (h, b) in enumerate(recs)
               if field(b, 'OwnerIndex') in {str(j - 1) for j in lvl} and i not in tree]
        tree |= set(nxt)
        lvl = nxt

    comp = recs[ci][1]
    if field(comp, 'LibReference') == 'C-USC0201':
        print('%s already converted; nothing done' % PART)
        return
    assert field(comp, 'LibReference') == 'C-USC0402' and field(comp, 'DesignItemId') == 'C-USC0402', comp
    comp = set_field(comp, 'LibReference', 'C-USC0201')
    comp = set_field(comp, 'DesignItemId', 'C-USC0201')
    recs[ci][1] = comp

    changed = {'DeviceName': 0, 'MANF#': 0, 'SPEC': 0, 'model': 0}
    for i in sorted(tree):
        b = recs[i][1]
        if b.startswith(b'|RECORD=41|'):
            name = field(b, 'Name')
            if name == 'DeviceName':
                assert field(b, 'Text') == 'C0402', b
                recs[i][1] = set_field(b, 'Text', 'C0201')
                changed['DeviceName'] += 1
            elif name == 'MANF#':
                assert field(b, 'Text') == 'GRM155R71C104KA88D', b
                recs[i][1] = set_field(b, 'Text', 'GRM033R61A104KE15D')
                changed['MANF#'] += 1
            elif name == 'SPEC':
                recs[i][1] = set_field(b, 'Text', SPEC)
                changed['SPEC'] += 1
            elif name == 'MANF':
                assert field(b, 'Text') == 'Murata', b
        elif b.startswith(b'|RECORD=45|') and field(b, 'ModelType') == 'PCBLIB':
            assert field(b, 'ModelName') == 'C0402', b
            b = set_field(b, 'ModelName', 'C0201')
            if field(b, 'ModelDatafileEntity0') is not None:
                b = set_field(b, 'ModelDatafileEntity0', 'C0201')
            recs[i][1] = b
            changed['model'] += 1
    assert changed == {'DeviceName': 1, 'MANF#': 1, 'SPEC': 1, 'model': 1}, changed
    left = sum(recs[i][1].count(b'C0402') for i in tree | {ci})
    assert left == 0, '%d copies of C0402 survived in %s' % (left, PART)

    out = join(recs)
    write_stream(PATH, 'FileHeader', out)
    assert read_stream(PATH, 'FileHeader') == out
    back = split(read_stream(PATH, 'FileHeader'))
    assert len(back) == len(recs)
    print('%s: C0402 -> C0201 (LibReference, DesignItemId, DeviceName, model), MANF# -> GRM033R61A104KE15D, SPEC '
          'rewritten; %d records, none added or renumbered' % (PART, len(back)))


if __name__ == '__main__':
    main()
