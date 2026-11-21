"""rip_region.py <seed_in.json> <seed_out.json> NET[,NET] x0 y0 x1 y1
Removes the seed (router) tracks and vias of the given nets that touch the window (any sampled centreline point or
the via centre inside it), so those nets open there and a later router pass can re-route them after others."""
import json
import sys

S = json.load(open(sys.argv[1]))
nets = set(sys.argv[3].split(','))
x0, y0, x1, y1 = map(float, sys.argv[4:8])


def inside(x, y):
    return x0 <= x <= x1 and y0 <= y <= y1


def touches(t):
    for k in range(21):
        if inside(t['x1'] + (t['x2'] - t['x1']) * k / 20, t['y1'] + (t['y2'] - t['y1']) * k / 20):
            return True
    return False


kt = [t for t in S['tracks'] if not (t['net'] in nets and touches(t))]
kv = [v for v in S['vias'] if not (v['net'] in nets and inside(v['x'], v['y']))]
print('ripped %d tracks, %d vias' % (len(S['tracks']) - len(kt), len(S['vias']) - len(kv)))
json.dump(dict(S, tracks=kt, vias=kv), open(sys.argv[2], 'w'), indent=0)
