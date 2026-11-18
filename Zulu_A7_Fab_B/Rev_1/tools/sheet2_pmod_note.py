"""Sheet 2 (zulu_a7_2.SchDoc), 2026-11-18: the Pmod JA note gave a JA pin-out from an earlier pin plan (JA1-JA4 =
A14 A15 B15 A16 in bank 16, JA7 = C15, JA8/JA9/JA10 = W19/N2/W7). The FPGA sheet's rows (zulu_a7_5.SchDoc, re-filed
the same day, docs/sheet5_reorganize.md) and vivado/zulu_a7_pins.xdc say JA1 U18, JA2 U19, JA3 W18, JA4 C17, JA7 R19,
JA8 W19, JA9 V19, JA10 U17 (all bank 14 except C17, bank 16). Rewrites only the note's last three lines, checks the new
pin-out against sheet 6's own nets, and proves sheet 2's nets unchanged.

    python tools/sheet2_pmod_note.py <zulu_a7_2.SchDoc>      (edits in place; run from the revision folder)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1/tools')
from schdoc import field, join, read_stream, set_field, split, write_stream  # noqa: E402
from sheet3_u3_layout import net_map, report  # noqa: E402

OLD = ('JA1-JA4 (the top row, the half a Pmod uses for SPI) are all in bank 16: A14 A15 B15 A16. ~1'
       'JA7 is C15, also bank 16.  JA8/JA9/JA10 are W19/N2/W7 -- banks 14/35/34 -- because nothing ~1'
       'else was free.  All five banks are VCCO=3.3V, so this costs timing coherence, not levels.')
NEW = ('JA1-JA4 (the top row, the half a Pmod uses for SPI) are U18 U19 W18 C17: banks 14/14/14/16. ~1'
       'JA7-JA10 are R19 W19 V19 U17, all bank 14.  U19/W18/V19 double as RDWR_B/CSI_B/DOUT_CSO_B, ~1'
       'which master SPI x4 does not use.  Banks 14 and 16 are both VCCO=3.3V.')
PINOUT = {'JA1': 'U18', 'JA2': 'U19', 'JA3': 'W18', 'JA4': 'C17', 'JA7': 'R19', 'JA8': 'W19', 'JA9': 'V19', 'JA10': 'U17'}


def main(path):
    sheet6 = os.path.join(os.path.dirname(path), 'zulu_a7_5.SchDoc')
    nets6 = net_map(split(read_stream(sheet6)))
    for net, ball in PINOUT.items():
        assert nets6.get(net) == frozenset({('U1', ball)}), (net, sorted(nets6.get(net, ())))
    raw = read_stream(path)
    R = split(raw)
    before = net_map(R)
    hit = [i for i, (h, b) in enumerate(R) if field(b, 'RECORD') == '28' and (field(b, 'Text') or '').startswith('Digilent 12-pin Pmod (JA).')]
    assert len(hit) == 1, hit
    t = field(R[hit[0]][1], 'Text')
    assert t.count(OLD) == 1 and t.endswith(OLD), 'note is not the expected text (already applied?)'
    R[hit[0]][1] = set_field(R[hit[0]][1], 'Text', t.replace(OLD, NEW))
    blob = join(R)
    write_stream(path, blob)
    assert read_stream(path) == blob
    print(field(R[hit[0]][1], 'Text').replace('~1', '\n'))
    report(before, net_map(split(read_stream(path))))


if __name__ == '__main__':
    main(sys.argv[1])
