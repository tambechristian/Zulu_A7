"""make_seeds.py <transplant_b.json> <after_b.json> <nets,...> <xmin> <tag>

Turn the transplanted SOURCE copper of the given nets east of x >= xmin (a track counts when either end is) into
router SEEDS: rippable router copper that router.py --seed re-routes from the live islands when a Pmod net needs the
room. Writes B/seeds_<tag>.json (router plan format), B/model_<tag>.json (after_b minus the seeds) and
B/transplant_<tag>.json (the transplant plan minus the seeds; the router output carries the seeds that survive)."""
import json
import os
import sys

BDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']


def span(v):
    return v['span'] if 'span' in v else STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]


def tk(t):
    e = sorted([(round(t['x1'], 4), round(t['y1'], 4)), (round(t['x2'], 4), round(t['y2'], 4))])
    return (t['net'], t['layer'], round(t['w'], 4)) + e[0] + e[1]


def vk(v):
    s = span(v)
    return (v['net'], round(v['x'], 4), round(v['y'], 4), s[0], s[-1])


def main():
    P = json.load(open(sys.argv[1]))
    M = json.load(open(sys.argv[2]))
    nets = set(sys.argv[3].split(','))
    xmin = float(sys.argv[4])
    tag = sys.argv[5]
    st = [t for t in P['tracks'] if t['net'] in nets and max(t['x1'], t['x2']) >= xmin]
    sv = [v for v in P['vias'] if v['net'] in nets and v['x'] >= xmin]
    stk, svk = {tk(t) for t in st}, {vk(v) for v in sv}
    seeds = {'tracks': [dict(t) for t in st],
             'vias': [{'net': v['net'], 'x': v['x'], 'y': v['y'], 'size': v['size'], 'hole': v['hole'],
                       'from': span(v)[0], 'to': span(v)[-1]} for v in sv]}
    model = dict(M)
    model['tracks'] = [t for t in M['tracks'] if tk(t) not in stk]
    model['vias'] = [v for v in M['vias'] if vk(v) not in svk]
    assert len(M['tracks']) - len(model['tracks']) == len(st), (len(M['tracks']) - len(model['tracks']), len(st))
    assert len(M['vias']) - len(model['vias']) == len(sv), (len(M['vias']) - len(model['vias']), len(sv))
    tp = dict(P)
    tp['tracks'] = [t for t in P['tracks'] if tk(t) not in stk]
    tp['vias'] = [v for v in P['vias'] if vk(v) not in svk]
    tp['_meta'] = dict(P.get('_meta', {}), seeded_to_router={'nets': sorted(nets), 'xmin': xmin, 'tracks': len(st),
                                                                 'vias': len(sv)})
    json.dump(seeds, open(os.path.join(BDIR, 'seeds_%s.json' % tag), 'w'), indent=0)
    json.dump(model, open(os.path.join(BDIR, 'model_%s.json' % tag), 'w'))
    json.dump(tp, open(os.path.join(BDIR, 'transplant_%s.json' % tag), 'w'), indent=1)
    print('seeds_%s: %d tracks, %d vias of %s east of x %.2f' % (tag, len(st), len(sv), sorted(nets), xmin))


if __name__ == '__main__':
    main()
