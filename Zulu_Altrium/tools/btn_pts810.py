# -*- coding: utf-8 -*-
"""BTN: PTA-142 (no maker, no distributor) -> C&K / Littelfuse PTS810SJM250SMTR LFS, 2026-09-08.

Sheet 2. The PTS810 (Datasheet/Littelfuse-CK-Tactile-PTS810-Series-Datasheet.pdf, rev 02/02/26)
is a 4.2 x 3.2 x 2.5 mm J-lead SMT tactile switch, SPST-NO momentary, 16 VDC 50 mA, 1.6 N
(160 gf) in the M grade, 150,000 operations, -40..85 C. Its schematic joins terminals 1-2 and
3-4, which is what the SWITCH_TACT symbol already does with pins "1,2" (VCC3V3) and "3,4"
(BTN), so the wiring is untouched. The land pattern is new: four pads 1.05 x 0.65 mm centred
at +-2.075 x +-1.075 mm (5.2 x 2.8 mm envelope), so the footprint model is renamed PTS810 for
the PCB stage; the PTA-142 pattern (1.6 mm pads at +-3.75 / +-1.4) does not fit.

Edits: MANF#, SPEC, Comment and NOTE parameters; a MANF parameter inserted after Comment (the
EAGLE part had none) with every later OwnerIndex shifted by one and the header Weight bumped;
the footprint ModelName. Refuses to run twice.

    python tools/btn_pts810.py tools "Imported zulu_a7.PrjPcb/zulu_a7_2.SchDoc"
"""
import sys, random, string
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

NEW_MPN = 'PTS810SJM250SMTR LFS'
SPEC = ('tactile switch SPST-NO momentary, SMT J-lead, 4.2 x 3.2 x 2.5 mm, 1.6 N (160 gf), 0.15 mm travel, '
        '150000 cycles, 16 VDC 50 mA, -40..85 C; terminals 1-2 and 3-4 internally common (PTS810 sheet p1); '
        'replaced the unsourceable PTA-142 on 2026-09-08')
NOTE = ('PTS810SJM250SMTR LFS, Littelfuse (C&K) PTS810 series, Datasheet/Littelfuse-CK-Tactile-PTS810-Series-Datasheet.pdf '
        'rev 02/02/26. Recommended PCB layout (p1): four pads (5.2 - 3.1)/2 = 1.05 mm wide by (2.8 - 1.5)/2 = 0.65 mm high, '
        'centred at +-2.075 mm and +-1.075 mm; body 4.2 x 3.2 mm, J-leads to 4.6 mm, height 2.5 mm. The datasheet schematic '
        'joins 1 with 2 and 3 with 4, so pins 1,2 (VCC3V3) and 3,4 (BTN) are unchanged. Footprint PTS810 to be drawn at the '
        'PCB stage; the PTA-142 pattern (1.6 mm pads at +-3.75 / +-1.4 mm) does not fit. Other force grades on the same '
        'pads: K 2.6 N, G 4.0 N, S 6.0 N. Digi-Key 106,352 in stock at $0.58, 16-week lead (2026-09-08); LCSC C116501 dry, '
        'the K grade C221896 stocked.')


def uid():
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(8))


def main(path):
    data = read_stream(path, 'FileHeader')
    recs = split(data)
    head = recs[0][1]
    weight = int(field(head, 'Weight'))
    assert weight == len(recs) - 1, (weight, len(recs))
    des = {int(field(b, 'OwnerIndex')) + 1: field(b, 'Text') for h, b in recs if b.startswith(b'|RECORD=34|')}
    comp = [i for i, d in des.items() if d == 'BTN']
    assert len(comp) == 1, comp
    ci = comp[0]                      # list index of the component record
    obj = ci - 1                      # object index children point at
    assert recs[ci][1].startswith(b'|RECORD=1|')
    prm = {}
    for i, (h, b) in enumerate(recs):
        if b.startswith(b'|RECORD=41|') and field(b, 'OwnerIndex') is not None and int(field(b, 'OwnerIndex')) == obj:
            prm[field(b, 'Name')] = i
    assert field(recs[prm['MANF#']][1], 'Text') == 'PTA-142', 'already applied'
    assert 'MANF' not in prm
    recs[prm['MANF#']][1] = set_field(recs[prm['MANF#']][1], 'Text', NEW_MPN)
    recs[prm['SPEC']][1] = set_field(recs[prm['SPEC']][1], 'Text', SPEC)
    recs[prm['NOTE']][1] = set_field(recs[prm['NOTE']][1], 'Text', NOTE)
    # the visible comment sits at (775, 1002) with the vertical N$BTN label 55 mils to its right: the full number
    # would run into it, so the sheet shows the family name and the full number lives in MANF#
    recs[prm['Comment']][1] = set_field(recs[prm['Comment']][1], 'Text', 'PTS810')
    # footprint model: RECORD=44 owned by the component, RECORD=45 owned by that 44
    i44 = [i for i, (h, b) in enumerate(recs) if b.startswith(b'|RECORD=44|') and int(field(b, 'OwnerIndex')) == obj]
    assert len(i44) == 1, i44
    i45 = [i for i, (h, b) in enumerate(recs) if b.startswith(b'|RECORD=45|') and int(field(b, 'OwnerIndex')) == i44[0] - 1]
    assert len(i45) == 1, i45
    assert field(recs[i45[0]][1], 'ModelName') == 'PTA-142', field(recs[i45[0]][1], 'ModelName')
    recs[i45[0]][1] = set_field(recs[i45[0]][1], 'ModelName', 'PTS810')
    # parent map before the insertion, keyed by UniqueID (records without one are skipped)
    def parents(rs):
        out = {}
        for h, b in rs:
            u = field(b, 'UniqueID'); oi = field(b, 'OwnerIndex')
            if u and oi is not None:
                pb = rs[int(oi) + 1][1]
                out[u] = (b[:12], pb[:12], field(pb, 'UniqueID'))
        return out
    before = parents(recs)
    # insert MANF right after the MANF# parameter
    base = recs[prm['MANF#']][1]
    new = set_field(set_field(set_field(base, 'Text', 'Littelfuse (C&K)'), 'Name', 'MANF'), 'UniqueID', uid())
    new = set_field(new, 'IndexInSheet', str(int(field(base, 'IndexInSheet')) + 1))
    pos = prm['MANF#'] + 1            # list index the new record takes
    new_obj = pos - 1                 # object index it takes; every OwnerIndex >= new_obj moves up by one
    recs.insert(pos, [recs[prm['MANF#']][0], new])   # same 4-byte record header as the parameter it follows
    for i in range(len(recs)):
        b = recs[i][1]
        oi = field(b, 'OwnerIndex')
        if oi is not None and int(oi) >= new_obj and i != pos:
            recs[i][1] = set_field(b, 'OwnerIndex', str(int(oi) + 1))
    recs[0][1] = set_field(head, 'Weight', str(len(recs) - 1))
    after = parents(recs)
    changed = [u for u in before if before[u] != after.get(u)]
    assert not changed, changed[:5]
    out = join(recs)
    write_stream(path, 'FileHeader', out)
    assert read_stream(path, 'FileHeader') == out
    print(f'BTN -> {NEW_MPN}; MANF inserted at {pos}, {len(recs) - 1} records, footprint PTS810, parents intact')


if __name__ == '__main__':
    main(sys.argv[2])
