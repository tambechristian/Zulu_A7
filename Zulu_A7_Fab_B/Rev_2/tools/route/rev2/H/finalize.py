"""finalize.py <composed_plan.json> <out_plan.json>
Drops every remove/add pair that cancels exactly (un-ripped seed copper the router kept: the board already has it),
then prints the plan statistics: tracks / vias added and removed (vias by type), added track length per layer."""
import json
import math
import sys

STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']


def span(v):
    return v['span'] if 'span' in v else STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]


def tkey(t):
    a, b = (round(t['x1'], 4), round(t['y1'], 4)), (round(t['x2'], 4), round(t['y2'], 4))
    return (t['net'], t['layer'], min(a, b), max(a, b), round(t['w'], 4))


def vkey(v):
    sp = span(v)
    return (v['net'], round(v['x'], 4), round(v['y'], 4), sp[0], sp[-1], round(v['size'], 3), round(v['hole'], 3))


def vtype(v):
    sp = span(v)
    if sp == STACK:
        return 'through 0.35/0.20'
    if sp == ['L3-SIG', 'L4-SIG']:
        return 'buried L3-L4'
    return 'laser %s-%s' % (sp[0].split('-')[0].replace(' Layer', ''), sp[-1].split('-')[0].replace(' Layer', ''))


def main():
    P = json.load(open(sys.argv[1]))
    rt = {}
    for t in P['remove']:
        rt.setdefault(tkey(t), []).append(t)
    rv = {}
    for v in P['remove_vias']:
        rv.setdefault(vkey(v), []).append(v)
    add_t, add_v, ct, cv = [], [], 0, 0
    for t in P['tracks']:
        k = tkey(t)
        if rt.get(k):
            rt[k].pop()
            ct += 1
        else:
            add_t.append(t)
    for v in P['vias']:
        k = vkey(v)
        if rv.get(k):
            rv[k].pop()
            cv += 1
        else:
            add_v.append(v)
    out = dict(P, tracks=add_t, vias=add_v, remove=[t for ts in rt.values() for t in ts],
               remove_vias=[v for vs in rv.values() for v in vs])
    json.dump(out, open(sys.argv[2], 'w'), indent=1)
    print('cancelled %d track and %d via remove/add pairs' % (ct, cv))
    print('final plan: remove %d tracks + %d vias, add %d tracks + %d vias' % (
        len(out['remove']), len(out['remove_vias']), len(add_t), len(add_v)))
    for tag, vs in (('added', add_v), ('removed', out['remove_vias'])):
        c = {}
        for v in vs:
            c[vtype(v)] = c.get(vtype(v), 0) + 1
        print('vias %s by type: %s' % (tag, dict(sorted(c.items()))))
    L = {}
    for t in add_t:
        L[t['layer']] = L.get(t['layer'], 0) + math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1'])
    Lr = {}
    for t in out['remove']:
        Lr[t['layer']] = Lr.get(t['layer'], 0) + math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1'])
    print('added track length %.2f mm %s' % (sum(L.values()), {k: round(v, 2) for k, v in L.items()}))
    print('removed track length %.2f mm %s' % (sum(Lr.values()), {k: round(v, 2) for k, v in Lr.items()}))


if __name__ == '__main__':
    main()
