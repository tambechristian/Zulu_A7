"""Fab B Rev 2 sync (2026-11-20), sheet 4: U10 (93LC46B EEPROM) becomes the MSOP-8 93LC46BT-I/MS, as on Zulu_A7_no_pmod Rev 2.

    python tools/u10_msop_sch.py            dry run
    python tools/u10_msop_sch.py apply      writes Imported zulu_a7.PrjPcb/zulu_a7_4.SchDoc

Port of Zulu_A7_no_pmod/Rev_2/tools/u10_msop_sch.py (3b1817d).  Same die and pinout (1 CS, 2 CLK, 3 DI, 4 DO, 5 VSS,
6-7 NC, 8 VCC; DS20001749K p.2).  Changed on U10 only, found by UniqueID: LibReference / DesignItemId, description,
Comment, EAGLE DeviceName, MANF# and the current PCB footprint model (MSOP-8_3X3_P0.65, the no-PMOD PcbLib footprint).
One deliberate difference from the no-PMOD text: the description dates the SOIC -> MSOP change to 2026-11-20, the day
it happened on this board (the no-PMOD sheet says 2026-11-14, its own date).  Pins, nets and the record count are
untouched; the SI model is added separately by tools/si_models_sch.py.  Needs backups/zulu_a7_4.SchDoc.pre-sync.
"""
import sys

from sync_sch_common import field, load, require_backup, save, set_field, sheet

NEW = 'MSOP-8_3X3_P0.65'
OLD_DESC_HEAD = 'Microchip 93LC46BT-I/SN, '
NEW_DESC_HEAD = 'Microchip 93LC46BT-I/MS (MSOP-8; was the SOIC-8 -I/SN until 2026-11-20), '
EDITS = {   # UniqueID: {field: (expected old, new)}
    'TWUCRGHY': {'LibReference': ('EEPROM-93LC46B-I/SN', 'EEPROM-93LC46B-I/MS'),
                 'DesignItemId': ('EEPROM-93LC46B-I/SN', 'EEPROM-93LC46B-I/MS')},
    'MBVCZONN': {'Text': ('-I/SN', '-I/MS')},                       # DeviceName
    'JQTHWDIV': {'Text': ('93LC46BT-I/SN', '93LC46BT-I/MS')},       # MANF#
    'KQWSBCOU': {'Text': ('93LC46BT-I/SN', '93LC46BT-I/MS')},       # Comment
    'IWBNDWRW': {'ModelName': ('SPI-8_SOIC_150', NEW), 'ModelDatafileEntity0': ('SPI-8_SOIC_150', NEW)},
}


def main():
    apply = 'apply' in sys.argv[1:]
    path = sheet(4)
    R = load(path)
    uid = {}
    for i, (h, b) in enumerate(R):
        uid.setdefault(field(b, 'UniqueID'), []).append(i)
    edits = {u: dict(fs) for u, fs in EDITS.items()}
    d = field(R[uid['TWUCRGHY'][0]][1], 'ComponentDescription')
    assert d.startswith(OLD_DESC_HEAD), d
    edits['TWUCRGHY']['ComponentDescription'] = (d, NEW_DESC_HEAD + d[len(OLD_DESC_HEAD):])
    for u, fs in edits.items():
        assert len(uid.get(u, [])) == 1, u
        i = uid[u][0]
        for k, (before, after) in fs.items():
            old = field(R[i][1], k)
            assert old == before, (u, k, old)
            R[i][1] = set_field(R[i][1], k, after)
            print('%s %-21s %r\n      -> %r' % (u, k, old[:90], after[:90]))
    if not apply:
        print('dry run (add "apply" to write)')
        return
    require_backup(path)
    print('written zulu_a7_4.SchDoc md5 %s, %d records (unchanged)' % (save(path, R), len(R)))


if __name__ == '__main__':
    main()
