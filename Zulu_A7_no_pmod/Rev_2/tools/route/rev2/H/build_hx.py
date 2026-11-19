"""build_hx.py <model_in.json> <seed_in.json> <model_out.json> <seed_out.json> <step.json> [<step.json> ...]
Strategy H model builder (build_h2.py for several steps). Each step is {tracks, vias, remove, remove_vias, drop_seed}:
remove/remove_vias leave the model (board copper), tracks/vias join it as FIXED copper, drop_seed items leave the seed,
and every seed track / via that clashes (exactly, router rules) with any step's copper leaves the seed too. A step with
only remove/remove_vias (an xrip file) just takes board copper away. Writes <seed_out>.test.json (seed + all step
copper, all step removals) for route_check against model_in."""
import json
import math
import sys

T = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools'
sys.path.insert(0, T)
import route_conn as C  # noqa: E402
import router as R  # noqa: E402
import compose_plan as CP  # noqa: E402

STACK = R.STACK


def span(v):
    return v['span'] if 'span' in v else STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]


M = json.load(open(sys.argv[1]))
seed = json.load(open(sys.argv[2]))
steps = [json.load(open(f)) for f in sys.argv[5:]]
hand_t = [t for s in steps for t in s.get('tracks', [])]
hand_v = [v for s in steps for v in s.get('vias', [])]
rm_t = [t for s in steps for t in s.get('remove', [])]
rm_v = [v for s in steps for v in s.get('remove_vias', [])]
rt = {CP.tkey(t) for t in rm_t}
rv = {CP.vkey(v) for v in rm_v}
n0 = (len(M['tracks']), len(M['vias']))
M['tracks'] = [t for t in M['tracks'] if CP.tkey(t) not in rt] + [dict(t) for t in hand_t]
M['vias'] = [v for v in M['vias'] if CP.vkey(v) not in rv] + [dict(v, span=span(v)) for v in hand_v]
print('model tracks %d -> %d, vias %d -> %d' % (n0[0], len(M['tracks']), n0[1], len(M['vias'])))
json.dump(M, open(sys.argv[3], 'w'))
dk = {CP.tkey(t) for s in steps for t in s.get('drop_seed', {}).get('tracks', [])} | rt
dv = {CP.vkey(v) for s in steps for v in s.get('drop_seed', {}).get('vias', [])} | rv


def clash_track(t):
    for h in hand_t:
        if h['layer'] == t['layer'] and h['net'] != t['net'] and \
                C.seg_seg((t['x1'], t['y1'], t['x2'], t['y2']), (h['x1'], h['y1'], h['x2'], h['y2'])) - t['w'] / 2 - h['w'] / 2 \
                < max(R.clearance(t['net'], t['layer']), R.clearance(h['net'], h['layer'])) - 1e-4:
            return True
    for v in hand_v:
        if t['layer'] in span(v) and v['net'] != t['net'] and \
                C.seg_dist(t['x1'], t['y1'], t['x2'], t['y2'], v['x'], v['y']) - t['w'] / 2 - v['size'] / 2 < R.CLEAR - 1e-4:
            return True
    return False


def clash_via(v):
    sp = span(v)
    for h in hand_t:
        if h['layer'] in sp and h['net'] != v['net'] and \
                C.seg_dist(h['x1'], h['y1'], h['x2'], h['y2'], v['x'], v['y']) - h['w'] / 2 - v['size'] / 2 < R.CLEAR - 1e-4:
            return True
    for o in hand_v:
        so = span(o)
        d = math.hypot(o['x'] - v['x'], o['y'] - v['y'])
        if set(so) & set(sp) and o['net'] != v['net'] and d - o['size'] / 2 - v['size'] / 2 < R.CLEAR - 1e-4:
            return True
        if set(so) & set(sp) and d > 1e-6 and d - o['hole'] / 2 - v['hole'] / 2 < R.HOLE_HOLE - 1e-4:
            return True
    return False


st, sv, drop = [], [], []
for t in seed['tracks']:
    if CP.tkey(t) in dk or clash_track(t):
        drop.append(('track', t['net'], t['layer'], t['x1'], t['y1'], t['x2'], t['y2']))
    else:
        st.append(t)
for v in seed['vias']:
    if CP.vkey(v) in dv or clash_via(v):
        drop.append(('via', v['net'], v['x'], v['y'], span(v)[0], span(v)[-1]))
    else:
        sv.append(v)
for d in drop:
    print('  drop', d)
json.dump({'tracks': st, 'vias': sv, 'remove': [], 'remove_vias': []}, open(sys.argv[4], 'w'), indent=0)
json.dump({'tracks': st + hand_t, 'vias': sv + hand_v, 'remove': rm_t, 'remove_vias': rm_v},
          open(sys.argv[4].replace('.json', '.test.json'), 'w'), indent=0)
print('seed: %d -> %d tracks, %d -> %d vias' % (len(seed['tracks']), len(st), len(seed['vias']), len(sv)))
