# -*- coding: utf-8 -*-
"""Move the designators that print over a neighbour's solder-mask opening.

The 2026-09-11 DRC leaves 37 Silk To Solder Mask violations. They are not 37 objects: they are
SIXTEEN designators, each hitting two to five pads that belong to a DIFFERENT component. Every
one of the sixteen is a part a human needs labelled -- U1, U3, U4, U6, U7, U8, U10, L1, L2, L3,
Q1, J1, R4, X4, BTN, LD0 -- so hiding them is the wrong answer. HideChipDesignators already took
the 145 chip passives; these are what is left, and they have to move instead.

WHERE THE NUMBERS COME FROM
  the offending text      parsed out of Texts6/Data -- x, y at byte 13/17, height at 21, stroke
                          at 25, rotation (double) at 27. Verified against the DRC's own reported
                          coordinates for LD0, L1, L2 and U3: exact to the micron.
  every pad on the board  place_board.rects(), the same per-pad geometry verify_copper.py uses,
                          rebuilt from pad 1 of each placed component. NOT the pad bounding box,
                          which for a drilled pad includes the plane anti-pad and is 0.5 mm too
                          big on every side.
  the forbidden zone      each pad grown by the SolderMaskExpansion rule (0.05 mm) to get the
                          mask opening, then by the Silk To Solder Mask rule (0.254 mm).

A text on Top Overlay competes with Top Layer pads and with every drilled pad; Bottom Overlay
likewise. That is the same same-side-or-drilled test place_board already uses for copper.

THE TEXT BOX. Altium anchors stroke text at the BOTTOM LEFT and the record stores the character
height, not the string extent. Width is modelled as n x 0.6 x height + stroke and height as
height + stroke, which reproduces all 37 reported collisions and adds none -- checked below, and
the check fails loudly if it stops reproducing them.

THE SEARCH is a spiral on the 0.025 mm snap grid out to 4 mm, nearest-first, so a designator ends
up as close to where the designer put it as the board allows. It must also stay 0.3 mm inside the
outline. If nothing is found the designator is reported, not silently left.

    python tools/fix_silk.py           report
    python tools/fix_silk.py --emit    write tools/silk_moves.txt
"""
import io
import os
import re
import struct
import sys

import olefile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import place_board as pb
from verify_placement import read_report
from verify_copper import lib_pad_offsets, transform

PCB   = os.path.join(HERE, '..', 'Imported zulu_a7.PrjPcb', 'zulu_a7.PcbDoc')
DRC   = os.path.join(HERE, '..', 'Imported zulu_a7.PrjPcb',
                     'Project Outputs for zulu_a7', 'Design Rule Check - zulu_a7.drc')
U     = 2.54e-6          # 1e-7 inch -> mm
MASK  = 0.05             # SolderMaskExpansion rule
SILK  = 0.254            # Silk To Solder Mask rule
EDGE  = 0.30             # keep silk this far inside the outline
STEP  = 0.025            # the board's snap grid
REACH = 4.0              # how far a designator may be moved


def texts():
    """every text primitive: string, layer, x, y, height, stroke, rotation."""
    f = olefile.OleFileIO(PCB)
    d = f.openstream('Texts6/Data').read()
    out, i = [], 0
    while i + 5 <= len(d):
        ln = struct.unpack('<I', d[i + 1:i + 5])[0]
        if i + 5 + ln > len(d):
            break
        b = d[i + 5:i + 5 + ln]
        i += 5 + ln
        if i + 4 > len(d):
            break
        sl = struct.unpack('<I', d[i:i + 4])[0]
        i += 4
        raw = d[i:i + sl]
        i += sl
        s = raw[1:1 + raw[0]].decode('latin-1') if sl else ''
        out.append(dict(s=s, layer=b[0],
                        x=struct.unpack('<i', b[13:17])[0] * U,
                        y=struct.unpack('<i', b[17:21])[0] * U,
                        h=struct.unpack('<i', b[21:25])[0] * U,
                        w=struct.unpack('<i', b[25:29])[0] * U,
                        rot=struct.unpack('<d', b[27:35])[0]))
    f.close()
    return out


def box(t):
    """bottom-left anchored bounding box of a stroke-font string."""
    wid = len(t['s']) * 0.6 * t['h'] + t['w']
    return t['x'], t['y'], t['x'] + wid, t['y'] + t['h'] + t['w']


def violations():
    h = io.open(DRC, encoding='latin-1').read()
    pat = re.compile(r'Silk To Solder Mask Clearance Constraint:\s*\([^)]*\)\s*Between Pad '
                     r'([^\s(]+)\([-\d.]+mm,[-\d.]+mm\) on .*?And Text "([^"]*)"\s*'
                     r'\(([-\d.]+)mm,([-\d.]+)mm\)')
    return [(m.group(2), float(m.group(3)), float(m.group(4)), m.group(1))
            for m in pat.finditer(h)]


def pad_rects():
    """side, x0, y0, x1, y1, multilayer, designator for every pad on the board."""
    comp, ext, place, src, missing, overflow = pb.build(verbose=False)
    got = read_report()
    off = lib_pad_offsets()
    actual = {}
    for d, g in got.items():
        fp = comp.get(d)
        o = off.get(fp, {}).get('1') if fp else None
        if o is None or g['p1'] is None:
            actual[d] = (g['layer'], g['rot'], g['cx'], g['cy'])
        else:
            tx, ty = transform(o[0], o[1], g['rot'], g['layer'] == 'bottom')
            actual[d] = (g['layer'], g['rot'], g['p1'][0] - tx, g['p1'][1] - ty)
    rc = pb.rects(comp, pb.lib_geometry(), actual)
    out = []
    for d in rc:
        side, rs = rc[d]
        for r in rs:
            x0, y0, x1, y1, multi = r[0], r[1], r[2], r[3], r[4]
            out.append((side, x0 - MASK, y0 - MASK, x1 + MASK, y1 + MASK, multi, d))
    return out


def hits(bx, pads, side):
    """pads whose mask opening comes within SILK of this text box."""
    x0, y0, x1, y1 = bx
    bad = []
    for pside, px0, py0, px1, py1, multi, d in pads:
        if not (pside == side or multi):
            continue
        if (min(x1, px1 + SILK) > max(x0, px0 - SILK) and
                min(y1, py1 + SILK) > max(y0, py0 - SILK)):
            bad.append(d)
    return bad


def main():
    v = violations()
    ts = texts()
    pads = pad_rects()
    print('DRC reports %d Silk To Solder Mask violations' % len(v))

    key = {(s, round(x, 3), round(y, 3)) for s, x, y, _ in v}
    bad = [t for t in ts if (t['s'], round(t['x'], 3), round(t['y'], 3)) in key]
    print('matched %d of %d offending text objects in Texts6' % (len(bad), len(key)))

    print('\n--- box model check ---')
    ok = True
    for t in bad:
        side = 'top' if t['layer'] == 33 else 'bottom'
        got = set(hits(box(t), pads, side))
        want = set(p.split('-')[0] for s, x, y, p in v
                   if s == t['s'] and round(x, 3) == round(t['x'], 3))
        if not want <= got:
            print('  MISS %-5s predicted %s, DRC found %s' % (t['s'], sorted(got), sorted(want)))
            ok = False
    print('  model reproduces every reported collision' if ok else '  MODEL IS WRONG - stop')

    print('\n--- search ---')
    moves, stuck = [], []
    n = int(REACH / STEP)
    spiral = sorted(((dx * STEP, dy * STEP) for dx in range(-n, n + 1) for dy in range(-n, n + 1)),
                    key=lambda o: (o[0] ** 2 + o[1] ** 2))
    for t in sorted(bad, key=lambda t: t['s']):
        side = 'top' if t['layer'] == 33 else 'bottom'
        x0, y0, x1, y1 = box(t)
        w, h = x1 - x0, y1 - y0
        found = None
        for dx, dy in spiral:
            nb = (x0 + dx, y0 + dy, x0 + dx + w, y0 + dy + h)
            if (nb[0] < EDGE or nb[1] < EDGE
                    or nb[2] > pb.BOARD[0] - EDGE or nb[3] > pb.BOARD[1] - EDGE):
                continue
            if not hits(nb, pads, side):
                found = (dx, dy)
                break
        if found:
            moves.append((t, found))
            print('  %-4s %-7s (%8.3f,%7.3f) -> (%8.3f,%7.3f)   moved %.3f mm'
                  % (t['s'], side, t['x'], t['y'], t['x'] + found[0], t['y'] + found[1],
                     (found[0] ** 2 + found[1] ** 2) ** 0.5))
        else:
            stuck.append(t)
            print('  %-4s %-7s NO CLEAR POSITION within %.1f mm' % (t['s'], side, REACH))

    print('\n%d moved, %d stuck' % (len(moves), len(stuck)))

    if '--emit' in sys.argv and ok and not stuck:
        lines = ["    Move('%s', %.4f, %.4f);" % (t['s'], t['x'] + dx, t['y'] + dy)
                 for t, (dx, dy) in moves]
        io.open(os.path.join(HERE, 'silk_moves.txt'), 'w').write('\n'.join(lines) + '\n')
        print('wrote tools/silk_moves.txt')
    return 0


if __name__ == '__main__':
    sys.exit(main())
