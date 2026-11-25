"""Update Rev_2 schematic X4 to the validated JST S2B-PH-SM4-TB.

Close zulu_a7_1.SchDoc in Altium before running this script.
"""
import hashlib
import os
import shutil
import sys

sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1/tools')
from schdoc import field, join, read_stream, set_field, split, write_stream  # noqa: E402

NEW = 'JST-S2B-PH-SM4-TB'
EDITS = {
    'RUXKJBMH': {
        'LibReference': NEW,
        'DesignItemId': NEW,
        'ComponentDescription': 'JST PH 2.0 mm 2-pin side-entry SMT header, LiPo battery input',
    },
    'ZHBBDJHM': {'Text': 'S2B-SM4-TB'},
    'TJYOKYDX': {'Text': 'S2B-PH-SM4-TB(LF)(SN)'},
    'YUTGJJUU': {
        'Text': 'JST PH 2.0 mm, 2 circuits, side-entry SMT header, 2 A, 100 V, -25..85 C, mates with PHR-2; '
                'pin 1 = battery +, pin 2 = GND',
    },
    'PVBJVFNU': {
        'Text': 'S2B-PH-SM4-TB(LF)(SN), top-side SMT, opening facing the south edge on the tapered PCB tab. '
                'The tab extends 3.70 mm beyond the original Feather outline. There is no universal JST-PH LiPo '
                'polarity standard: verify pack positive goes to pin 1 before plugging in.',
    },
    'QUWQMOUZ': {'ModelName': NEW, 'ModelDatafileEntity0': NEW},
}


def main():
    path = sys.argv[1]
    raw = read_stream(path)
    records = split(raw)
    uid = {field(body, 'UniqueID'): i for i, (_, body) in enumerate(records)}
    for unique_id, fields in EDITS.items():
        assert unique_id in uid, unique_id
        i = uid[unique_id]
        for key, value in fields.items():
            old = field(records[i][1], key)
            assert old is not None, (unique_id, key)
            records[i][1] = set_field(records[i][1], key, value)
            print('%s %-22s %s -> %s' % (
                unique_id,
                key,
                (old[:50] + '...') if len(old) > 50 else old,
                value[:60],
            ))
    backup = path + '.pre-x4-smd-tab'
    if not os.path.exists(backup):
        shutil.copy2(path, backup)
    blob = join(records)
    write_stream(path, blob)
    assert read_stream(path) == blob
    print('written; records %d (unchanged); md5 %s' % (
        len(records),
        hashlib.md5(open(path, 'rb').read()).hexdigest()[:8],
    ))


if __name__ == '__main__':
    main()
