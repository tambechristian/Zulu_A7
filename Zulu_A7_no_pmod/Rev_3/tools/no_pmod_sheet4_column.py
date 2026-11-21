"""Zulu_a7_no_pmod Rev 2: reword the JP3/JP4 notes on sheet 4 after JP4 joined JP3 on the west edge (2026-11-12).
All six JTAG holes now form one 2.54 mm column centred on that edge: GND, TMS, TCK (JP3), then VCC3V3, TDO, TDI (JP4)."""
import os
import sys

sys.path.insert(0, r'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium/tools')
from fix_text_orientation import field, join, read_stream, set_field, split, write_stream  # noqa: E402

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Imported zulu_a7.PrjPcb', 'zulu_a7_4.SchDoc')
HEAD = 'Bare plated holes -- NO HEADER FITTED, nothing to order. '
TAIL = ' For flying leads or a pogo jig. The FT2232 does JTAG over USB on channel B; this is the fallback.'
NEW = {
    '(TCK, TMS, GND)': HEAD + 'Three of the six JTAG holes (TCK, TMS, GND), on the west edge; JP4 carries the other three '
                       'directly below, so all six form one 2.54 mm column centred on that edge.' + TAIL,
    '(TDI, TDO, VCC3V3)': HEAD + 'Three of the six JTAG holes (TDI, TDO, VCC3V3), on the west edge directly below JP3; '
                          'together the six form one 2.54 mm column centred on that edge.' + TAIL,
}
R = split(read_stream(P, 'FileHeader'))
n = 0
for rec in R:
    t = field(rec[1], 'Text')
    if t and t.startswith(HEAD) and 'south-west corner' in t:
        for k, v in NEW.items():
            if k in t:
                rec[1] = set_field(rec[1], 'Text', v)
                n += 1
                break
assert n == 2, n
out = join(R)
write_stream(P, 'FileHeader', out)
assert read_stream(P, 'FileHeader') == out
print('notes', n)
