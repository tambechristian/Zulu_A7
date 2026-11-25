"""reseed_orig.py PLAN ORIG MODEL OUT NET[,NET...]

For each net: drop that net's pieces from PLAN (seed copper) and add the ORIG-board
copper of the net that is not already present in MODEL (exact match)."""
import json
import sys

plan_fn, orig_fn, model_fn, out_fn, nets = sys.argv[1:6]
nets = set(nets.split(','))
plan = json.load(open(plan_fn))
orig = json.load(open(orig_fn))
model = json.load(open(model_fn))


def tk(t):
    return (t['net'], t['layer'], round(t['x1'], 4), round(t['y1'], 4), round(t['x2'], 4), round(t['y2'], 4))


def tk_rev(t):
    return (t['net'], t['layer'], round(t['x2'], 4), round(t['y2'], 4), round(t['x1'], 4), round(t['y1'], 4))


def vk(v):
    return (v['net'], round(v['x'], 4), round(v['y'], 4), tuple(sorted(v['span'])))


have_t = set(map(tk, model['tracks'])) | set(map(tk_rev, model['tracks']))
have_v = set(map(vk, model['vias']))

n_t0, n_v0 = len(plan['tracks']), len(plan['vias'])
# BBOX=x0,x1,y0,y1 limits both the dropped plan pieces and the restored original pieces to that area
bb = [float(s) for s in __import__('os').environ.get('BBOX', '').split(',') if s]


def inside(*pts):
    return not bb or all(bb[0] <= x <= bb[1] and bb[2] <= y <= bb[3] for x, y in pts)


def touches(*pts):
    return not bb or any(bb[0] <= x <= bb[1] and bb[2] <= y <= bb[3] for x, y in pts)


plan['tracks'] = [t for t in plan['tracks']
                  if not (t['net'] in nets and touches((t['x1'], t['y1']), (t['x2'], t['y2'])))]
plan['vias'] = [v for v in plan['vias'] if not (v['net'] in nets and touches((v['x'], v['y'])))]
print('dropped', n_t0 - len(plan['tracks']), 'tracks', n_v0 - len(plan['vias']), 'vias')

at = av = 0
for t in orig['tracks']:
    if t['net'] in nets and tk(t) not in have_t and inside((t['x1'], t['y1']), (t['x2'], t['y2'])):
        plan['tracks'].append(dict(t))
        at += 1
for v in orig['vias']:
    if v['net'] in nets and vk(v) not in have_v and inside((v['x'], v['y'])):
        plan['vias'].append({'net': v['net'], 'x': v['x'], 'y': v['y'], 'size': v['size'],
                             'hole': v['hole'], 'from': v['span'][0], 'to': v['span'][1]})
        av += 1
print('added', at, 'tracks', av, 'vias')
json.dump(plan, open(out_fn, 'w'))
