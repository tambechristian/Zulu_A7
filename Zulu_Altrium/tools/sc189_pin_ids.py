# -*- coding: utf-8 -*-
"""Sheet 1, 2026-09-09: give the SC189 pins their own UniqueIDs.

tools/sc189_power_section.py (2026-09-06) built U5, U6 and U7 by cloning one pin record, so all
fifteen pins of the three regulators carry the single UniqueID PDYAEPSY. Every other component on
the sheet has distinct pin identifiers, and nothing anywhere in the project refers to PDYAEPSY, so
the repair is simply to hand each of the fifteen a fresh identifier drawn clear of the 953 already
in use on the sheet.

It never troubled compiling or netlisting -- pins are matched by designator there -- but pin
UniqueIDs are what Altium follows when it synchronises a schematic with a PCB and when it
cross-probes, which is why this is worth clearing before the board work starts.

Nothing else in the record is touched: no record is added, removed or reordered, so the header
count, every OwnerIndex and the exported netlist all stay exactly as they were. verify() proves
that by comparing each rewritten record with the original byte for byte with the UniqueID masked
out. Refuses to run twice.

    python tools/sc189_pin_ids.py tools "Imported zulu_a7.PrjPcb/zulu_a7_1.SchDoc"
"""
import sys, re, random, string, collections
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

PARTS = ('U5', 'U6', 'U7')
UID = re.compile(rb'\|UniqueID=[^|\x00]*')


def owner_list_index(b):
    o = field(b, 'OwnerIndex')
    return int(o) + 1 if o is not None else None


def main(path):
    recs = split(read_stream(path, 'FileHeader'))
    before = [bytes(b) for h, b in recs]
    desig = {owner_list_index(b): field(b, 'Text') for h, b in recs if b.startswith(b'|RECORD=34|')}
    comps = {i for i, (h, b) in enumerate(recs) if b.startswith(b'|RECORD=1|') and desig.get(i) in PARTS}
    assert len(comps) == len(PARTS), sorted(desig.get(i) for i in comps)
    pins = [i for i, (h, b) in enumerate(recs) if b.startswith(b'|RECORD=2|') and owner_list_index(b) in comps]
    assert len(pins) == 15, len(pins)
    used = {field(b, 'UniqueID') for h, b in recs if field(b, 'UniqueID')}
    shared = collections.Counter(field(recs[i][1], 'UniqueID') for i in pins)
    if all(n == 1 for n in shared.values()):
        raise SystemExit('the SC189 pins already have distinct UniqueIDs; nothing done')
    print(f'{len(pins)} pins across {", ".join(PARTS)} share {len(shared)} identifier(s): ' +
          ', '.join(f'{u} x{n}' for u, n in shared.items()))
    fresh = set()
    while len(fresh) < len(pins):
        u = ''.join(random.choice(string.ascii_uppercase) for _ in range(8))
        if u not in used:
            fresh.add(u); used.add(u)
    for i, u in zip(pins, sorted(fresh)):
        recs[i][1] = set_field(recs[i][1], 'UniqueID', u)
        print(f'  {desig[owner_list_index(recs[i][1])]:3} pin {field(recs[i][1], "Designator"):>2} {field(recs[i][1], "Name"):5} -> {u}')
    blob = join(recs)
    write_stream(path, 'FileHeader', blob)
    assert read_stream(path, 'FileHeader') == blob
    verify(path, before, pins)


def verify(path, before=None, pins=None):
    recs = split(read_stream(path, 'FileHeader'))
    assert int(field(recs[0][1], 'Weight')) == len(recs) - 1, 'header count'
    assert all(b.endswith(b'\x00') for h, b in recs), 'a record lost its terminator'
    uids = [field(b, 'UniqueID') for h, b in recs if field(b, 'UniqueID')]
    dup = [u for u, n in collections.Counter(uids).items() if n > 1]
    assert not dup, f'duplicate UniqueIDs remain: {dup}'
    if before is not None:
        assert len(before) == len(recs), 'record count changed'
        changed = [i for i in range(len(recs)) if before[i] != recs[i][1]]
        assert changed == sorted(pins), (changed, pins)
        for i in changed:                                    # identical once the identifier is masked
            assert UID.sub(b'|UniqueID=', before[i]) == UID.sub(b'|UniqueID=', recs[i][1]), i
    print(f'verify: {len(recs)} records, {len(uids)} identifiers all distinct, '
          f'{len(pins) if pins else 0} records changed and only in their UniqueID')


if __name__ == '__main__':
    main(sys.argv[2])
