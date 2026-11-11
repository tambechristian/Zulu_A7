"""Fab B BTN spread, step 1 (2026-11-08): the router model with BTN moved west and its pocket cleared.

    python tools/btn_spread_prep.py [route/led/final.json] [route/btn/]

After the LED column was spread, BTN (PTS810, body 3.2 x 4.2 mm) sat 0.9 mm (pad to pad) from the LED column on its
east and 3.2 mm from the microSD socket X3 on its west. It moves DX west so that the two Top-side gaps are equal:
X3 pad edge 15.025 -> BTN pad edge, and BTN pad edge -> LED pad edge 22.10.

Writes model.json (router input) and rip.json {'remove', 'remove_vias', 'moves'} like led_spread_prep.py.
What is ripped
  1. every track / via of N$BTN inside the pocket window WIN
  2. every Top track, and every via whose span includes Top, of ANY other net within CLEAR + SLACK of a new BTN land
  3. BTN-net (N$BTN / VCC3V3) tracks ending on an old BTN land and vias inside an old BTN land (via-in-pad stacks)
  4. every via of the same column (same net, x, y) as a ripped via
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import route_conn as C  # noqa: E402

SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'route', 'led', 'final.json')
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'route', 'btn')
REF, OLD = 'BTN', (19.80, 12.92)
DX = -1.25
WIN = (15.6, 9.0, 21.9, 16.9)
CLEAR, SLACK = 0.09, 0.03


def inwin(x, y):
    return WIN[0] <= x <= WIN[2] and WIN[1] <= y <= WIN[3]


def seg_in_win(t):
    return any(inwin(t['x1'] + (t['x2'] - t['x1']) * k / 16, t['y1'] + (t['y2'] - t['y1']) * k / 16) for k in range(17))


def main():
    M = json.load(open(SRC))
    os.makedirs(OUT, exist_ok=True)
    old_pads = [dict(p) for p in M['pads'] if p['ref'] == REF]
    for p in M['pads']:
        if p['ref'] == REF:
            p['x'] = round(p['x'] + DX, 4)
    new_pads = [p for p in M['pads'] if p['ref'] == REF]
    bnets = {p['net'] for p in new_pads}

    def on_old(x, y, net):
        return any(p['net'] == net and C.pad_point(p, x, y) < 1e-3 for p in old_pads)

    rm_t = []
    for t in M['tracks']:
        if t['net'] == 'N$BTN' and seg_in_win(t):
            rm_t.append(t)
        elif t['layer'] == 'Top Layer' and any(
                t['net'] != p['net'] and C.pad_seg(p, (t['x1'], t['y1'], t['x2'], t['y2'])) - t['w'] / 2 < CLEAR + SLACK
                for p in new_pads):
            rm_t.append(t)
        elif t['layer'] == 'Top Layer' and t['net'] in bnets and (on_old(t['x1'], t['y1'], t['net']) or
                                                                 on_old(t['x2'], t['y2'], t['net'])):
            rm_t.append(t)
    cols = set()
    for v in M['vias']:
        key = (v['net'], round(v['x'], 3), round(v['y'], 3))
        if v['net'] == 'N$BTN' and inwin(v['x'], v['y']):
            cols.add(key)
        elif 'Top Layer' in v['span'] and any(
                v['net'] != p['net'] and C.pad_point(p, v['x'], v['y']) - v['size'] / 2 < CLEAR + SLACK for p in new_pads):
            cols.add(key)
        elif 'Top Layer' in v['span'] and v['net'] in bnets and any(
                p['net'] == v['net'] and C.pad_point(p, v['x'], v['y']) - v['size'] / 2 < 1e-3 for p in old_pads):
            cols.add(key)
    rm_v = [v for v in M['vias'] if (v['net'], round(v['x'], 3), round(v['y'], 3)) in cols]
    ids_t, ids_v = {id(t) for t in rm_t}, {id(v) for v in rm_v}
    M['tracks'] = [t for t in M['tracks'] if id(t) not in ids_t]
    M['vias'] = [v for v in M['vias'] if id(v) not in ids_v]
    moves = [{'ref': REF, 'dx': DX, 'dy': 0.0, 'x': round(OLD[0] + DX, 4), 'y': OLD[1]}]
    json.dump(M, open(os.path.join(OUT, 'model.json'), 'w'))
    json.dump({'remove': rm_t, 'remove_vias': rm_v, 'moves': moves}, open(os.path.join(OUT, 'rip.json'), 'w'), indent=1)
    nets = sorted({t['net'] for t in rm_t} | {v['net'] for v in rm_v})
    print('ripped %d tracks, %d vias (%d columns) on %d nets: %s' % (len(rm_t), len(rm_v), len(cols), len(nets), ', '.join(nets)))
    oc = C.open_count(C.islands(M))
    print('open connections now: %d on %d nets' % (sum(oc.values()), len(oc)))
    for n, k in sorted(oc.items()):
        print('  %-12s %d' % (n, k))


if __name__ == '__main__':
    main()
