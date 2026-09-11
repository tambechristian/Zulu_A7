# -*- coding: utf-8 -*-
"""Check a saved Altium PcbLib against the geometry it was supposed to be built from.

A PcbLib is an OLE compound file: each footprint is one top-level storage, and its `Data` stream is
a run of primitive records. A pad is a 0x02 type byte followed by length-prefixed blocks -- the
first holds its designator, and the first block of 100 bytes or more is the geometry, carrying
X, Y at +13/+17 and the pad X/Y size at +21, all little-endian int32 in units of 1e-7 inch.

That is enough to re-read the library offline and prove it says what the source said, which beats
opening 41 footprints in the PCB editor and eyeballing them.

Altium re-origins an imported footprint, so positions are compared RELATIVE to pad 1 (or, for
footprints with no pad 1, to the alphabetically first pad) rather than absolutely.

    python tools/verify_pcblib.py "<path to .pcblib>"
"""
import io
import json
import os
import re
import struct
import sys
import collections

import olefile

U = 1e-7 * 25.4          # internal unit -> mm
TOL = 0.006              # mm; Altium rounds to its internal grid (0.2751 vs 0.275)

HERE = os.path.dirname(os.path.abspath(__file__))


def pads(f, pkg):
    """Every pad in one footprint as (name, x, y, dx, dy) in mm."""
    d = f.openstream([pkg, 'Data']).read()
    out, i = [], 0
    while i < len(d) - 6:
        if d[i] != 2:
            i += 1
            continue
        j = i + 1
        try:
            nlen = struct.unpack_from('<I', d, j)[0]
            if not (0 < nlen < 64):
                i += 1
                continue
            sl = d[j + 4]
            nm = d[j + 5:j + 5 + sl]
            if sl == 0 or sl != nlen - 1 or not re.fullmatch(rb'[A-Za-z0-9_]+', nm):
                i += 1
                continue
            j += 4 + nlen
            blk = None
            for _ in range(6):
                blen = struct.unpack_from('<I', d, j)[0]
                if blen >= 100:
                    blk = d[j + 4:j + 4 + blen]
                    j += 4 + blen
                    break
                j += 4 + blen
            if blk is None:
                i += 1
                continue
            x, y = struct.unpack_from('<ii', blk, 13)
            xs, ys = struct.unpack_from('<ii', blk, 21)
            out.append((nm.decode(), x * U, y * U, xs * U, ys * U))
            i = j
        except Exception:
            i += 1
    return out


def anchor(ps):
    one = [p for p in ps if p[0] == '1']
    return (one or sorted(ps))[0]


def main(path):
    f = olefile.OleFileIO(path)
    skip = {'FileHeader', 'Library', 'Textures', 'Models', 'ComponentParamsTOC',
            'LayerKindMapping', 'FileVersionInfo'}
    fps = sorted({e[0] for e in f.listdir() if len(e) > 1} - skip)
    print('%s\n%d footprints\n' % (path, len(fps)))

    with io.open(os.path.join(HERE, 'new_footprints.json'), encoding='utf-8') as fh:
        drawn = {d['name']: d for d in json.load(fh)}

    fail = 0
    for name in fps:
        got = pads(f, name)
        if name not in drawn:
            print('  %-20s %3d pads   (from the old board, not re-checked)' % (name, len(got)))
            continue
        want = drawn[name]['pads']
        gn, wn = sorted(p[0] for p in got), sorted(p['name'] for p in want)
        if gn != wn:
            print('  %-20s PAD SET MISMATCH  library=%s  source=%s' % (name, gn, wn))
            fail += 1
            continue
        ga, wa = anchor(got), anchor([(p['name'], p['x'], p['y'], p['dx'], p['dy']) for p in want])
        gmap = {p[0]: (p[1] - ga[1], p[2] - ga[2], p[3], p[4]) for p in got}
        bad = []
        for p in want:
            dx0, dy0 = p['x'] - wa[1], p['y'] - wa[2]
            gx, gy, gdx, gdy = gmap[p['name']]
            # a pad rotated 90 deg in the library reports its sizes swapped; accept either
            size_ok = ((abs(gdx - p['dx']) < TOL and abs(gdy - p['dy']) < TOL) or
                       (abs(gdx - p['dy']) < TOL and abs(gdy - p['dx']) < TOL))
            if abs(gx - dx0) > TOL or abs(gy - dy0) > TOL or not size_ok:
                bad.append('%s lib(%.3f,%.3f,%.3fx%.3f) src(%.3f,%.3f,%.3fx%.3f)'
                           % (p['name'], gx, gy, gdx, gdy, dx0, dy0, p['dx'], p['dy']))
        if bad:
            print('  %-20s %3d pads   %d OFF: %s' % (name, len(got), len(bad), '; '.join(bad[:4])))
            fail += 1
        else:
            sizes = collections.Counter((round(p[3], 3), round(p[4], 3)) for p in got)
            print('  %-20s %3d pads   MATCHES source, sizes %s'
                  % (name, len(got), dict(list(sizes.items())[:3])))

    # the two corrected inherits, checked the same way they were when the library was first built
    print()
    dip = pads(f, 'ZULU-DIP37')
    names = sorted((p[0] for p in dip), key=int)
    rows = collections.defaultdict(list)
    for n, x, y, _, _ in dip:
        rows[round(y, 2)].append(round(x, 2))
    ok_dip = (names == [str(i) for i in range(1, 41)] and len(rows) == 2
              and all(len(v) == 20 for v in rows.values()))
    print('  ZULU-DIP37   %d pads, names 1..40 %s, two rows of 20 %s'
          % (len(dip), 'yes' if names == [str(i) for i in range(1, 41)] else 'NO',
             'yes' if len(rows) == 2 and all(len(v) == 20 for v in rows.values()) else 'NO'))
    cp = pads(f, 'XC7A35T-CPG236')
    sz = {(round(p[3], 4), round(p[4], 4)) for p in cp}
    # 0.225, not UG475's 0.275 maximum: the larger land closes the escape gap -- see
    # make_fp_source.py section B and board/STACKUP.md
    ok_cp = len(cp) == 238 and all(abs(a - 0.225) < TOL and abs(b - 0.225) < TOL for a, b in sz)
    print('  CPG236       %d lands, sizes %s' % (len(cp), sz))
    f.close()

    if fail or not ok_dip or not ok_cp:
        print('\nFAILED: %d drawn footprints off, DIP37 %s, CPG236 %s'
              % (fail, 'ok' if ok_dip else 'BAD', 'ok' if ok_cp else 'BAD'))
        return 1
    print('\nAll %d drawn footprints match tools/new_footprints.json; DIP37 and CPG236 both good.'
          % len(drawn))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
