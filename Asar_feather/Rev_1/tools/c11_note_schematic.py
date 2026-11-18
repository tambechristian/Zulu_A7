"""Sheet 4 (asar_a7_3.SchDoc), 2026-11-17: the U3 DECOUPLING note listed C11 among the caps under U3; C11 now sits on the top
beside U4 pin 8 as U4's bypass (docs/c11_move.md). Rewrites only that sentence of the note and proves the sheet's nets unchanged.

    python tools/c11_note_schematic.py Asar_feather.PrjPcb/asar_a7_3.SchDoc
"""
import hashlib
import sys

from schdoc import field, join, read_stream, set_field, split, write_stream
from sheet3_u3_layout import net_map, report

SRC_MD5 = 'a999eb30bbb53f82dd57c2a4b4c67ec3'
OLD = 'C3-C9, C11 and C12 ~1(0.1 uF) and C13 (10 uF bulk) are on the bottom side under U3. ~1Do NOT split the ground plane.'
NEW = ("C3-C9 and C12 ~1(0.1 uF) and C13 (10 uF bulk) are on the bottom side under U3; C11 (U4's bypass) is on ~1"
       "the top beside U4 pin 8. Do NOT split the ground plane.")


def main(path):
    if hashlib.md5(open(path, 'rb').read()).hexdigest() != SRC_MD5:
        raise SystemExit('%s is not the expected sheet (md5 %s)' % (path, SRC_MD5))
    raw = read_stream(path)
    R = split(raw)
    before = net_map(R)
    hit = [i for i, (h, b) in enumerate(R) if field(b, 'RECORD') == '28' and (field(b, 'Text') or '').startswith('U3 DECOUPLING')]
    assert len(hit) == 1
    t = field(R[hit[0]][1], 'Text')
    assert t.count(OLD) == 1, t
    R[hit[0]][1] = set_field(R[hit[0]][1], 'Text', t.replace(OLD, NEW))
    blob = join(R)
    write_stream(path, blob)
    assert read_stream(path) == blob
    print(field(R[hit[0]][1], 'Text').replace('~1', '\n'))
    report(before, net_map(split(read_stream(path))))


if __name__ == '__main__':
    main(sys.argv[1])
