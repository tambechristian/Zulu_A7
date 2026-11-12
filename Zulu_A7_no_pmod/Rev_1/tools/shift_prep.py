"""Fab B: move a group of Top parts and rip their pocket in the router model (generalises btn_spread_prep.py).

    python tools/shift_prep.py <base_model.json> <out_dir> <moves.json>

moves.json: {"window": [x0, y0, x1, y1], "moves": [{"ref", "x", "y", "dx", "dy"}]}  (x, y = component origin BEFORE)
What is ripped
  1. every track / via of a moved part's signal net (not GND / VCC3V3) inside the window
  2. every Top track, and every via whose span includes Top, of ANY other net within CLEAR + SLACK of a new land
  3. plane-net tracks ending on an old land of a moved part, and plane-net vias inside an old land
  4. every via of the same column (same net, x, y) as a ripped via
Writes model.json (moved, ripped), base_moved.json (moved, not ripped: the route_check base) and rip.json.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import route_conn as C  # noqa: E402

CLEAR, SLACK = 0.09, 0.03
PLANE = {'GND', 'VCC3V3'}


def main():
    M = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    cfg = json.load(open(sys.argv[3]))
    W = cfg['window']
    mv = {m['ref']: m for m in cfg['moves']}
    os.makedirs(out, exist_ok=True)
    inwin = lambda x, y: W[0] <= x <= W[2] and W[1] <= y <= W[3]  # noqa: E731
    seg_in = lambda t: any(inwin(t['x1'] + (t['x2'] - t['x1']) * k / 16, t['y1'] + (t['y2'] - t['y1']) * k / 16)  # noqa: E731
                           for k in range(17))
    old = [dict(p) for p in M['pads'] if p['ref'] in mv]
    for p in M['pads']:
        if p['ref'] in mv:
            p['x'] = round(p['x'] + mv[p['ref']]['dx'], 4)
            p['y'] = round(p['y'] + mv[p['ref']]['dy'], 4)
    new = [p for p in M['pads'] if p['ref'] in mv]
    json.dump(M, open(os.path.join(out, 'base_moved.json'), 'w'))
    sig = {p['net'] for p in new} - PLANE - {''}
    on_old = lambda x, y, net: any(p['net'] == net and C.pad_point(p, x, y) < 1e-3 for p in old)  # noqa: E731
    rm_t = []
    for t in M['tracks']:
        if t['net'] in sig and seg_in(t):
            rm_t.append(t)
        elif t['layer'] == 'Top Layer' and any(
                t['net'] != p['net'] and C.pad_seg(p, (t['x1'], t['y1'], t['x2'], t['y2'])) - t['w'] / 2 < CLEAR + SLACK for p in new):
            rm_t.append(t)
        elif t['layer'] == 'Top Layer' and t['net'] in PLANE and (on_old(t['x1'], t['y1'], t['net']) or on_old(t['x2'], t['y2'], t['net'])):
            rm_t.append(t)
    cols = set()
    for v in M['vias']:
        key = (v['net'], round(v['x'], 3), round(v['y'], 3))
        if v['net'] in sig and inwin(v['x'], v['y']):
            cols.add(key)
        elif 'Top Layer' in v['span'] and any(
                v['net'] != p['net'] and C.pad_point(p, v['x'], v['y']) - v['size'] / 2 < CLEAR + SLACK for p in new):
            cols.add(key)
        elif 'Top Layer' in v['span'] and v['net'] in PLANE and any(
                p['net'] == v['net'] and C.pad_point(p, v['x'], v['y']) - v['size'] / 2 < 1e-3 for p in old):
            cols.add(key)
    rm_v = [v for v in M['vias'] if (v['net'], round(v['x'], 3), round(v['y'], 3)) in cols]
    it, iv = {id(t) for t in rm_t}, {id(v) for v in rm_v}
    M['tracks'] = [t for t in M['tracks'] if id(t) not in it]
    M['vias'] = [v for v in M['vias'] if id(v) not in iv]
    moves = [{'ref': r, 'dx': m['dx'], 'dy': m['dy'], 'x': round(m['x'] + m['dx'], 4), 'y': round(m['y'] + m['dy'], 4)}
             for r, m in mv.items()]
    json.dump(M, open(os.path.join(out, 'model.json'), 'w'))
    json.dump({'remove': rm_t, 'remove_vias': rm_v, 'moves': moves}, open(os.path.join(out, 'rip.json'), 'w'), indent=1)
    nets = sorted({t['net'] for t in rm_t} | {v['net'] for v in rm_v})
    print('ripped %d tracks, %d vias (%d columns) on %d nets: %s' % (len(rm_t), len(rm_v), len(cols), len(nets), ', '.join(nets)))
    oc = C.open_count(C.islands(M))
    print('open connections now: %d on %d nets: %s' % (sum(oc.values()), len(oc), oc))


if __name__ == '__main__':
    main()
