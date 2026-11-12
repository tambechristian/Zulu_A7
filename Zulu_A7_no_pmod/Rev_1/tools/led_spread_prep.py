"""Fab B LED spread, step 1 (2026-11-07): the router model with LD0-LD5 at their new places and the pocket cleared.

    python tools/led_spread_prep.py [route/model.json] [route/led/]

The user asked for the LED column to be spread evenly (the 0603 LEDs sat on a 1.2 mm pitch, 0.30 mm gaps).
New column, x unchanged at 23.35: LD4 stays at 17.385, LD3/LD5/LD2/LD1 follow on a 1.6 mm pitch (0.70 mm gaps)
and LD0 (the 1.6 x 1.6 RGB) sits 0.70 mm below LD1.

Writes
  model.json   the model with the six parts' pads moved and the ripped copper gone (router input)
  rip.json     {'remove': tracks, 'remove_vias': vias, 'moves': [{ref, dy, x, y}]} in model coordinates
What is ripped
  1. every track / via of an LED net (the 12 LED signal nets) inside the pocket window WIN
  2. every track / via of ANY net, on any layer of its span that has an LED land, that comes within
     CLEAR + SLACK of a new LED land (Top only: the LEDs are Top parts), and every via of the same column
     (same net, same x/y) as a ripped via
  3. GND / VCC3V3 tracks that end on an old LED land (their island is re-tied by the router's plane vias)
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import route_conn as C  # noqa: E402

SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'route', 'model.json')
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'route', 'led')
NEW_Y = {'LD4': 17.385, 'LD3': 15.785, 'LD5': 14.185, 'LD2': 12.585, 'LD1': 10.985, 'LD0': 8.91}
OLD_Y = {'LD4': 17.385, 'LD3': 16.185, 'LD5': 14.985, 'LD2': 13.785, 'LD1': 12.585, 'LD0': 10.885}
X = 23.35
LED_NETS = {'N$LD1A', 'N$LD2A', 'NetLD3_A', 'NetLD3_K', 'NetLD4_A', 'NetLD4_K', 'LD5_K',
            'LED0_B', 'LED0_R', 'LED0_G', 'N$LD0B', 'N$LD0R', 'N$LD0G'}
WIN = (20.9, 7.75, 25.0, 18.25)          # x0, y0, x1, y1
CLEAR, SLACK = 0.09, 0.03


def inwin(x, y):
    return WIN[0] <= x <= WIN[2] and WIN[1] <= y <= WIN[3]


def seg_in_win(t):
    return any(inwin(t['x1'] + (t['x2'] - t['x1']) * k / 16, t['y1'] + (t['y2'] - t['y1']) * k / 16)
               for k in range(17))


def main():
    M = json.load(open(SRC))
    os.makedirs(OUT, exist_ok=True)
    old_pads = [dict(p) for p in M['pads'] if p['ref'] in NEW_Y]
    for p in M['pads']:
        if p['ref'] in NEW_Y:
            p['y'] = round(p['y'] + NEW_Y[p['ref']] - OLD_Y[p['ref']], 4)
    new_pads = [p for p in M['pads'] if p['ref'] in NEW_Y]

    rm_t, rm_v = [], []
    for t in M['tracks']:
        if t['net'] in LED_NETS and seg_in_win(t):
            rm_t.append(t)
        elif t['layer'] == 'Top Layer' and any(
                t['net'] != p['net'] and C.pad_seg(p, (t['x1'], t['y1'], t['x2'], t['y2'])) - t['w'] / 2 < CLEAR + SLACK
                for p in new_pads):
            rm_t.append(t)
        elif t['layer'] == 'Top Layer' and t['net'] in ('GND', 'VCC3V3') and any(
                C.pad_point(p, x, y) < 1e-3 for p in old_pads for x, y in ((t['x1'], t['y1']), (t['x2'], t['y2']))):
            rm_t.append(t)
    cols = set()
    for v in M['vias']:
        if v['net'] in LED_NETS and inwin(v['x'], v['y']):
            cols.add((v['net'], round(v['x'], 3), round(v['y'], 3)))
        elif 'Top Layer' in v['span'] and any(
                v['net'] != p['net'] and C.pad_point(p, v['x'], v['y']) - v['size'] / 2 < CLEAR + SLACK for p in new_pads):
            cols.add((v['net'], round(v['x'], 3), round(v['y'], 3)))
    rm_v = [v for v in M['vias'] if (v['net'], round(v['x'], 3), round(v['y'], 3)) in cols]
    ids_t = {id(t) for t in rm_t}
    ids_v = {id(v) for v in rm_v}
    M['tracks'] = [t for t in M['tracks'] if id(t) not in ids_t]
    M['vias'] = [v for v in M['vias'] if id(v) not in ids_v]
    moves = [{'ref': r, 'dy': round(NEW_Y[r] - OLD_Y[r], 4), 'x': X, 'y': NEW_Y[r]} for r in NEW_Y
             if NEW_Y[r] != OLD_Y[r]]
    json.dump(M, open(os.path.join(OUT, 'model.json'), 'w'))
    json.dump({'remove': rm_t, 'remove_vias': rm_v, 'moves': moves}, open(os.path.join(OUT, 'rip.json'), 'w'), indent=1)
    nets = sorted({t['net'] for t in rm_t} | {v['net'] for v in rm_v})
    print('ripped %d tracks, %d vias (%d columns) on %d nets: %s' % (len(rm_t), len(rm_v), len(cols), len(nets),
                                                                    ', '.join(nets)))
    oc = C.open_count(C.islands(M))
    print('open connections now: %d on %d nets' % (sum(oc.values()), len(oc)))
    for n, k in sorted(oc.items()):
        print('  %-12s %d' % (n, k))


if __name__ == '__main__':
    main()
