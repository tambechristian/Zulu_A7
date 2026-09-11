# -*- coding: utf-8 -*-
"""FRAME1-FRAME7 become Graphical components, 2026-09-10.

Each sheet carries a DOCFIELD ("DOCUMENT FIELD") component -- EAGLE's title-block document field,
which the Altium importer turned into a real component with zero pins and no footprint. Left alone
they are Standard components, so Design > Import Changes would demand a footprint for all seven
and stop with seven errors before a single part reached the board. tools/board_preflight.py found
them; they are the only components in the project with no footprint.

Altium's ComponentKind: 0 Standard, 1 Mechanical, 2 Graphical, 3 Net Tie (In BOM), 4 Net Tie,
5 Standard (No BOM). Graphical is the right answer for a title block: excluded from the PCB and
from the BOM, drawn on the schematic and nowhere else. No component in this project carries the
field at all today, so it is inserted rather than replaced.

One field per component record, no inserts, no index shifts, nothing renumbered.

Run with the project closed in Altium:

    for i in 0 1 2 3 4 5 6; do python tools/frames_graphical.py tools \\
        "Imported zulu_a7.PrjPcb/zulu_a7_$i.SchDoc"; done
"""
import sys

sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else 'tools')
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

GRAPHICAL = '2'
LIBREF = 'DOCFIELD'


def main(path):
    data = read_stream(path, 'FileHeader')
    recs = split(data)

    # the designator record names it; its owner is the component
    frames = [int(field(b, 'OwnerIndex')) + 1 for h, b in recs
              if b.startswith(b'|RECORD=34|') and (field(b, 'Text') or '').startswith('FRAME')]
    if not frames:
        print('%s: no FRAME component, nothing done' % path)
        return

    done = []
    for ci in frames:
        b = recs[ci][1]
        if not b.startswith(b'|RECORD=1|'):
            raise SystemExit('%s: record %d is not a component' % (path, ci))
        lib = field(b, 'LibReference')
        if lib != LIBREF:
            raise SystemExit('%s: FRAME at %d is %s, not %s; nothing done' % (path, ci, lib, LIBREF))
        was = field(b, 'ComponentKind')
        if was == GRAPHICAL:
            done.append('already graphical')
            continue
        pins = sum(1 for h, x in recs
                   if x.startswith(b'|RECORD=2|') and field(x, 'OwnerIndex') == str(ci - 1))
        if pins:
            raise SystemExit('%s: FRAME at %d has %d pins; that is not a title block' % (path, ci, pins))
        recs[ci][1] = set_field(b, 'ComponentKind', GRAPHICAL)
        done.append('ComponentKind %s -> %s' % (was, GRAPHICAL))

    out = join(recs)
    write_stream(path, 'FileHeader', out)
    assert read_stream(path, 'FileHeader') == out
    print('%s  %d FRAME component(s): %s' % (path, len(frames), '; '.join(done)))


if __name__ == '__main__':
    main(sys.argv[2])
