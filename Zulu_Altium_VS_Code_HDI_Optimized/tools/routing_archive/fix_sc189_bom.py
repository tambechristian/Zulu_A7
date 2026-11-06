# -*- coding: utf-8 -*-
"""Bring the part numbers on the SC189 section in line with the values.

tools/sc189_power_section.py changed the visible values of L2/L3 (1.5uH),
C82/C84 (22uF) and C78 (10uF 10V) but left the hidden MANF#/SPEC parameters
from the LTC3569 design, and cloned the three input caps from a 6.3 V part.
Checked against the Semtech SC189 datasheet (2010-08-27) on 2026-09-06:

  * L1-L3  Murata DFE252010P-1R5M=P2, 1.5 uH; ripple <= 0.31 A p-p at 2.5 MHz,
           so the peak stays under 1 A even at the 677 mA worst case
  * C80    GRM21BR61A226ME44L 22 uF 10 V 0805 (unchanged, text only)
  * C82/84 GRM188R60J226MEA0D 22 uF 6.3 V 0603 on the 1.8 V and 1.0 V rails
  * C78    GRM21BR61A106KE19L 10 uF 10 V 0805 (the old number was the 22 uF part)
  * C147-9 GRM21BR61A106KE19L 10 uF 10 V 0805 at each VIN pin; the datasheet
           asks for >= 4.7 uF effective and its own reference design uses an
           0805, a 6.3 V 0603 is down to ~3 uF at 5 V.  Footprint moves
           C0603 -> C0805 with it.

Keyed by designator, so it can run on the installed sheet and is idempotent.
Run with the project closed in Altium:
    python tools/fix_sc189_bom.py tools "Imported zulu_a7.PrjPcb/zulu_a7_1.SchDoc"
"""
import sys
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

L_SPEC = '1.5uH +-20%, Isat >=1.8A, 1.00 mm max -- SC189 LX inductor, 2.5 MHz, <=0.31 A p-p ripple'
EDITS = {
    'L1':   {'MANF#': 'DFE252010P-1R5M=P2', 'SPEC': L_SPEC},
    'L2':   {'MANF#': 'DFE252010P-1R5M=P2', 'SPEC': L_SPEC},
    'L3':   {'MANF#': 'DFE252010P-1R5M=P2', 'SPEC': L_SPEC},
    'C80':  {'SPEC': 'X5R 10V +-20%, 1.45 mm max -- SC189 COUT on VCC3V3, sense pin 4 lands here'},
    'C82':  {'MANF#': 'GRM188R60J226MEA0D', 'SPEC': 'X5R 6.3V +-20%, 0.80 mm max -- SC189 COUT on VCC1V8, sense pin 4 lands here'},
    'C84':  {'MANF#': 'GRM188R60J226MEA0D', 'SPEC': 'X5R 6.3V +-20%, 0.80 mm max -- SC189 COUT on VCC1V0, sense pin 4 lands here'},
    'C78':  {'MANF#': 'GRM21BR61A106KE19L', 'SPEC': 'X5R 10V +-10%, 1.45 mm max -- VU bulk after D1 (USB attach limit 10uF)'},
    'C147': {'MANF#': 'GRM21BR61A106KE19L', 'SPEC': 'X5R 10V +-10%, 1.45 mm max -- SC189 CIN, at pins 1-2 of U5', 'DeviceName': 'C0805'},
    'C148': {'MANF#': 'GRM21BR61A106KE19L', 'SPEC': 'X5R 10V +-10%, 1.45 mm max -- SC189 CIN, at pins 1-2 of U6', 'DeviceName': 'C0805'},
    'C149': {'MANF#': 'GRM21BR61A106KE19L', 'SPEC': 'X5R 10V +-10%, 1.45 mm max -- SC189 CIN, at pins 1-2 of U7', 'DeviceName': 'C0805'},
}
FOOTPRINT = {'C147': 'C0805', 'C148': 'C0805', 'C149': 'C0805'}

def main(path):
    data = read_stream(path, 'FileHeader')
    recs = split(data)
    desig = {int(field(b, 'OwnerIndex')) + 1: field(b, 'Text') for h, b in recs if b.startswith(b'|RECORD=34|')}
    comp_idx = {d: i for i, d in desig.items() if d in EDITS}
    missing = set(EDITS) - set(comp_idx)
    if missing:
        raise SystemExit(f'not on this sheet: {sorted(missing)}')
    done = []
    for i, rec in enumerate(recs):
        b = rec[1]
        owner = field(b, 'OwnerIndex')
        if owner is None:
            continue
        d = desig.get(int(owner) + 1)
        if d not in EDITS:
            continue
        if b.startswith(b'|RECORD=41|'):
            name = field(b, 'Name')
            if name in EDITS[d] and field(b, 'Text') != EDITS[d][name]:
                done.append(f"{d} {name}: {field(b, 'Text')!r} -> {EDITS[d][name]!r}")
                rec[1] = set_field(b, 'Text', EDITS[d][name])
    # footprint: RECORD=44 (owned by the component) -> RECORD=45 (owned by the 44) carries ModelName
    for d, i in comp_idx.items():
        if d not in FOOTPRINT:
            continue
        impls = [j for j, (h, b) in enumerate(recs) if b.startswith(b'|RECORD=44|') and field(b, 'OwnerIndex') == str(i - 1)]
        for j in impls:
            for k, (h, b) in enumerate(recs):
                if b.startswith(b'|RECORD=45|') and field(b, 'OwnerIndex') == str(j - 1) and field(b, 'ModelName') == 'C0603':
                    done.append(f"{d} footprint: {field(b, 'ModelName')!r} -> {FOOTPRINT[d]!r}")
                    recs[k][1] = set_field(b, 'ModelName', FOOTPRINT[d])
    # the component's own LibReference/DesignItemId carry the package too
    for d, i in comp_idx.items():
        if d in FOOTPRINT:
            b = recs[i][1]
            for key in ('LibReference', 'DesignItemId'):
                v = field(b, key)
                if v and v.endswith('C0603'):
                    done.append(f'{d} {key}: {v!r} -> {v[:-5] + FOOTPRINT[d]!r}')
                    b = set_field(b, key, v[:-5] + FOOTPRINT[d])
            recs[i][1] = b
    out = join(recs)
    if out == data:
        print('nothing to do')
        return
    write_stream(path, 'FileHeader', out)
    assert read_stream(path, 'FileHeader') == out
    print(f'{len(done)} edits:')
    for x in done:
        print('  ' + x)

if __name__ == '__main__':
    main(sys.argv[2])
