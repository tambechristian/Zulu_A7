"""Rev 2 (2026-11-11): set X2's MANF#, SPEC and NOTE on sheet 2 (zulu_a7_2.SchDoc) for the four 1x10 strips.

    python tools/rev2_x2_sch.py          dry run (prints the record diff count)
    python tools/rev2_x2_sch.py apply    writes the sheet (backup in Rev_2/backups first)

Only the Text of three parameter records per X2 gate changes; the netlist is untouched.
"""
import sys, shutil, os
sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1/tools')
from schdoc import read_stream, split, field, set_field, join, write_stream, owner
P = r'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/Imported zulu_a7.PrjPcb/zulu_a7_2.SchDoc'
BK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backups', 'zulu_a7_2.SchDoc.pre-rev2')  # Rev_2/backups is gitignored
NEW = {
 'MANF#': '4x PRPC010SAAN-RC',
 'SPEC': 'four 0.1 in male breakaway header strips, 0.64 mm square gold-flash pins, 2.54 mm pitch, through-hole, mounted from the underside, one part number, four per board: PRPC010SAAN-RC 1x10 for pins 1-10, 11-20, 21-30 and 31-40 (Rev 2, 2026-11-11: both landings moved one pin west so each row splits 10 + 10)',
 'NOTE': 'Pin field ZULU-DIP37 (Rev 2, 2026-11-11): 40 pins of 1.016 mm on 2.54 mm pitch, two rows 22.86 mm (0.900 in) apart, numbered 1-40 straight through and skipping both landings. The rows are mirror images: top row pins 1-10 (x 59.69..36.83) = GND, CHAN-CLK, CHAN0..CHAN7, FOUR positions for the micro-USB X1 (34.29..26.67, X1 centred on x 30.48), pins 11-20 (24.13..1.27) = CHAN8..CHAN13, GND, +3.3V, +1.8V, +1.0V; bottom row pins 21-30 (59.69..36.83) = GND, VU, RST#, CHAN14..CHAN20, FOUR positions for the LiPo header X4 at the SAME four x values (X4 centred on x 30.48, top side, opposite X1), pins 31-40 (24.13..1.27) = CHAN21..CHAN28, ANALOG-IO0, ANALOG-IO1. Each landing is 12.70 mm between the neighbouring pin centres (36.83 and 24.13). Rev 2 change: pins 10 (CHAN7) and 30 (CHAN20) moved from x 26.67 to 36.83 and X1/X4 moved 2.54 mm west, so the strips are four identical 1x10. Pin numbers and nets are unchanged. Three grounds (1, 17, 21); 3.3 V for the header is pin 18 alone; pin 22 VU sources the 4.4 V rail. Sullins PRPC strips fit the holes (0.64 mm square pins, Sullins recommends 1.02 mm). Alternate: any 2.54 mm 1x40 breakaway strip cut to 10 + 10 twice.'}
if not os.path.exists(BK):
    shutil.copy2(P, BK)
old = split(read_stream(BK)); assert read_stream(BK) == read_stream(P)
gates = {owner(b) for (h, b) in old if field(b, 'RECORD') == '34' and field(b, 'Text') == 'X2'}
new = [list(r) for r in old]; n = 0
for i, (h, b) in enumerate(old):
    if owner(b) in gates and field(b, 'RECORD') == '41' and field(b, 'Name') in NEW:
        new[i][1] = set_field(b, 'Text', NEW[field(b, 'Name')]); n += 1
if 'apply' in sys.argv:
    write_stream(P, join(new))
chk = split(read_stream(P)) if 'apply' in sys.argv else new
diff = [k for k in range(len(old)) if old[k] != chk[k]]
print('gates', len(gates), 'records set', n, 'changed', len(diff), 'count', len(old), len(chk), 'Weight', field(old[0][1], 'Weight'), field(chk[0][1], 'Weight'))
for k in diff:
    assert old[k][1].decode('latin-1').replace('Text=' + field(old[k][1], 'Text'), '') == chk[k][1].decode('latin-1').replace('Text=' + field(chk[k][1], 'Text'), '')
