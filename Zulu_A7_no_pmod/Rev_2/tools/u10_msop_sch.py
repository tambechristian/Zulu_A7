"""No-PMOD Rev 2 (2026-11-14): U10 (93LC46B EEPROM) becomes the MSOP-8 93LC46BT-I/MS on schematic sheet 4.

    python tools/u10_msop_sch.py <zulu_a7_4.SchDoc>          (close the sheet in Altium first)

The SOIC-8 body sat 0.14 mm under X2's pins 11-20 header housing (audit 2026-11-14) and had no legal Bottom site; on
Top it covered X2's pin labels; the user chose the MSOP-8 (same die and pinout: 1 CS, 2 CLK, 3 DI, 4 DO, 5 VSS,
6-7 NC, 8 VCC; datasheet DS20001749K p.2).  Changed on U10 only, found by UniqueID: LibReference / DesignItemId,
description, Comment, EAGLE DeviceName, MANF# and the current PCB footprint model (MSOP-8_3X3_P0.65, drawn by
tools/NoPmodLibFix.pas).  Pins, nets and the SI model are untouched; the record count is unchanged.
"""
import hashlib
import os
import shutil
import sys

sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1/tools')
from schdoc import field, join, read_stream, set_field, split, write_stream  # noqa: E402

NEW = 'MSOP-8_3X3_P0.65'
EDITS = {   # UniqueID: {field: value}
    'TWUCRGHY': {'LibReference': 'EEPROM-93LC46B-I/MS', 'DesignItemId': 'EEPROM-93LC46B-I/MS'},
    'MBVCZONN': {'Text': '-I/MS'},
    'JQTHWDIV': {'Text': '93LC46BT-I/MS'},
    'KQWSBCOU': {'Text': '93LC46BT-I/MS'},
    'IWBNDWRW': {'ModelName': NEW, 'ModelDatafileEntity0': NEW},
}


def main():
    path = sys.argv[1]
    raw = read_stream(path)
    R = split(raw)
    uid = {field(b, 'UniqueID'): i for i, (h, b) in enumerate(R)}
    edits = dict(EDITS)
    d = field(R[uid['TWUCRGHY']][1], 'ComponentDescription')
    assert d.startswith('Microchip 93LC46BT-I/SN, '), d
    edits['TWUCRGHY']['ComponentDescription'] = 'Microchip 93LC46BT-I/MS (MSOP-8; was the SOIC-8 -I/SN until 2026-11-14), ' + d[len('Microchip 93LC46BT-I/SN, '):]
    for u, fs in edits.items():
        assert u in uid, u
        i = uid[u]
        for k, v in fs.items():
            old = field(R[i][1], k)
            assert old is not None, (u, k)
            R[i][1] = set_field(R[i][1], k, v)
            print('%s %-22s %s -> %s' % (u, k, (old[:50] + '...') if len(old) > 50 else old, v[:60]))
    bak = path + '.pre-u10-msop'
    if not os.path.exists(bak):
        shutil.copy2(path, bak)
    blob = join(R)
    write_stream(path, blob)
    assert read_stream(path) == blob
    print('written; records %d (unchanged); md5 %s' % (len(R), hashlib.md5(open(path, 'rb').read()).hexdigest()[:8]))


if __name__ == '__main__':
    main()
