"""No-PMOD Rev 2 (2026-11-19): bring the schematic notes in line with the 2026-11-19 board.

    python tools/stale_notes_sch.py          dry run (prints every change)
    python tools/stale_notes_sch.py apply    writes the sheets (backups in Rev_2/backups first)

On 2026-11-19 U2 became the FT2232HQ (QFN-64) and X4 the side-entry S2B-PH-SM4-TB between X2 pins 30 and 31 (no PCB
tab). Several notes still named the FT2232HL, the old top-entry B2B header, the abandoned edge tab, the pre-Rev-2
landing positions and the bq24232's 4.4 V rail. Only the Text field of note/parameter/label records changes. The
record count, every other field and the netlist are untouched. Statements that compare the QFN with the FT2232HL
("pins 1-64 match FT2232HL") are correct and stay.
"""
import hashlib
import os
import shutil
import sys

sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1/tools')
from schdoc import field, join, read_stream, set_field, split, write_stream  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRJ = os.path.join(HERE, 'Imported zulu_a7.PrjPcb')
BAK = os.path.join(HERE, 'backups')

X2_FRAME = (
    'X2: 40 pins on a 2.54 mm grid, rows 22.86 mm (0.900 in) apart, numbered 1-40 straight ~1'
    'through from the right and skipping both landings.  The two rows are mirror images. ~1'
    'TOP ROW, x 59.69 down to 1.27: GND (pin 1), CHAN-CLK (2), CHAN0..CHAN7 (3-10), ~1'
    '  then CHAN8..CHAN13 (11-16), GND, +3.3V, +1.8V, +1.0V (17-20). ~1'
    'BOTTOM ROW, x 59.69 down to 1.27: GND, VU, RST# (pins 21-23), CHAN14..CHAN20 (24-30), ~1'
    '  then CHAN21..CHAN28 (31-38), ANALOG-IO0, ANALOG-IO1 (39, 40). ~1'
    'FOUR positions in each row -- x 34.29, 31.75, 29.21, 26.67, between pins 10 and 11 above ~1'
    '  and between pins 30 and 31 below -- are RESERVED, not spare: the edge-mounted ~1'
    '  micro-USB X1 lands on the top row, the side-entry LiPo header X4 ~1'
    '  (JST S2B-PH-SM4-TB, top-side SMT) lands on the bottom row opposite it. ~1'
    '  Each landing is 12.70 mm between the neighbouring pin centres, 11.176 mm clear. ~1'
    'THREE grounds: pins 1, 17, 21.  Pin 18 is the only +3.3V pin.  Pin 22 VU is the ~1'
    '  LTC3556 PowerPath output (VOUT): external power is USB or the LiPo on X4. ~1'
    '  Rev 2: four identical 1x10 strips (pins 1-10, 11-20, 21-30, 31-40).')

X4_NOTE = ('S2B-PH-SM4-TB(LF)(SN), top-side SMT side-entry header between X2 pins 30 and 31; the opening faces the '
           'south board edge, so the cable plugs in parallel to the board. There is no universal JST-PH LiPo '
           'polarity standard: verify pack positive goes to pin 1 before plugging in.')

# sheet: [(UniqueID, expected old Text, new Text)]
BY_UID = {
    0: [('POZQZCRY', 'FT2232HL', 'FT2232HQ')],
    1: [('PVBJVFNU', None, X4_NOTE)],
    2: [('RQLMHDNL', None, X2_FRAME)],
    4: [('QERNKKPK', 'FT2232HL, JTAG, CLOCK', 'FT2232HQ, JTAG, CLOCK'),
        ('VTPSFZDQ', '12MHz 10ppm (FPGA + FT2232HL)', '12MHz 10ppm (FPGA + FT2232HQ)')],
}
# sheet 2: X2's per-gate NOTE parameters (41 copies) still carry the bq24232's 4.4 V rail
X2_NOTE_OLD = 'pin 22 VU sources the 4.4 V rail.'
X2_NOTE_NEW = 'pin 22 VU is the LTC3556 PowerPath output (VOUT).'
X2_NOTE_COUNT = 41


def edit_sheet(n, apply):
    path = os.path.join(PRJ, 'zulu_a7_%d.SchDoc' % n)
    raw = read_stream(path)
    old = split(raw)
    new = [list(r) for r in old]
    uid = {field(b, 'UniqueID'): i for i, (h, b) in enumerate(old)}
    changed = []
    for u, before, after in BY_UID.get(n, []):
        i = uid[u]
        t = field(old[i][1], 'Text')
        assert t is not None, (n, u)
        if before is not None:
            assert t == before, (n, u, t)
        new[i][1] = set_field(old[i][1], 'Text', after)
        changed.append((i, u, t, after))
    if n == 2:
        hits = 0
        for i, (h, b) in enumerate(old):
            t = field(b, 'Text') or ''
            if field(b, 'RECORD') == '41' and field(b, 'Name') == 'NOTE' and X2_NOTE_OLD in t:
                new[i][1] = set_field(b, 'Text', t.replace(X2_NOTE_OLD, X2_NOTE_NEW))
                changed.append((i, field(b, 'UniqueID'), X2_NOTE_OLD, X2_NOTE_NEW))
                hits += 1
        assert hits == X2_NOTE_COUNT, hits
    # only the Text field may differ
    for i, u, t, a in changed:
        strip = lambda rec: rec.decode('latin-1').replace('Text=' + field(rec, 'Text'), '')
        assert strip(old[i][1]) == strip(new[i][1]), (n, u)
    for i, u, t, a in changed[:6]:
        print('S%d %s: %r\n      -> %r' % (n, u, t[:90], a[:90]))
    if len(changed) > 6:
        print('S%d ... %d more records' % (n, len(changed) - 6))
    if apply:
        os.makedirs(BAK, exist_ok=True)
        bak = os.path.join(BAK, 'zulu_a7_%d.SchDoc.pre-stale-notes' % n)
        if not os.path.exists(bak):
            shutil.copy2(path, bak)
        blob = join(new)
        write_stream(path, blob)
        assert read_stream(path) == blob
        chk = split(read_stream(path))
        assert len(chk) == len(old)
        diff = [k for k in range(len(old)) if old[k][1] != chk[k][1]]
        assert sorted(diff) == sorted(c[0] for c in changed), (n, len(diff))
        print('S%d written: %d records changed of %d, md5 %s' % (
            n, len(diff), len(old), hashlib.md5(open(path, 'rb').read()).hexdigest()[:8]))


def main():
    apply = 'apply' in sys.argv
    for n in (0, 1, 2, 4):
        edit_sheet(n, apply)


if __name__ == '__main__':
    main()
