"""Rev 2 (2026-11-11, user request): X1 and X4 move 2.54 mm west, X2 pads 10 (CHAN7) and 30 (CHAN20) move 10.16 mm
east, so each X2 row splits 10 + 10 around a 12.70 mm landing centred on x 30.48.

    python tools/route/rev2/rev2_prep.py <base_model.json> <out_dir>

Writes base_moved.json (pads moved, nothing ripped: the route_check base), model.json (moved and ripped: the router
input), rip.json ({remove, remove_vias}) and moves.json (what the Altium script must do).
Rip rules
  1. every track / via of a moved pad's signal net (not GND / VCC3V3) inside WINDOW;
  2. every track of ANY other net, on a layer of a new land, within CLEAR + SLACK of that land (through-hole lands:
     all six layers), and every via whose span shares a layer with that land and comes that close;
  3. GND / VCC3V3 tracks ending on an old land of a moved pad, and vias of those nets inside an old land;
  4. every via of the same column (same net and x, y) as a ripped via; tracks left dangling are pruned later by
     compose_plan / prune_stubs.
"""
import json
import math
import os
import sys

STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
PLANE = {'GND', 'VCC3V3'}
CLEAR, SLACK = 0.09, 0.03
WINDOW = [17.0, 0.0, 46.0, 25.4]
MOVES = {'X1': (-2.54, 0.0), 'X4': (-2.54, 0.0),
         # X1's moved mounting holes land on these Bottom parts (MH1 on U10 pad 6, MH2 on R86/R84); place_u10d.py
         # and place_search.py picked the smallest moves that clear them with no power copper ripped
         'U10': (-1.3, -0.05), 'R96': (-0.9, 1.2), 'R84': (-1.7, 0.6), 'R86': (-1.7, 0.6)}
PAD_MOVES = {('X2', '10'): (10.16, 0.0), ('X2', '30'): (10.16, 0.0)}


def pad_layers(p):
    return STACK if p['drill'] else p['layers']


def rect_gap(p, x, y, r):
    dx = max(abs(x - p['x']) - p['w'] / 2, 0)
    dy = max(abs(y - p['y']) - p['h'] / 2, 0)
    return math.hypot(dx, dy) - r


def seg_pt(px, py, t):
    x1, y1, x2, y2 = t['x1'], t['y1'], t['x2'], t['y2']
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    k = 0 if L2 == 0 else max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / L2))
    return math.hypot(px - x1 - k * dx, py - y1 - k * dy)


def track_rect_gap(t, p):
    # sample the track centreline (fine enough for a rip decision: 0.05 mm steps)
    L = math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1'])
    n = max(1, int(L / 0.05))
    return min(rect_gap(p, t['x1'] + (t['x2'] - t['x1']) * k / n, t['y1'] + (t['y2'] - t['y1']) * k / n, t['w'] / 2)
               for k in range(n + 1))


def main():
    M = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    inwin = lambda x, y: WINDOW[0] <= x <= WINDOW[2] and WINDOW[1] <= y <= WINDOW[3]  # noqa: E731
    old, new = [], []
    for p in M['pads']:
        d = MOVES.get(p['ref']) or PAD_MOVES.get((p['ref'], p['pad']))
        if d:
            old.append(dict(p))
            p['x'] = round(p['x'] + d[0], 4)
            p['y'] = round(p['y'] + d[1], 4)
            new.append(p)
    json.dump(M, open(os.path.join(out, 'base_moved.json'), 'w'))
    sig = {p['net'] for p in new if p['net'] and p['net'] not in PLANE}
    rm_t, rm_v = set(), set()
    for i, t in enumerate(M['tracks']):
        if t['net'] in sig and (inwin(t['x1'], t['y1']) or inwin(t['x2'], t['y2'])):
            rm_t.add(i)
            continue
        for p in new:
            if t['net'] == p['net'] or t['layer'] not in pad_layers(p):
                continue
            if t['layer'] in ('L2-GND', 'L5-VCC3V3') and t['net'] in PLANE:
                continue
            if track_rect_gap(t, p) < CLEAR + SLACK:
                rm_t.add(i)
                break
        else:
            if t['net'] in PLANE:
                for p in old:
                    if p['net'] == t['net'] and t['layer'] in pad_layers(p) and (
                            rect_gap(p, t['x1'], t['y1'], 0) <= 0 or rect_gap(p, t['x2'], t['y2'], 0) <= 0):
                        rm_t.add(i)
                        break
    for i, v in enumerate(M['vias']):
        if v['net'] in sig and inwin(v['x'], v['y']):
            rm_v.add(i)
            continue
        for p in new:
            if not set(v['span']) & set(pad_layers(p)):
                continue
            if v['net'] != p['net'] and rect_gap(p, v['x'], v['y'], v['size'] / 2) < CLEAR + SLACK:
                rm_v.add(i)
                break
            if p['drill'] and math.hypot(v['x'] - p['x'], v['y'] - p['y']) - v['hole'] / 2 - p['drill'] / 2 < 0.24:
                rm_v.add(i)
                break
        else:
            if v['net'] in PLANE:
                for p in old:
                    if p['net'] == v['net'] and rect_gap(p, v['x'], v['y'], 0) <= 0:
                        rm_v.add(i)
                        break
    cols = {(M['vias'][i]['net'], round(M['vias'][i]['x'], 4), round(M['vias'][i]['y'], 4)) for i in rm_v}
    for i, v in enumerate(M['vias']):
        if (v['net'], round(v['x'], 4), round(v['y'], 4)) in cols:
            rm_v.add(i)
    rip = {'remove': [M['tracks'][i] for i in sorted(rm_t)], 'remove_vias': [M['vias'][i] for i in sorted(rm_v)]}
    M['tracks'] = [t for i, t in enumerate(M['tracks']) if i not in rm_t]
    M['vias'] = [v for i, v in enumerate(M['vias']) if i not in rm_v]
    json.dump(M, open(os.path.join(out, 'model.json'), 'w'))
    json.dump(rip, open(os.path.join(out, 'rip.json'), 'w'), indent=0)
    json.dump({'parts': {k: list(v) for k, v in MOVES.items()},
               'pads': [{'ref': r, 'pad': n, 'dx': d[0], 'dy': d[1]} for (r, n), d in PAD_MOVES.items()]},
              open(os.path.join(out, 'moves.json'), 'w'), indent=1)
    nets = {}
    for t in rip['remove']:
        nets[t['net']] = nets.get(t['net'], 0) + 1
    for v in rip['remove_vias']:
        nets[v['net']] = nets.get(v['net'], 0) + 1
    print('ripped', len(rm_t), 'tracks,', len(rm_v), 'vias; nets:', dict(sorted(nets.items(), key=lambda kv: -kv[1])))


if __name__ == '__main__':
    main()
