"""Reword JP3/JP4's NOTE for the JTAG 2x3 block (2026-11-21, docs/jtag_block.md).

The six JTAG test pads now form one 2x3 block on the Bottom at the FT2232H's east edge; the old NOTE said the other
three pads were "4.2 mm away under the FT2232H" (they were 11 mm apart before the move). Only the two NOTE parameter
texts change; the script refuses unless it finds the old wording, so it cannot run twice.
    python tools/set_jp_block_notes.py      (close asar_a7_4.SchDoc in Altium first)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schdoc import field, join, owner, read_stream, set_field, split, write_stream  # noqa: E402

PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Asar_feather.PrjPcb', 'asar_a7_4.SchDoc')
OLD = '4.2 mm away under the FT2232H'
TAIL = ('Footprint TP-1X03-SMD: three 1.0 mm round pads on 1.27 mm, for a pogo-pin jig or soldered flying leads. The '
        'FT2232 does JTAG over USB on channel B; this is the fallback.')
BLOCK = ('the six form one 2x3 block on 1.27 mm at the FT2232H\'s east edge (north to south: west column GND, TMS, '
         'TCK; east column VCC3V3, TDO, TDI).')
NOTE = {
    'JP3': 'Bottom-side SMD test pads -- NO PART FITTED, nothing to order. Three of the six JTAG pads (TCK, TMS, GND), '
           'the west column; JP4 (TDI, TDO, VCC3V3) is the column beside it: ' + BLOCK + ' ' + TAIL,
    'JP4': 'Bottom-side SMD test pads -- NO PART FITTED, nothing to order. Three of the six JTAG pads (TDI, TDO, '
           'VCC3V3), the east column; JP3 (TCK, TMS, GND) is the column beside it: ' + BLOCK + ' ' + TAIL,
}


def main():
    recs = split(read_stream(PATH))
    refs = {owner(b): field(b, 'Text') for h, b in recs if field(b, 'RECORD') == '34'}
    done = []
    for i, (h, b) in enumerate(recs):
        ref = refs.get(owner(b))
        if ref not in NOTE or field(b, 'RECORD') != '41' or field(b, 'Name') != 'NOTE':
            continue
        old = field(b, 'Text') or ''
        if OLD not in old:
            sys.exit('REFUSED: %s NOTE is not the old wording: %r' % (ref, old[:80]))
        recs[i][1] = set_field(b, 'Text', NOTE[ref])
        done.append(ref)
    if sorted(done) != ['JP3', 'JP4']:
        sys.exit('REFUSED: found %s' % sorted(done))
    write_stream(PATH, join(recs))
    print('asar_a7_4.SchDoc: rewrote the NOTE of', ', '.join(sorted(done)))


if __name__ == '__main__':
    main()
