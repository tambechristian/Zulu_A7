"""U4 0.40 mm north (2026-11-19), so its SOIC body clears U1's BGA body (0.14 mm overlap, 0.24 at max tolerance).

    python tools/route/u4_move/prep.py <board model.json> <out dir> [dy]

Same method as tools/bodies_fix_prep.py (2026-11-14, U4 deferred then): U4's own fan-out is kept with a Top jog from
each old pad centre to the new one; other-net copper too close to a new pad or jog (0.09 mm, on Top) is ripped and
left for router.py. Writes model.json (router input), base_moved.json (for compose_plan / route_check) and rip.json.
"""
import json
import math
import os
import sys

TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, TOOLS)
import route_conn as C  # noqa: E402
from bodies_fix_prep import pad_pt, pad_seg  # noqa: E402

CLR = 0.09
ORIGIN = (43.5505, 21.3050)


def main():
    M = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    dy = float(sys.argv[3]) if len(sys.argv) > 3 else 0.40
    os.makedirs(out, exist_ok=True)
    old = [dict(p) for p in M['pads'] if p['ref'] == 'U4']
    for p in M['pads']:
        if p['ref'] == 'U4':
            p['y'] = round(p['y'] + dy, 4)
    json.dump(M, open(os.path.join(out, 'base_moved.json'), 'w'))
    new = [p for p in M['pads'] if p['ref'] == 'U4']
    jogs = []
    for p in old:
        ws = [t['w'] for t in M['tracks'] if t['net'] == p['net'] and t['layer'] == 'Top Layer' and
              any(abs(x - p['x']) < 1e-3 and abs(y - p['y']) < 1e-3 for x, y in ((t['x1'], t['y1']), (t['x2'], t['y2'])))]
        jogs.append({'net': p['net'], 'layer': 'Top Layer', 'w': min(ws + [p['h']]) if ws else 0.0762,
                     'x1': p['x'], 'y1': p['y'], 'x2': p['x'], 'y2': round(p['y'] + dy, 4)})
    rm_t, rm_v = [], []
    for p in new:
        for t in M['tracks']:
            if t['layer'] == 'Top Layer' and t['net'] != p['net'] and pad_seg(p, t) < t['w'] / 2 + CLR and t not in rm_t:
                rm_t.append(t)
        for v in M['vias']:
            if 'Top Layer' in v['span'] and v['net'] != p['net'] and pad_pt(p, v['x'], v['y']) < v['size'] / 2 + CLR and v not in rm_v:
                rm_v.append(v)
    for j in jogs:                         # a jog lies inside old+new pad, but check it all the same
        jp = {'x': j['x1'], 'y': (j['y1'] + j['y2']) / 2, 'w': j['w'], 'h': abs(j['y2'] - j['y1']) + j['w'], 'shape': 'rect'}
        for t in M['tracks']:
            if t['layer'] == 'Top Layer' and t['net'] != j['net'] and pad_seg(jp, t) < t['w'] / 2 + CLR and t not in rm_t:
                rm_t.append(t)
    # a via that goes: also the Top/inner stubs it fed are left for the router; same-span stack partners go with it
    for v in list(rm_v):
        for w in M['vias']:
            if w is not v and w not in rm_v and abs(w['x'] - v['x']) < 1e-4 and abs(w['y'] - v['y']) < 1e-4 and w['net'] == v['net']:
                rm_v.append(w)
    ids_t, ids_v = {id(t) for t in rm_t}, {id(v) for v in rm_v}
    M['tracks'] = [t for t in M['tracks'] if id(t) not in ids_t] + jogs
    M['vias'] = [v for v in M['vias'] if id(v) not in ids_v]
    move = {'ref': 'U4', 'x': ORIGIN[0], 'y': round(ORIGIN[1] + dy, 4), 'dx': 0.0, 'dy': dy,
            'pad1': [43.85, round(21.305 + dy, 4)], 'pad_xy': {p['pad']: [p['x'], p['y']] for p in new}}
    json.dump(M, open(os.path.join(out, 'model.json'), 'w'))
    json.dump({'remove': rm_t, 'remove_vias': rm_v, 'moves': [move], 'jogs': jogs}, open(os.path.join(out, 'rip.json'), 'w'), indent=1)
    nets = sorted({o['net'] for o in rm_t + rm_v})
    print('dy %.2f: removed %d tracks, %d vias on %d nets: %s' % (dy, len(rm_t), len(rm_v), len(nets), nets))
    oc = C.open_count(C.islands(M))
    print('open connections now: %d on %d nets: %s' % (sum(oc.values()), len(oc), dict(oc)))


if __name__ == '__main__':
    main()
