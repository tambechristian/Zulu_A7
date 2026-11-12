"""build_h2.py <hand.json> <seed_in.json> <model_out.json> <seed_out.json> [model_in.json (default model_H.json)]
Strategy H, second model: model_H.json minus the hand step's base removals plus its copper as FIXED model copper;
the seed plan minus the hand step's drop_seed items and minus every seed track / via that now clashes (exactly, as
route_check judges) with the hand copper. Also writes <seed_out>.test.json (seed + hand, the hand removals) for a
route_check against model_H.json."""
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


hand = json.load(open(sys.argv[1]))
seed = json.load(open(sys.argv[2]))
M = json.load(open(sys.argv[5] if len(sys.argv) > 5 else 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools/route/rev2/H/model_H.json'))
rt = {CP.tkey(t) for t in hand['remove']}
rv = {CP.vkey(v) for v in hand['remove_vias']}
n0 = (len(M['tracks']), len(M['vias']))
M['tracks'] = [t for t in M['tracks'] if CP.tkey(t) not in rt] + [dict(t) for t in hand['tracks']]
M['vias'] = [v for v in M['vias'] if CP.vkey(v) not in rv] + [dict(v, span=span(v)) for v in hand['vias']]
print('model tracks %d -> %d, vias %d -> %d' % (n0[0], len(M['tracks']), n0[1], len(M['vias'])))
json.dump(M, open(sys.argv[3], 'w'))
ds = hand.get('drop_seed', {'tracks': [], 'vias': []})
dk = {CP.tkey(t) for t in ds['tracks']}
dv = {(v['net'], round(v['x'], 4), round(v['y'], 4), span(v)[0], span(v)[-1]) for v in ds['vias']}


def gap_seg_seg(a, b):
    return C.seg_seg((a['x1'], a['y1'], a['x2'], a['y2']), (b['x1'], b['y1'], b['x2'], b['y2'])) - a['w'] / 2 - b['w'] / 2


def clash_track(t):
    for h in hand['tracks']:
        if h['layer'] == t['layer'] and h['net'] != t['net'] and \
                gap_seg_seg(t, h) < max(R.clearance(t['net'], t['layer']), R.clearance(h['net'], h['layer'])) - 1e-4:
            return True
    for v in hand['vias']:
        if t['layer'] in span(v) and v['net'] != t['net'] and \
                C.seg_dist(t['x1'], t['y1'], t['x2'], t['y2'], v['x'], v['y']) - t['w'] / 2 - v['size'] / 2 < R.CLEAR - 1e-4:
            return True
    return False


def clash_via(v):
    sp = span(v)
    for h in hand['tracks']:
        if h['layer'] in sp and h['net'] != v['net'] and \
                C.seg_dist(h['x1'], h['y1'], h['x2'], h['y2'], v['x'], v['y']) - h['w'] / 2 - v['size'] / 2 < R.CLEAR - 1e-4:
            return True
    for o in hand['vias']:
        so = span(o)
        d = math.hypot(o['x'] - v['x'], o['y'] - v['y'])
        if set(so) & set(sp) and o['net'] != v['net'] and d - o['size'] / 2 - v['size'] / 2 < R.CLEAR - 1e-4:
            return True
        if set(so) & set(sp) and d > 1e-6 and d - o['hole'] / 2 - v['hole'] / 2 < R.HOLE_HOLE - 1e-4:
            return True
    return False


st, sv = [], []
drop = []
for t in seed['tracks']:
    if CP.tkey(t) in dk or clash_track(t):
        drop.append(('track', t['net'], t['layer'], t['x1'], t['y1'], t['x2'], t['y2']))
    else:
        st.append(t)
for v in seed['vias']:
    if (v['net'], round(v['x'], 4), round(v['y'], 4), span(v)[0], span(v)[-1]) in dv or clash_via(v):
        drop.append(('via', v['net'], v['x'], v['y'], span(v)[0], span(v)[-1]))
    else:
        sv.append(v)
for d in drop:
    print('  drop', d)
out = {'tracks': st, 'vias': sv, 'remove': [], 'remove_vias': []}
json.dump(out, open(sys.argv[4], 'w'), indent=0)
json.dump({'tracks': st + hand['tracks'], 'vias': sv + hand['vias'], 'remove': hand['remove'],
           'remove_vias': hand['remove_vias']}, open(sys.argv[4].replace('.json', '.test.json'), 'w'), indent=0)
print('seed: %d -> %d tracks, %d -> %d vias' % (len(seed['tracks']), len(st), len(seed['vias']), len(sv)))
