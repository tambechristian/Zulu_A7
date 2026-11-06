# -*- coding: utf-8 -*-
"""D2: the NOTE parameter, 2026-09-09.

Sheet 2. D2 is the Schottky that ORs the +5V-INPUT header pin onto VU. It carried no NOTE,
and the master BOM (docs/zulu_a7-bom.csv, written by master_bom.py from the sheets) had been
carrying a hand-written note for it from the file's previous edit. The note belongs on the
sheet like every other one, so this appends one hidden NOTE parameter to D2, cloned from its
MANF# parameter record (same fonts and colour, IndexInSheet -1 as on the parts built here,
fresh UniqueID). Appended at the end of the record list, so no OwnerIndex changes; the header
Weight is bumped. Refuses to run twice.

    python tools/d2_note.py tools "Imported zulu_a7.PrjPcb/zulu_a7_2.SchDoc"
"""
import sys, random, string
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

NOTE = ('D1 (the Schottky between the USB VBUS and VU) was removed on 2026-09-09: USB5V0 now feeds the bq24232 '
        'charger U8, whose input FET does the reverse blocking. D2 (+5V-INPUT ORing onto VU) stays. Footprint: '
        'PMEG2020EJ is SOD323F, the SOD123 pattern is wrong (component_validation.md finding 2).')


def uid():
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(8))


def main(path):
    recs = split(read_stream(path, 'FileHeader'))
    head = recs[0][1]
    assert int(field(head, 'Weight')) == len(recs) - 1
    des = {int(field(b, 'OwnerIndex')) + 1: field(b, 'Text') for h, b in recs if b.startswith(b'|RECORD=34|')}
    ci = [i for i, d in des.items() if d == 'D2']
    assert len(ci) == 1, ci
    obj = ci[0] - 1
    prm = {}
    for i, (h, b) in enumerate(recs):
        if b.startswith(b'|RECORD=41|') and field(b, 'OwnerIndex') is not None and int(field(b, 'OwnerIndex')) == obj:
            prm[field(b, 'Name')] = i
    assert 'NOTE' not in prm, 'already applied'
    h, b = recs[prm['MANF#']]
    nb = set_field(set_field(set_field(set_field(b, 'Text', NOTE), 'Name', 'NOTE'), 'UniqueID', uid()), 'IndexInSheet', '-1')
    assert field(nb, 'IsHidden') == 'T' and field(nb, 'OwnerIndex') == str(obj)
    recs.append([h, nb])
    recs[0][1] = set_field(head, 'Weight', str(len(recs) - 1))
    out = join(recs)
    write_stream(path, 'FileHeader', out)
    assert read_stream(path, 'FileHeader') == out
    print(f'D2: NOTE appended as record {len(recs) - 1}, Weight {len(recs) - 1}')


if __name__ == '__main__':
    main(sys.argv[2])
