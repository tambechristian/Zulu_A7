"""Zulu_a7_no_pmod: reword the JP3/JP4 notes and descriptions on sheet 4, which still talked about the Pmod (Rev 2, 2026-11-12)."""
import os
import sys

sys.path.insert(0, r'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium/tools')
from fix_text_orientation import field, join, read_stream, set_field, split, write_stream  # noqa: E402

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Imported zulu_a7.PrjPcb', 'zulu_a7_4.SchDoc')
OLD = ': a 1x3 body clears the Pmod shroud beside it by 0.09 mm, inside anyone\'s assembly tolerance.'
NEW = {'JP4': 'Bare plated holes -- NO HEADER FITTED, nothing to order. Three of the six JTAG holes (TCK, TMS, GND), upright on the west edge; JP4 carries the other three in the south-west corner above the X2 row. For flying leads or a pogo jig. The FT2232 does JTAG over USB on channel B; this is the fallback.',
       'JP3': 'Bare plated holes -- NO HEADER FITTED, nothing to order. Three of the six JTAG holes (TDI, TDO, VCC3V3), in the south-west corner above the X2 row; JP3 carries the other three upright on the west edge. For flying leads or a pogo jig. The FT2232 does JTAG over USB on channel B; this is the fallback.'}
R = split(read_stream(P, 'FileHeader'))
n = d = 0
for rec in R:
    b = rec[1]
    t = field(b, 'Text')
    if t and t.startswith('Bare plated holes') and 'far side of the Pmod' in t:
        for k, v in NEW.items():
            if ('; %s carries the other three' % k) in t:
                rec[1] = set_field(b, 'Text', v)
                n += 1
                break
    c = field(b, 'ComponentDescription')
    if c and OLD in c:
        rec[1] = set_field(rec[1], 'ComponentDescription', c.replace(OLD, '.'))
        d += 1
assert (n, d) == (2, 2), (n, d)
out = join(R)
write_stream(P, 'FileHeader', out)
assert read_stream(P, 'FileHeader') == out
print('notes', n, 'descriptions', d)
