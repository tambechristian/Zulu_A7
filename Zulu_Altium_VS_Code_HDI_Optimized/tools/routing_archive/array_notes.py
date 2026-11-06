# -*- coding: utf-8 -*-
"""Sheets 3 and 4, 2026-09-09: three NOTE parameters, after an adversarial review of the arrays.

Nothing here touches connectivity. NOTE is a hidden parameter, so the netlist and the PDF come out
identical; only the BOM's note column and docs/component_validation.md change. No record is added or
removed, so no OwnerIndex moves and the header count stands.

R34's NOTE was left stale by the array work and said the opposite of what the board now does: "unlike
R1, R2 and R4, which used 2, 3 and 6 of theirs and were split into discretes. This one stays an
array." Two of those three are arrays again.

R1's NOTE gains the tolerance question, which is the one place the 5 percent grade has a real answer.
UG470 Table 2-4 asks for <= 4.7 kohm on PROGRAM_B and INIT_B; a 5 percent 4.7 k part is 4.935 k worst
case, outside that. It is a wording problem rather than a physical one and the arithmetic is written
out so nobody has to re-derive it, along with why buying strict compliance costs availability.

R4's NOTE gains three supply caveats: the CTS 74x series is filed under Legacy Products, there is no
drop-in second source on this land, and every stock figure came from one distributor.

    python tools/array_notes.py tools "Imported zulu_a7.PrjPcb"
"""
import sys, os
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

R34_OLD = ('The microSD DAT0-3 pull-ups, all four elements used -- which is what an array is actually '
           'for, unlike R1, R2 and R4, which used 2, 3 and 6 of theirs and were split into discretes. '
           'This one stays an array.')
R34_NEW = ('The microSD DAT0-3 pull-ups, all four elements used -- which is what an array is actually '
           'for. R1, R2 and R4 used 2, 3 and 6 of theirs in the EAGLE original and were split into '
           'discretes during the import; on 2026-09-09 R1 and R4 went back into arrays of their own '
           '(742C043472JP and 742C163101JP), so all three arrays on this board are CTS 74x concave '
           'parts sharing one land-pattern rule. R2 is still a discrete.')

R1_ADD = (' TOLERANCE AGAINST UG470: Table 2-4 asks for a pull-up of 4.7 kohm OR LESS on both of these '
          'pins, and this is a 5 percent part, so its worst case is 4.935 k -- 5 percent outside the '
          'stated maximum. That is a wording problem rather than a physical one. The limit exists to '
          'hold the pin high against input leakage, and DS181 worst-case leakage of 15 uA across 4.935 k '
          'is 74 mV, against a VIH of 2.0 V. The discretes this replaces were 1 percent parts and were '
          'already outside the same limit, at 4.747 k. Strict compliance would mean 4.3 kohm +-5 percent '
          '(4.515 k worst case), but CTS does not stock a 432 code in the 742C043 family -- the stocked '
          'spread is 101, 220, 470, 471, 472, 473, 102, 103 and 104 -- so buying compliance here would '
          'cost availability, which is the thing that actually stops a board getting built. Dropping to '
          'the next stocked value, 1 k, would cost margin where it matters: it lifts the low level the '
          'bridge can assert on RST# through the 100 ohm from 0.10 V to 0.43 V.')

R4_ADD = (' SUPPLY CAVEATS, all read 2026-09-09. (1) CTS files the whole 74x series -- this part and '
          "R34's 742C083 with it -- under Legacy Products on its own site. Near-term risk is low: 25,352 "
          'stocked, MOQ 1, deep sibling stock. It is not a young family. (2) There is no drop-in second '
          'source on this land. The alternate above needs its own footprint, so this one package is a '
          'single point of failure where the six discretes it replaces had many interchangeable vendors; '
          'if that matters for the build, qualify a second 16-pad 0.80 mm concave array on the same land '
          'first. (3) Every stock and price figure here is Digi-Key alone -- Mouser, Arrow, TTI, Octopart '
          'and LCSC all refused automated reads that day -- so none of it has second-distributor '
          'corroboration. AND ONE LAYOUT POINT: the two spare elements are unplaced, so pads 7-10 carry '
          'no net. If the layout wants them as grounded metal beside TCK, that has to come back here as '
          'two more placed gates with both ends on GND; it cannot be done in the PCB alone.')


def owner_list_index(b):
    o = field(b, 'OwnerIndex')
    return int(o) + 1 if o is not None else None


def edit(path, jobs):
    """jobs: {designator: (old_fragment_or_None, replacement_or_addition)}"""
    recs = split(read_stream(path, 'FileHeader'))
    n_before = len(recs)
    assert int(field(recs[0][1], 'Weight')) == n_before - 1, 'header count is already wrong'
    desig = {owner_list_index(b): field(b, 'Text') for h, b in recs if b.startswith(b'|RECORD=34|')}
    hit = {}
    for i, (h, b) in enumerate(recs):
        if not b.startswith(b'|RECORD=41|') or field(b, 'Name') != 'NOTE':
            continue
        d = desig.get(owner_list_index(b))
        if d not in jobs:
            continue
        old, new = jobs[d]
        t = field(b, 'Text')
        if old is None:                                   # append once
            if new.strip() in t:
                continue
            t2 = t + new
        else:
            if old not in t:
                continue
            t2 = t.replace(old, new)
        recs[i][1] = set_field(b, 'Text', t2)
        hit[d] = hit.get(d, 0) + 1
    if not hit:
        raise SystemExit(f'{os.path.basename(path)}: every note is already current; nothing done')
    assert len(recs) == n_before
    blob = join(recs)
    write_stream(path, 'FileHeader', blob)
    assert read_stream(path, 'FileHeader') == blob
    print(f'{os.path.basename(path)}: ' + ', '.join(f'{d} x{c}' for d, c in sorted(hit.items())))


def main(prj):
    edit(os.path.join(prj, 'zulu_a7_3.SchDoc'), {'R34': (R34_OLD, R34_NEW)})
    edit(os.path.join(prj, 'zulu_a7_4.SchDoc'), {'R1': (None, R1_ADD), 'R4': (None, R4_ADD)})
    verify(prj)


def verify(prj):
    for n in (3, 4):
        path = os.path.join(prj, f'zulu_a7_{n}.SchDoc')
        recs = split(read_stream(path, 'FileHeader'))
        assert int(field(recs[0][1], 'Weight')) == len(recs) - 1, f'sheet {n} header count'
        assert all(b.endswith(b'\x00') for h, b in recs), f'sheet {n} terminator'
        desig = {owner_list_index(b): field(b, 'Text') for h, b in recs if b.startswith(b'|RECORD=34|')}
        notes = {}
        for h, b in recs:
            if b.startswith(b'|RECORD=41|') and field(b, 'Name') == 'NOTE':
                notes.setdefault(desig.get(owner_list_index(b)), set()).add(field(b, 'Text'))
        for d, texts in notes.items():
            assert d is None or len(texts) == 1, f'{d} carries {len(texts)} different notes'
        if n == 3:
            assert R34_OLD not in list(notes['R34'])[0], 'R34 still claims R1 and R4 are discretes'
            assert '742C163101JP' in list(notes['R34'])[0]
        else:
            assert 'OR LESS' in list(notes['R1'])[0], 'R1 has no tolerance note'
            assert 'Legacy Products' in list(notes['R4'])[0], 'R4 has no supply note'
            assert len(notes['R1']) == 1 and len(notes['R4']) == 1
    print('verify: three notes current, both sheets intact, no record added or removed')


if __name__ == '__main__':
    main(sys.argv[2])
