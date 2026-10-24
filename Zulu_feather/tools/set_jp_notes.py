"""Reword JP3/JP4's NOTE and SPEC for the Feather board (2026-10-23, user request).

On the production board they were bare plated 1x3 holes beside the Pmod; on the Feather they are bottom-side SMD
test pads (footprint TP-1X03-SMD). Only these two parameter texts change on each part; the script refuses unless
it finds the old "Bare plated holes" / "three bare plated holes" wording, so it cannot run twice.
    python tools/set_jp_notes.py      (close zulu_a7_4.SchDoc in Altium first)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schdoc import field, join, owner, read_stream, set_field, split, write_stream  # noqa: E402

PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Zulu_feather.PrjPcb', 'zulu_a7_4.SchDoc')
NOTE = {
    'JP3': 'Bottom-side SMD test pads -- NO PART FITTED, nothing to order. Three of the six JTAG pads (TCK, TMS, GND); '
           'JP4 carries TDI, TDO and VCC3V3, 4.2 mm away under the FT2232H. Footprint TP-1X03-SMD: three 1.0 mm round '
           'pads on 1.27 mm, for a pogo-pin jig or soldered flying leads. The FT2232 does JTAG over USB on channel B; '
           'this is the fallback.',
    'JP4': 'Bottom-side SMD test pads -- NO PART FITTED, nothing to order. Three of the six JTAG pads (TDI, TDO, '
           'VCC3V3); JP3 carries TCK, TMS and GND, 4.2 mm away under the FT2232H. Footprint TP-1X03-SMD: three 1.0 mm '
           'round pads on 1.27 mm, for a pogo-pin jig or soldered flying leads. The FT2232 does JTAG over USB on '
           'channel B; this is the fallback.',
}
SPEC = ('DNS - do not stuff: three bottom-side 1.0 mm round SMD pads, 1x3 on 1.27 mm (TP-1X03-SMD), for pogo pins or '
        'flying leads; no part to order (Feather board, 2026-10-23)')


def main():
    recs = split(read_stream(PATH))
    refs = {owner(b): field(b, 'Text') for h, b in recs if field(b, 'RECORD') == '34'}
    done = []
    for i, (h, b) in enumerate(recs):
        ref = refs.get(owner(b))
        name = field(b, 'Name')
        if ref not in NOTE or field(b, 'RECORD') != '41' or name not in ('NOTE', 'SPEC'):
            continue
        old = field(b, 'Text') or ''
        if name == 'NOTE' and not old.startswith('Bare plated holes'):
            sys.exit('REFUSED: %s NOTE is not the old wording: %r' % (ref, old[:40]))
        if name == 'SPEC' and 'three bare plated holes' not in old:
            sys.exit('REFUSED: %s SPEC is not the old wording: %r' % (ref, old[:40]))
        recs[i][1] = set_field(b, 'Text', NOTE[ref] if name == 'NOTE' else SPEC)
        done.append('%s %s' % (ref, name))
    if sorted(done) != ['JP3 NOTE', 'JP3 SPEC', 'JP4 NOTE', 'JP4 SPEC']:
        sys.exit('REFUSED: found %s' % sorted(done))
    write_stream(PATH, join(recs))
    print('zulu_a7_4.SchDoc: rewrote', ', '.join(sorted(done)))


if __name__ == '__main__':
    main()
