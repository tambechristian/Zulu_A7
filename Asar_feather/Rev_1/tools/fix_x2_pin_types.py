"""Second step of the X2 re-arrangement (2026-10-23): restore each pad's pin properties.

arrange_x2.py re-pointed each X2 slot to another part. A placed copy keeps the electrical type and other pin
properties only for the part it originally showed; the other parts' pins in that copy are defaults. So after the
re-pointing, GND/VBATT/USB5V0 lost their power type and the CHAN pins their I/O type, which Altium's ERC reported.
This copies, for every pad, the pin record that showed it before the arrangement (read from the given backup)
into the slot now showing it, keeping only the new record's OwnerIndex, Location and PinConglomerate (the
pin's direction, which depends on the slot's side: 50 left, 48 right).
    python tools/fix_x2_pin_types.py <asar_a7_2.SchDoc saved before arrange_x2.py>
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schdoc import field, join, owner, read_stream, split, write_stream  # noqa: E402

PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Asar_feather.PrjPcb', 'asar_a7_2.SchDoc')
KEEP = re.compile(rb'\|(?:OwnerIndex|Location\.X|Location\.Y|Location\.X_Frac|Location\.Y_Frac)=[^|\x00]*')


def shown_pins(recs):
    refs = {owner(b): field(b, 'Text') for h, b in recs if field(b, 'RECORD') == '34'}
    out = {}
    for c, r in refs.items():
        if r != 'X2':
            continue
        cur = field(recs[c][1], 'CurrentPartId')
        for i, (h, b) in enumerate(recs):
            if owner(b) == c and field(b, 'RECORD') == '2' and field(b, 'OwnerPartId') == cur:
                out[field(b, 'Designator')] = i
    return out


def main():
    old = split(read_stream(sys.argv[1]))
    recs = split(read_stream(PATH))
    before, now = shown_pins(old), shown_pins(recs)
    if sorted(before, key=int) != sorted(now, key=int) or len(now) != 28:
        sys.exit('REFUSED: pad sets differ: before %s now %s' % (sorted(before), sorted(now)))
    fixed = 0
    for pad, i in now.items():
        src = old[before[pad]][1]
        keep = b''.join(KEEP.findall(recs[i][1]))
        body = KEEP.sub(b'', src)
        m = re.match(rb'\|RECORD=2', body)
        new = body[:m.end()] + keep + body[m.end():]
        if new != recs[i][1]:
            recs[i][1] = new
            fixed += 1
    write_stream(PATH, join(recs))
    print('X2: restored the original pin record on %d of 28 pads' % fixed)


if __name__ == '__main__':
    main()
