# -*- coding: utf-8 -*-
"""JP3 / JP4: the DNS (do not stuff) flag, 2026-09-08.

Sheet 4. The two 1x3 JTAG positions are bare plated holes for flying leads or pogo pins
(package 1X03-NOSILK, part TESTPT-1X3NOSILK); their NOTE already says "NO HEADER FITTED,
nothing to order", but the BOM had no machine-readable flag, so PCBWay's inquiry would have
stopped on two lines without a part number. This inserts two hidden parameters after each
part's NOTE: DNS = Yes (the value PCBWay's BOM template uses in its Type column) and a SPEC
line saying the same in words. Every later OwnerIndex is renumbered and the header Weight
bumped. Refuses to run twice.

    python tools/jp_dns.py tools "Imported zulu_a7.PrjPcb/zulu_a7_4.SchDoc"
"""
import sys, random, string
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

NEW = [('DNS', 'Yes'),
       ('SPEC', 'DNS - do not stuff: three bare plated holes, 1x3 on 2.54 mm, for flying leads or pogo pins; no part to order (flagged 2026-09-08)')]


def uid():
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(8))


def main(path):
    recs = split(read_stream(path, 'FileHeader'))
    head = recs[0][1]
    assert int(field(head, 'Weight')) == len(recs) - 1
    des = {int(field(b, 'OwnerIndex')) + 1: field(b, 'Text') for h, b in recs if b.startswith(b'|RECORD=34|')}
    targets = sorted(i for i, d in des.items() if d in ('JP3', 'JP4'))
    assert len(targets) == 2, targets
    insert_after = {}
    for ci in targets:
        obj = ci - 1
        prm = {}
        for i, (h, b) in enumerate(recs):
            if b.startswith(b'|RECORD=41|') and field(b, 'OwnerIndex') is not None and int(field(b, 'OwnerIndex')) == obj:
                prm[field(b, 'Name')] = i
        assert 'DNS' not in prm, 'already applied'
        insert_after[prm['NOTE']] = ci

    def parents(rs):
        out = {}
        for h, b in rs:
            u = field(b, 'UniqueID'); oi = field(b, 'OwnerIndex')
            if u and oi is not None:
                pb = rs[int(oi) + 1][1]
                out[u] = (b[:12], pb[:12], field(pb, 'UniqueID'))
        return out
    before = parents(recs)
    old_owner, new_recs, old_to_new = {}, [], {}
    for i, (h, b) in enumerate(recs):
        old_to_new[i] = len(new_recs)
        new_recs.append([h, b])
        oi = field(b, 'OwnerIndex')
        if oi is not None: old_owner[id(new_recs[-1])] = int(oi) + 1
        if i in insert_after:
            idx = int(field(b, 'IndexInSheet'))
            for k, (name, text) in enumerate(NEW, 1):
                nb = set_field(set_field(set_field(set_field(b, 'Text', text), 'Name', name), 'UniqueID', uid()), 'IndexInSheet', str(idx + k))
                new_recs.append([h, nb])
                old_owner[id(new_recs[-1])] = insert_after[i]
    for r in new_recs:
        if id(r) in old_owner:
            r[1] = set_field(r[1], 'OwnerIndex', str(old_to_new[old_owner[id(r)]] - 1))
    new_recs[0][1] = set_field(head, 'Weight', str(len(new_recs) - 1))
    after = parents(new_recs)
    changed = [u for u in before if before[u] != after.get(u)]
    assert not changed, changed[:5]
    assert len(new_recs) == len(recs) + 2 * len(NEW)
    out = join(new_recs)
    write_stream(path, 'FileHeader', out)
    assert read_stream(path, 'FileHeader') == out
    print(f'JP3/JP4: DNS=Yes and SPEC inserted, {len(new_recs) - 1} records, parents intact')


if __name__ == '__main__':
    main(sys.argv[2])
