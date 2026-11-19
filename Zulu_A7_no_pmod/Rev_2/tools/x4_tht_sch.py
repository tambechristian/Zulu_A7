"""No-PMOD Rev 2 (2026-11-14): X4 becomes the through-hole JST PH B2B-PH-K-S on schematic sheet 1.

    python tools/x4_tht_sch.py <zulu_a7_1.SchDoc>          (close the sheet in Altium first)

The top-entry SMD B2B-PH-SM4-TB's housing sat 0.74 mm over U2's south pins (audit 2026-11-14); the user chose the
through-hole vertical twin.  Changed on X4 only, found by UniqueID: LibReference / DesignItemId, description, the
EAGLE DeviceName, MANF#, SPEC, NOTE and the current PCB footprint model (JST-B2B-PH-K-S, drawn by
tools/NoPmodX4Footprint.pas).  The pins (1 BAT+, 2 GND) and every net are untouched; the record count is unchanged.
"""
import hashlib
import os
import shutil
import sys

sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1/tools')
from schdoc import field, join, read_stream, set_field, split, write_stream  # noqa: E402

NEW = 'JST-B2B-PH-K-S'
EDITS = {   # UniqueID: {field: value}
    'RUXKJBMH': {'LibReference': NEW, 'DesignItemId': NEW,
                 'ComponentDescription': 'JST PH 2.0 mm 2-pin vertical through-hole header, LiPo battery input'},
    'ZHBBDJHM': {'Text': 'K-S'},
    'TJYOKYDX': {'Text': 'B2B-PH-K-S(LF)(SN)'},
    'YUMYLJBK': {'Text': 'JST PH 2.0 mm, 2 circuits, vertical through-hole header, 2 A, 100 V, -25..85 C, mates with '
                         'PHR-2 housing; pin 1 = battery +, pin 2 = GND'},
    'PVBJVFNU': {'Text': 'B2B-PH-K-S(LF)(SN), through-hole, 6.0 mm tall, wire leaves upward. Replaced the top-entry SMD '
                         'B2B-PH-SM4-TB on 2026-11-14: its housing sat 0.74 mm over U2 pins 17-29. There is no polarity '
                         'standard for JST-PH LiPo packs: check pin 1 = + against the pack before plugging in. Trim the '
                         'pin tails flush on the bottom (the board sits on a carrier through X2).'},
    'QUWQMOUZ': {'ModelName': NEW, 'ModelDatafileEntity0': NEW},
}


def main():
    path = sys.argv[1]
    raw = read_stream(path)
    R = split(raw)
    uid = {field(b, 'UniqueID'): i for i, (h, b) in enumerate(R)}
    spec = [u for u in uid if u and u.startswith('YU') and 'SPEC' == field(R[uid[u]][1], 'Name') and
            'B2B' not in (field(R[uid[u]][1], 'Text') or '') and 'top-entry SMT header with fixing tabs' in
            (field(R[uid[u]][1], 'Text') or '')]
    assert len(spec) == 1, spec
    edits = dict(EDITS)
    edits[spec[0]] = edits.pop('YUMYLJBK')
    for u, fs in edits.items():
        assert u in uid, u
        i = uid[u]
        for k, v in fs.items():
            old = field(R[i][1], k)
            assert old is not None, (u, k)
            R[i][1] = set_field(R[i][1], k, v)
            print('%s %-22s %s -> %s' % (u, k, (old[:50] + '...') if len(old) > 50 else old, v[:60]))
    bak = path + '.pre-x4-tht'
    if not os.path.exists(bak):
        shutil.copy2(path, bak)
    blob = join(R)
    write_stream(path, blob)
    assert read_stream(path) == blob
    print('written; records %d (unchanged); md5 %s' % (len(R), hashlib.md5(open(path, 'rb').read()).hexdigest()[:8]))


if __name__ == '__main__':
    main()
