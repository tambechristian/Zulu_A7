"""Fab B Rev 2 sync (2026-11-20): bring the schematic notes in line with the FT2232HQ / S2B-PH-SM4-TB / LTC3556 board.

    python tools/stale_notes_sch.py          dry run (prints every change)
    python tools/stale_notes_sch.py apply    writes sheets 0, 2 and 4 (sheet 1 is checked, already right)

Port of Zulu_A7_no_pmod/Rev_2/tools/stale_notes_sch.py (e6d23c6); run it AFTER tools/x4_smd_tab_sch.py and
tools/u2_ft2232hq.py.  Only the Text field of note / parameter / label records changes; record counts, every other
field and the netlist are untouched (checked).  Each text was checked against this board before reuse:

- sheet 0  POZQZCRY  block-diagram label FT2232HL -> FT2232HQ.
- sheet 1  PVBJVFNU  X4 NOTE: x4_smd_tab_sch.py already wrote the final text; this only verifies it.
- sheet 2  RQLMHDNL  X2 text frame.  Same text as the no-PMOD sheet: it describes only X2 (pins, nets, landings at
           x 34.29..26.67, the four 1x10 strips), all of which are identical on this board (X2 pins at x 1.27..59.69,
           the Pmod J1 and JTAG JP3/JP4 lie further east and are not mentioned).  The old text still named pins 9/10
           and 29/30 as the landing neighbours (pre-Rev-2), the top-entry B2B header, the bq24232 4.4 V rail and
           "THE PCB FOOTPRINT MUST BE REDRAWN".  Pin -> net map checked against this project's netlist.
- sheet 2  41 X2 NOTE parameters: "pin 22 VU sources the 4.4 V rail." -> "pin 22 VU is the LTC3556 PowerPath output
           (VOUT)." (VU is the LTC3556 U8 output net on this board too.)
- sheet 4  QERNKKPK  OriginDescription FT2232HL, JTAG, CLOCK -> FT2232HQ, JTAG, CLOCK.
- sheet 4  VTPSFZDQ  Q1 Comment 12MHz 10ppm (FPGA + FT2232HL) -> (FPGA + FT2232HQ).

The JP3/JP4 notes of the no-PMOD sheet 4 (west-edge JTAG column) are NOT ported: this board keeps its JTAG holes at
the east end.  Every written text is scanned for words that would only fit the no-PMOD board (FORBIDDEN).
Needs backups/zulu_a7_N.SchDoc.pre-sync for every sheet it writes.
"""
import re
import sys

from sync_sch_common import field, load, require_backup, save, set_field, sheet, strip_field

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

# sheet: [(UniqueID, expected old Text (None = any), new Text)]
BY_UID = {
    0: [('POZQZCRY', 'FT2232HL', 'FT2232HQ')],
    1: [('PVBJVFNU', X4_NOTE, X4_NOTE)],
    2: [('RQLMHDNL', None, X2_FRAME)],
    4: [('QERNKKPK', 'FT2232HL, JTAG, CLOCK', 'FT2232HQ, JTAG, CLOCK'),
        ('VTPSFZDQ', '12MHz 10ppm (FPGA + FT2232HL)', '12MHz 10ppm (FPGA + FT2232HQ)')],
}
X2_NOTE_OLD = 'pin 22 VU sources the 4.4 V rail.'
X2_NOTE_NEW = 'pin 22 VU is the LTC3556 PowerPath output (VOUT).'
X2_NOTE_COUNT = 41
FORBIDDEN = re.compile(r'no[-_ ]?pmod|without (?:the )?pmod|pmod (?:was )?removed|west[- ]edge|column|60\.96|'
                       r'2\.4 ?x ?1|4\.4 ?V|bq24232|B2B-PH|FT2232HL\b(?!-)', re.I)
# allowed on purpose: texts that compare the QFN with the FT2232HL, and the DQ resistors' pointer to the SI study,
# which lives in the no-PMOD project (a path, not a description of this board)
ALLOWED = ('pin numbering as FT2232HL', 'match FT2232HL', 'Zulu_A7_no_pmod/Rev_2/docs/dq_series_resistors.md')


def scan(text):
    """Forbidden phrases found in text (empty list = clean)."""
    t = text
    for ok in ALLOWED:
        t = t.replace(ok, '')
    return FORBIDDEN.findall(t)


def edit_sheet(n, apply):
    path = sheet(n)
    old = load(path)
    new = [list(r) for r in old]
    uid = {}
    for i, (h, b) in enumerate(old):
        uid.setdefault(field(b, 'UniqueID'), []).append(i)
    changed = []
    for u, before, after in BY_UID.get(n, []):
        assert len(uid.get(u, [])) == 1, (n, u)
        i = uid[u][0]
        t = field(old[i][1], 'Text')
        assert t is not None, (n, u)
        if before is not None:
            assert t == before, (n, u, t)
        if t == after:
            print('S%d %s: already %r' % (n, u, t[:90]))
            continue
        new[i][1] = set_field(old[i][1], 'Text', after)
        changed.append((i, u, t, after))
    if n == 2:
        hits = 0
        for i, (h, b) in enumerate(old):
            t = field(b, 'Text') or ''
            if field(b, 'RECORD') == '41' and field(b, 'Name') == 'NOTE' and X2_NOTE_OLD in t:
                assert t.count(X2_NOTE_OLD) == 1
                new[i][1] = set_field(b, 'Text', t.replace(X2_NOTE_OLD, X2_NOTE_NEW))
                changed.append((i, field(b, 'UniqueID'), X2_NOTE_OLD, X2_NOTE_NEW))
                hits += 1
        assert hits == X2_NOTE_COUNT, hits
    for i, u, t, a in changed:
        assert strip_field(old[i][1], 'Text') == strip_field(new[i][1], 'Text'), (n, u)   # only Text differs
        bad = scan(field(new[i][1], 'Text'))
        assert not bad, (n, u, bad)
    for i, u, t, a in changed[:6]:
        print('S%d %s (record %d): %r\n      -> %r' % (n, u, i, t[:90], a[:90]))
    if len(changed) > 6:
        print('S%d ... %d more records' % (n, len(changed) - 6))
    if apply and changed:
        require_backup(path)
        m = save(path, new)
        chk = load(path)
        assert len(chk) == len(old)
        diff = [k for k in range(len(old)) if old[k][1] != chk[k][1]]
        assert sorted(diff) == sorted(c[0] for c in changed), (n, len(diff))
        print('S%d written: %d records changed of %d, md5 %s' % (n, len(diff), len(old), m))


def main():
    apply = 'apply' in sys.argv[1:]
    for n in (0, 1, 2, 4):
        edit_sheet(n, apply)
    if not apply:
        print('dry run (add "apply" to write)')


if __name__ == '__main__':
    main()
