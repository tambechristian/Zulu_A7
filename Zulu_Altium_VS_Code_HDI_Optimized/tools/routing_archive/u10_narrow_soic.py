# -*- coding: utf-8 -*-
"""U10 moves from the 300-mil SOIC8 pattern to the 150-mil SPI-8_SOIC_150, 2026-09-10.

The EEPROM fitted is the Microchip 93LC46BT-I/SN: SN = the 3.90 mm narrow body with a 6.00 mm BSC
lead span. The imported SOIC8 package is a 300-mil pattern with its pad rows 7.62 mm apart, so its
pads begin 3.06 mm out from the centreline while the leads stop at 3.00 mm -- the part cannot
solder to it. That has been open since the 2026-09-07 footprint audit with two ways out: change the
land, or order the 208-mil SOIJ part 93LC46BT-I/SM to suit the pads. This takes the first.

SPI-8_SOIC_150 was copied into the PcbLib from zulu_a7.sch on 2026-09-10 for exactly this. Its rows
are 4.93 mm apart with 2.07 x 0.51 mm pads on the 1.27 mm pitch, so the lands run from 1.43 to 3.50
mm either side of the centreline: they start inside the 1.95 mm body edge for a heel fillet and
reach 0.50 mm past the 3.00 mm lead tip for a toe fillet. Pads are numbered 1-4 down one side and
5-8 back up the other, matching U10's pins.

The edit is one record rewritten in place -- no index shifts, nothing renumbered. The footprint name
appears TWICE in a RECORD=45 (ModelName and ModelDatafileEntity0) and both have to move, which is
the only trap here.

Run with the project closed in Altium, or at least with sheet 4 not open in an editor:

    python tools/u10_narrow_soic.py tools "Imported zulu_a7.PrjPcb/zulu_a7_4.SchDoc"
"""
import sys

sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else 'tools')
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

OLD = 'SOIC8'
NEW = 'SPI-8_SOIC_150'
PART = 'U10'


def main(path):
    data = read_stream(path, 'FileHeader')
    recs = split(data)

    hits = [int(field(b, 'OwnerIndex')) + 1 for h, b in recs
            if b.startswith(b'|RECORD=34|') and field(b, 'Text') == PART]
    if len(hits) != 1:
        print('%s: %s appears %d times, nothing done' % (path, PART, len(hits)))
        return
    ci = hits[0]

    # the model record hangs off the component's Comment parameter, not off the component, so walk
    # the whole subtree rather than assuming a depth
    tree, lvl = set(), [ci]
    while lvl:
        nxt = [i for i, (h, b) in enumerate(recs)
               if field(b, 'OwnerIndex') in {str(j - 1) for j in lvl} and i not in tree]
        tree |= set(nxt)
        lvl = nxt

    targets = [i for i in sorted(tree)
               if recs[i][1].startswith(b'|RECORD=45|')
               and field(recs[i][1], 'ModelType') == 'PCBLIB']
    if len(targets) != 1:
        raise SystemExit('%s has %d PCBLIB model records, expected 1' % (PART, len(targets)))
    i = targets[0]
    b = recs[i][1]
    was = field(b, 'ModelName')
    if was == NEW:
        print('%s: %s already on %s, nothing done' % (path, PART, NEW))
        return
    if was != OLD:
        raise SystemExit('%s footprint is %s, not %s; nothing done' % (PART, was, OLD))

    b = set_field(b, 'ModelName', NEW)
    b = set_field(b, 'ModelDatafileEntity0', NEW)       # the second copy of the name
    recs[i][1] = b

    assert field(b, 'ModelName') == NEW
    assert field(b, 'ModelDatafileEntity0') == NEW
    assert OLD.encode() not in b, 'a copy of the old name survived: %s' % b

    out = join(recs)
    assert len(out) == len(data) + 2 * (len(NEW) - len(OLD)), 'unexpected size change'
    write_stream(path, 'FileHeader', out)
    assert read_stream(path, 'FileHeader') == out
    print('%s  %s: footprint %s -> %s (record %d, ModelName and ModelDatafileEntity0); '
          '%d records, none renumbered' % (path, PART, OLD, NEW, i, len(recs)))


if __name__ == '__main__':
    main(sys.argv[2])
