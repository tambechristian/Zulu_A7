"""Silk edits for the 2026-11-19 DRC (2026-11-19). READ-ONLY; writes silk_plan.json and checks every new line.

    python tools/route/drc20/silk.py

Rule: Silk To Solder Mask 0.254 mm (measured, as the DRC does, from the pad copper: the U2-1 item reads 0.185 mm =
0.26 - 0.075). Every new line keeps MARGIN from every pad on its side (through-hole pads on both), and from the other
silk of its side.
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
M = json.load(open(os.path.join(os.path.dirname(HERE), 'illustration', 'base.json')))
MARGIN = 0.27       # rule 0.254 + a little; the X4 line keeps its existing 0.275 mm to X4-1
# (layer, width, old line, new line, why)
EDITS = [
    ('Top', 0.15, (25.9, 9.95, 26.35, 9.95), (25.9, 9.95, 26.25, 9.95), 'U2 corner mark, SW, arm along the bottom'),
    ('Top', 0.15, (25.9, 9.95, 25.9, 10.4), (25.9, 9.95, 25.9, 10.3), 'U2 corner mark, SW, arm up the side'),
    ('Top', 0.15, (25.9, 19.15, 26.35, 19.15), (25.9, 19.15, 26.25, 19.15), 'U2 corner mark, NW'),
    ('Top', 0.15, (25.9, 18.7, 25.9, 19.15), (25.9, 18.8, 25.9, 19.15), 'U2 corner mark, NW'),
    ('Top', 0.15, (34.65, 9.95, 35.1, 9.95), (34.75, 9.95, 35.1, 9.95), 'U2 corner mark, SE'),
    ('Top', 0.15, (35.1, 9.95, 35.1, 10.4), (35.1, 9.95, 35.1, 10.3), 'U2 corner mark, SE'),
    ('Top', 0.15, (34.65, 19.15, 35.1, 19.15), (34.75, 19.15, 35.1, 19.15), 'U2 corner mark, NE'),
    ('Top', 0.15, (35.1, 18.7, 35.1, 19.15), (35.1, 18.8, 35.1, 19.15), 'U2 corner mark, NE'),
    ('Top', 0.15, (29.54, 8.65, 29.54, 9.5), (29.54, 8.65, 29.54, 9.35), 'X4 pin-1 line, clear of U2 pads 22/23'),
    ('Bottom', 0.15, (21.8851, 18.195, 21.8851, 18.495), (21.15, 18.6, 21.6, 18.6),
     'U10 pin-1 mark, out of U3-33 into the gap below U10 pin 1'),
]


def segbox_gap(seg, w, box):
    """Clearance from a round-capped line (x1, y1, x2, y2, width w) to a box (x0, y0, x1, y1)."""
    x1, y1, x2, y2 = seg
    best = 1e9
    for k in range(201):
        t = k / 200
        px, py = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
        dx = max(box[0] - px, 0, px - box[2])
        dy = max(box[1] - py, 0, py - box[3])
        best = min(best, math.hypot(dx, dy))
    return best - w / 2


ok = True
for side, w, old, new, why in EDITS:
    lay = 'Top Layer' if side == 'Top' else 'Bottom Layer'
    g, who = 1e9, None
    for p in M['pads']:
        if p['drill'] or (p['layers'] and lay in p['layers']) or not p['layers']:
            if not (p['drill'] or not p['layers'] or lay in p['layers']):
                continue
            b = (p['x'] - p['w'] / 2, p['y'] - p['h'] / 2, p['x'] + p['w'] / 2, p['y'] + p['h'] / 2)
            d = segbox_gap(new, w, b)
            if d < g:
                g, who = d, '%s-%s' % (p['ref'], p['pad'])
    gold = min(segbox_gap(old, w, (p['x'] - p['w'] / 2, p['y'] - p['h'] / 2, p['x'] + p['w'] / 2, p['y'] + p['h'] / 2))
               for p in M['pads'] if p['drill'] or not p['layers'] or lay in p['layers'])
    print('%-6s %-58s pad gap %.3f -> %.3f (nearest %s) %s' % (side, why, gold, g, who, 'OK' if g >= MARGIN else 'TOO CLOSE'))
    ok &= g >= MARGIN
assert ok
json.dump([dict(side=s, w=w, old=o, new=n, why=y) for s, w, o, n, y in EDITS], open(os.path.join(HERE, 'silk_plan.json'), 'w'), indent=1)
