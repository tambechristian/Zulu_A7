# -*- coding: utf-8 -*-
"""Repair after x2_lipo_corner.py, 2026-09-09: put back 14 catalogue parameters on two X2 gate copies.

The EAGLE importer gave the seven catalogue parameters of every ZULU-CONN gate copy (DeviceName,
LibraryName, DeviceSetName, MANF, MANF#, SPEC, NOTE) an OwnerPartId that is a per-copy serial
number, unrelated to the copy's sub-part. x2_lipo_corner.py deleted every child record whose
OwnerPartId was one of the two dead sub-parts (35, 45), which was right for the pins, polygons and
GateName/SymbolName entries but also took the seven catalogue parameters of the two copies whose
serial happened to be 35 or 45 (copy UniqueID DFRVQUTC, the CHAN22 gate, and IDTIOHHH, the pin-less
body gate). Found by the adversarial review of commit 338ea4e. This script clones the seven records
of a healthy copy (so MANF#/SPEC/NOTE carry the current texts), gives them fresh UniqueIDs and the
target copy's own CurrentPartId, and appends them to each damaged copy; the header Weight is bumped.
Refuses to run when every copy already has the seven.

    python tools/x2_restore_params.py tools "Imported zulu_a7.PrjPcb/zulu_a7_2.SchDoc"
"""
import sys, random, string
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

CATALOGUE = ('DeviceName', 'LibraryName', 'DeviceSetName', 'MANF', 'MANF#', 'SPEC', 'NOTE')


def uid():
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(8))


def owner_list_index(b):
    o = field(b, 'OwnerIndex')
    return int(o) + 1 if o is not None else None


def main(path):
    recs = split(read_stream(path, 'FileHeader'))
    head = recs[0][1]
    assert int(field(head, 'Weight')) == len(recs) - 1
    copies = [i for i, (h, b) in enumerate(recs) if b.startswith(b'|RECORD=1|') and field(b, 'LibReference') == 'ZULU-CONN']
    have = {ci: {} for ci in copies}
    for i, (h, b) in enumerate(recs):
        if b.startswith(b'|RECORD=41|') and owner_list_index(b) in have and field(b, 'Name') in CATALOGUE:
            have[owner_list_index(b)][field(b, 'Name')] = i
    damaged = [ci for ci in copies if set(have[ci]) != set(CATALOGUE)]
    if not damaged:
        raise SystemExit('every X2 copy carries the seven catalogue parameters; nothing done')
    healthy = next(ci for ci in copies if set(have[ci]) == set(CATALOGUE))
    added = 0
    for ci in damaged:
        missing = [n for n in CATALOGUE if n not in have[ci]]
        pid = field(recs[ci][1], 'CurrentPartId')
        for name in missing:
            h, b = recs[have[healthy][name]]
            nb = set_field(set_field(set_field(b, 'OwnerIndex', str(ci - 1)), 'OwnerPartId', pid), 'UniqueID', uid())
            recs.append([h, nb]); added += 1
        print(f'copy {field(recs[ci][1], "UniqueID")} (part {pid}): restored {", ".join(missing)}')
    recs[0][1] = set_field(head, 'Weight', str(len(recs) - 1))
    out = join(recs)
    write_stream(path, 'FileHeader', out)
    assert read_stream(path, 'FileHeader') == out
    # verify
    recs = split(read_stream(path, 'FileHeader'))
    count = {ci: 0 for ci in copies}
    for h, b in recs:
        if b.startswith(b'|RECORD=41|') and owner_list_index(b) in count and field(b, 'Name') in CATALOGUE:
            count[owner_list_index(b)] += 1
    assert all(v == 7 for v in count.values()), count
    print(f'{added} parameter records appended; all {len(copies)} copies carry the seven catalogue parameters')


if __name__ == '__main__':
    main(sys.argv[2])
