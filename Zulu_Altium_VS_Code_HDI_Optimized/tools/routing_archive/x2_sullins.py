# -*- coding: utf-8 -*-
"""X2: the ZULU-CONN placeholder gets its part numbers, 2026-09-08.

Sheet 2. X2 is the breadboard pin field (EAGLE package ZULU-DIP37): two rows 0.900 in apart
on 0.1 in pitch, 1.016 mm holes, 44 fitted positions, the top row as 1-9 and 10-20 with a
four-position gap for the USB receptacle, the bottom row 21-44. It is populated with three
Sullins PRPC 0.1 in male breakaway strips mounted from the underside: PRPC024SAAN-RC (1x24,
bottom row), PRPC009SAAN-RC (1x9, top row pads 1-9) and PRPC011SAAN-RC (1x11, top row pads
10-20). The imported part carries no MANF, MANF#, SPEC or NOTE parameter at all, and every one
of its 45 placed gates is its own component record with a full parameter set, so the four
parameters are inserted after each gate's DeviceSetName parameter (180 records) with every
later OwnerIndex renumbered and the header Weight bumped. Comment (ZULU-CONN, the connector's
name on the sheet) and the ZULU-DIP37 footprint model are unchanged. Refuses to run twice.

    python tools/x2_sullins.py tools "Imported zulu_a7.PrjPcb/zulu_a7_2.SchDoc"
"""
import sys, random, string
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

MANF = 'Sullins'
MPN = 'PRPC024SAAN-RC + PRPC009SAAN-RC + PRPC011SAAN-RC'
SPEC = ('three 0.1 in male breakaway header strips, 0.64 mm square gold-flash pins, 2.54 mm pitch, through-hole, mounted from the '
        'underside: PRPC024SAAN-RC 1x24 on the bottom row (pads 21-44), PRPC009SAAN-RC 1x9 (pads 1-9) and PRPC011SAAN-RC 1x11 '
        '(pads 10-20) on the top row; one of each per board; added 2026-09-08 to the ZULU-CONN placeholder')
NOTE = ('Pin field ZULU-DIP37: 44 holes of 1.016 mm on 2.54 mm pitch, two rows 22.86 mm (0.900 in) apart, top row 1-9 and 10-20 '
        'with a four-position gap for X1, bottom row 21-44; inserted centred it lands in breadboard columns B and I. Sullins PRPC '
        'strips fit the holes (0.64 mm square pins, Sullins recommends 1.02 mm). Digi-Key 2026-09-08: PRPC024SAAN-RC 361 at $0.45, '
        'PRPC009SAAN-RC 1,201 at $0.18, PRPC011SAAN-RC 428 at $0.22. Alternates: Wurth 61302411121 for the 24-way (5,364), or any '
        '2.54 mm 1x40 breakaway strip (LCSC Boomele C2337, 81,690) cut to 24 + 11 + 9.')
NEW = [('MANF', MANF), ('MANF#', MPN), ('SPEC', SPEC), ('NOTE', NOTE)]


def uid():
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(8))


def main(path):
    recs = split(read_stream(path, 'FileHeader'))
    head = recs[0][1]
    assert int(field(head, 'Weight')) == len(recs) - 1
    des = {int(field(b, 'OwnerIndex')) + 1: field(b, 'Text') for h, b in recs if b.startswith(b'|RECORD=34|')}
    gates = sorted(i for i, d in des.items() if d == 'X2')
    assert len(gates) == 45, len(gates)
    # per gate: its parameter records; refuse if MANF# already there; find the DeviceSetName record to insert after
    insert_after = {}
    for ci in gates:
        obj = ci - 1
        prm = {}
        for i, (h, b) in enumerate(recs):
            if b.startswith(b'|RECORD=41|') and field(b, 'OwnerIndex') is not None and int(field(b, 'OwnerIndex')) == obj:
                prm[field(b, 'Name')] = i
        assert 'MANF#' not in prm, 'already applied'
        insert_after[prm['DeviceSetName']] = ci
    # parent map before, by UniqueID
    def parents(rs):
        out = {}
        for h, b in rs:
            u = field(b, 'UniqueID'); oi = field(b, 'OwnerIndex')
            if u and oi is not None:
                pb = rs[int(oi) + 1][1]
                out[u] = (b[:12], pb[:12], field(pb, 'UniqueID'))
        return out
    before = parents(recs)
    # build the new list; remember each record's owner as an OLD list index
    old_owner = {}
    new_recs = []
    old_to_new = {}
    for i, (h, b) in enumerate(recs):
        old_to_new[i] = len(new_recs)
        new_recs.append([h, b])
        oi = field(b, 'OwnerIndex')
        if oi is not None: old_owner[id(new_recs[-1])] = int(oi) + 1
        if i in insert_after:
            ci = insert_after[i]
            idx = int(field(b, 'IndexInSheet'))
            for k, (name, text) in enumerate(NEW, 1):
                nb = set_field(set_field(set_field(set_field(b, 'Text', text), 'Name', name), 'UniqueID', uid()), 'IndexInSheet', str(1000 + k))
                new_recs.append([h, nb])
                old_owner[id(new_recs[-1])] = ci
    for r in new_recs:
        if id(r) in old_owner:
            r[1] = set_field(r[1], 'OwnerIndex', str(old_to_new[old_owner[id(r)]] - 1))
    new_recs[0][1] = set_field(head, 'Weight', str(len(new_recs) - 1))
    after = parents(new_recs)
    changed = [u for u in before if before[u] != after.get(u)]
    assert not changed, changed[:5]
    assert len(new_recs) == len(recs) + 4 * 45
    out = join(new_recs)
    write_stream(path, 'FileHeader', out)
    assert read_stream(path, 'FileHeader') == out
    print(f'X2: {MPN} on 45 gates, {len(new_recs) - 1} records, parents intact')


if __name__ == '__main__':
    main(sys.argv[2])
