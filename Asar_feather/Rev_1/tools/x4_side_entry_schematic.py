"""X4 (LiPo JST) top-entry -> side-entry on sheet 1 (2026-11-16, user: "Yes, convert").

    python tools/x4_side_entry_schematic.py            # dry run: prints what would change
    python tools/x4_side_entry_schematic.py --apply    # backs the sheet up to backups/, then writes it

Changes only X4's own records on asar_a7_1.SchDoc: the part's library reference and description, the MANF# / SPEC /
NOTE parameters and the footprint model (JST-B2B-PH-SM4-TB -> JST-S2B-PH-SM4-TB). Pins, wiring, designator, comment
and every UniqueID stay as they are, so the netlist cannot change; record count is unchanged (the header Weight stays
valid). Every old value is asserted before anything is written. Close the sheet in Altium first.
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import schdoc  # noqa: E402

ROOT = os.path.dirname(HERE)
SHEET = os.path.join(ROOT, 'Asar_feather.PrjPcb', 'asar_a7_1.SchDoc')
BACKUP = os.path.join(ROOT, 'backups', 'asar_a7_1_before_x4_s2b.SchDoc')

OLD_FP, NEW_FP = 'JST-B2B-PH-SM4-TB', 'JST-S2B-PH-SM4-TB'
PARAMS = {
    'MANF#': ('B2B-PH-SM4-TB(LF)(SN)', 'S2B-PH-SM4-TB(LF)(SN)'),
    'SPEC': ('JST PH 2.0 mm, 2 circuits, top-entry SMT header with fixing tabs, 2 A, 100 V, -25..85 C, mates with PHR-2 '
             'housing; pin 1 = battery +, pin 2 = GND',
             'JST PH 2.0 mm, 2 circuits, side-entry SMT header with fixing tabs, 2 A, 100 V, -25..85 C, mates with PHR-2 '
             'housing; pin 1 = battery +, pin 2 = GND'),
    'NOTE': (None,
             'S2B-PH-SM4-TB(LF)(SN): side entry, 5.5 mm tall, lies flat with the cable leaving the top long edge as on '
             'Adafruit Feathers (replaced the top-entry B2B-PH-SM4-TB on 2026-11-16). There is no polarity standard for '
             'JST-PH LiPo packs: check pin 1 = + against the pack before plugging in (Adafruit packs put + on JST circuit '
             '1, deduced from their board files). Footprint JST-S2B-PH-SM4-TB: JST ePH side-entry land, two 1.0 x 3.5 mm '
             'contact pads and two 1.5 x 3.4 mm fixing pads.'),
}
DESC = ('JST PH 2.0 mm 2-pin top-entry SMT header, LiPo battery input',
        'JST PH 2.0 mm 2-pin side-entry SMT header, LiPo battery input')


def main():
    apply = '--apply' in sys.argv
    recs = schdoc.split(schdoc.read_stream(SHEET))
    parts = [i for i, (h, b) in enumerate(recs) if schdoc.field(b, 'RECORD') == '1'
             and schdoc.field(b, 'LibReference') == OLD_FP]
    assert len(parts) == 1, 'expected one X4 part record with LibReference %s, found %d' % (OLD_FP, len(parts))
    pi = parts[0]
    kids = schdoc.subtree(recs, [pi]) - {pi}
    des = [i for i in kids if schdoc.field(recs[i][1], 'Name') == 'Designator']
    assert len(des) == 1 and schdoc.field(recs[des[0]][1], 'Text') == 'X4', 'the part is not X4'
    changes = []

    def put(i, key, old, new):
        cur = schdoc.field(recs[i][1], key)
        if old is not None:
            assert cur == old, (i, key, cur)
        changes.append((i, key, cur, new))
        recs[i][1] = schdoc.set_field(recs[i][1], key, new)

    put(pi, 'LibReference', OLD_FP, NEW_FP)
    put(pi, 'DesignItemId', OLD_FP, NEW_FP)
    put(pi, 'ComponentDescription', DESC[0], DESC[1])
    for name, (old, new) in PARAMS.items():
        hit = [i for i in kids if schdoc.field(recs[i][1], 'RECORD') == '41' and schdoc.field(recs[i][1], 'Name') == name]
        assert len(hit) == 1, (name, hit)
        if old is None:
            assert schdoc.field(recs[hit[0]][1], 'Text').startswith('B2B-PH-SM4-TB(LF)(SN): 8 mm tall'), name
        put(hit[0], 'Text', old, new)
    models = [i for i in kids if schdoc.field(recs[i][1], 'RECORD') == '45' and schdoc.field(recs[i][1], 'ModelType') == 'PCBLIB']
    assert len(models) == 1, models
    put(models[0], 'ModelName', OLD_FP, NEW_FP)
    put(models[0], 'ModelDatafileEntity0', OLD_FP, NEW_FP)
    for i, key, old, new in changes:
        print('record %d %s: %r -> %r' % (i, key, (old or '')[:70], new[:70]))
    if not apply:
        print('dry run: nothing written (pass --apply)')
        return
    if not os.path.exists(BACKUP):
        shutil.copy2(SHEET, BACKUP)
    data = schdoc.join(recs)
    schdoc.write_stream(SHEET, data)
    again = schdoc.split(schdoc.read_stream(SHEET))
    assert len(again) == len(recs) and all(a[1] == b[1] for a, b in zip(again, recs)), 'read-back differs'
    print('written %s (%d records, backup %s)' % (SHEET, len(again), BACKUP))


if __name__ == '__main__':
    main()
