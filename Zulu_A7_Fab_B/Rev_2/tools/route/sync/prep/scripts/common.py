"""Shared helpers for the Fab B Rev 2 <- no_pmod Rev 2 transplant prep (route-model format, tools/route_model.py)."""
import json
import math
import os
from collections import Counter, defaultdict

PREP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(PREP)))
MODELS = os.path.join(PREP, 'models')
STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
CHAIN = ['22ee1dc', '51ffba0', '06d9f27', '04819de', '3b1817d', '3e4ee8c', '427960e']


def load(name):
    return json.load(open(os.path.join(MODELS, name + '.json')))


def r4(v):
    return round(v, 4)


def tkey(t):
    e = sorted([(r4(t['x1']), r4(t['y1'])), (r4(t['x2']), r4(t['y2']))])
    return ('T', t['net'], t['layer'], r4(t['w'])) + e[0] + e[1]


def vkey(v):
    sp = v['span'] if 'span' in v else STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]
    return ('V', v['net'], r4(v['x']), r4(v['y']), r4(v['size']), r4(v['hole']), sp[0], sp[-1])


def pkey(p):
    return ('P', p['ref'], p['pad'], r4(p['x']), r4(p['y']), r4(p['w']), r4(p['h']), p['shape'], tuple(p['layers']),
            r4(p['drill']), p['net'])


def objs(M):
    """copper objects (tracks + vias) with keys"""
    out = []
    for t in M['tracks']:
        out.append(('T', tkey(t), t))
    for v in M['vias']:
        out.append(('V', vkey(v), v))
    return out


def mdiff(A, B):
    """multiset diff of [(kind, key, obj)]: (in A not B, in B not A)"""
    ca = Counter(k for _, k, _ in A)
    cb = Counter(k for _, k, _ in B)
    ra, rb = ca - cb, cb - ca
    out_a, out_b = [], []
    used = Counter()
    for kd, k, o in A:
        if used[k] < ra[k]:
            used[k] += 1
            out_a.append((kd, k, o))
    used = Counter()
    for kd, k, o in B:
        if used[k] < rb[k]:
            used[k] += 1
            out_b.append((kd, k, o))
    return out_a, out_b


def span(v):
    return v['span'] if 'span' in v else STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]


def plan_via(v):
    sp = span(v)
    return {'net': v['net'], 'x': r4(v['x']), 'y': r4(v['y']), 'size': r4(v['size']), 'hole': r4(v['hole']),
            'from': sp[0], 'to': sp[-1]}


def plan_rvia(v):
    sp = span(v)
    return {'net': v['net'], 'x': r4(v['x']), 'y': r4(v['y']), 'size': r4(v['size']), 'hole': r4(v['hole']),
            'span': list(sp)}


def plan_track(t):
    return {k: (r4(t[k]) if k not in ('net', 'layer') else t[k]) for k in ('net', 'layer', 'w', 'x1', 'y1', 'x2', 'y2')}


def desc(kd, o):
    if kd == 'T':
        return 'T %s %s w%.4f (%.4f,%.4f)-(%.4f,%.4f)' % (o['layer'], o['net'], o['w'], o['x1'], o['y1'], o['x2'], o['y2'])
    if kd == 'V':
        sp = span(o)
        return 'V %s (%.4f,%.4f) %.3f/%.3f %s>%s' % (o['net'], o['x'], o['y'], o['size'], o['hole'], sp[0], sp[-1])
    return 'P %s-%s %s (%.4f,%.4f) %gx%g %s' % (o['ref'], o['pad'], o['net'], o['x'], o['y'], o['w'], o['h'], o['shape'])


def centre(kd, o):
    if kd == 'T':
        return ((o['x1'] + o['x2']) / 2, (o['y1'] + o['y2']) / 2)
    return (o['x'], o['y'])


def dump(obj, name):
    json.dump(obj, open(os.path.join(PREP, name), 'w'), indent=1)
