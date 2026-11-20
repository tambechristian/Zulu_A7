"""Fab B Rev 2 sync (2026-11-20), sheet 1: X4 becomes the side-entry SMD JST S2B-PH-SM4-TB, as on Zulu_A7_no_pmod Rev 2.

    python tools/x4_smd_tab_sch.py            dry run
    python tools/x4_smd_tab_sch.py apply      writes Imported zulu_a7.PrjPcb/zulu_a7_1.SchDoc

Port of Zulu_A7_no_pmod/Rev_2/tools/x4_smd_tab_sch.py (3b1817d) with the X4 NOTE written straight in its final
form, the text Zulu_A7_no_pmod/Rev_2/tools/stale_notes_sch.py gave it (e6d23c6): this board's sheet 1 was identical
to the no-PMOD one at 31df8a8, and both boards place X4 between X2 pins 30 and 31 with the opening on the south edge,
so the no-PMOD note is true here.  The SOURCE's intermediate note ("tapered PCB tab ... 3.70 mm beyond the Feather
outline") described an abandoned tab and is never written.

Changed on X4 only, found by UniqueID: LibReference / DesignItemId, ComponentDescription, the EAGLE DeviceName, MANF#,
SPEC, NOTE and the current PCB footprint model (JST-S2B-PH-SM4-TB, the no-PMOD PcbLib footprint).  Pins (1 BAT+, 2 GND),
nets and the record count are untouched.  After the write the FileHeader stream must equal the no-PMOD HEAD sheet 1
byte for byte (checked; reported, not required, so the script stays usable if that sheet moves on).
Needs backups/zulu_a7_1.SchDoc.pre-sync.
"""
import sys

from sync_sch_common import field, load, read_stream, require_backup, save, set_field, sheet

NEW = 'JST-S2B-PH-SM4-TB'
X4_NOTE = ('S2B-PH-SM4-TB(LF)(SN), top-side SMT side-entry header between X2 pins 30 and 31; the opening faces the '
           'south board edge, so the cable plugs in parallel to the board. There is no universal JST-PH LiPo '
           'polarity standard: verify pack positive goes to pin 1 before plugging in.')
EDITS = {   # UniqueID: {field: (expected old value, new value)}
    'RUXKJBMH': {'LibReference': ('JST-B2B-PH-SM4-TB', NEW),
                 'DesignItemId': ('JST-B2B-PH-SM4-TB', NEW),
                 'ComponentDescription': ('JST PH 2.0 mm 2-pin top-entry SMT header, LiPo battery input',
                                          'JST PH 2.0 mm 2-pin side-entry SMT header, LiPo battery input')},
    'ZHBBDJHM': {'Text': ('SM4-TB', 'S2B-SM4-TB')},                                  # DeviceName
    'TJYOKYDX': {'Text': ('B2B-PH-SM4-TB(LF)(SN)', 'S2B-PH-SM4-TB(LF)(SN)')},        # MANF#
    'YUTGJJUU': {'Text': (None, 'JST PH 2.0 mm, 2 circuits, side-entry SMT header, 2 A, 100 V, -25..85 C, mates '
                                'with PHR-2; pin 1 = battery +, pin 2 = GND')},       # SPEC
    'PVBJVFNU': {'Text': (None, X4_NOTE)},                                           # NOTE
    'QUWQMOUZ': {'ModelName': ('JST-B2B-PH-SM4-TB', NEW), 'ModelDatafileEntity0': ('JST-B2B-PH-SM4-TB', NEW)},
}


def main():
    apply = 'apply' in sys.argv[1:]
    path = sheet(1)
    R = load(path)
    uid = {}
    for i, (h, b) in enumerate(R):
        uid.setdefault(field(b, 'UniqueID'), []).append(i)
    changed = []
    for u, fs in EDITS.items():
        assert len(uid.get(u, [])) == 1, u
        i = uid[u][0]
        for k, (before, after) in fs.items():
            old = field(R[i][1], k)
            assert old is not None, (u, k)
            if before is not None:
                assert old == before, (u, k, old)
            R[i][1] = set_field(R[i][1], k, after)
            changed.append(i)
            print('%s %-21s %r\n      -> %r' % (u, k, old[:90], after[:90]))
    print('%d fields in %d records' % (len(changed), len(set(changed))))
    if not apply:
        print('dry run (add "apply" to write)')
        return
    require_backup(path)
    print('written zulu_a7_1.SchDoc md5 %s, %d records (unchanged)' % (save(path, R), len(R)))
    same = read_stream(path) == read_stream(sheet(1, src=True))
    print('FileHeader == no-PMOD sheet 1: %s' % same)


if __name__ == '__main__':
    main()
