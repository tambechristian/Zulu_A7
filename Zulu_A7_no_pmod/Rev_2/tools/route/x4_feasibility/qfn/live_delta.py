"""Copper delta between the live (edge-tab) board model and the judged notchless board.

    python live_delta.py LIVE_MODEL.json FINAL_BOARD.json OUT_PLAN.json

Tracks and vias are matched as multisets (net, layer/span, size, ends either way round) within TOL mm. The plan has
remove / remove_vias for live objects absent from the final board and tracks / vias for final objects absent from the
live board. It also proves that every removal selects exactly one live object by the emit_copper matching rule, and
that no object that stays is selected by a removal.
"""
import json
import sys
from collections import defaultdict

TOL = 0.002


def close(a, b):
    return abs(a - b) <= TOL


def tmatch(a, b):
    if a['net'] != b['net'] or a['layer'] != b['layer'] or not close(a['w'], b['w']):
        return False
    return ((close(a['x1'], b['x1']) and close(a['y1'], b['y1']) and close(a['x2'], b['x2']) and close(a['y2'], b['y2'])) or
            (close(a['x1'], b['x2']) and close(a['y1'], b['y2']) and close(a['x2'], b['x1']) and close(a['y2'], b['y1'])))


def vmatch(a, b):
    return (a['net'] == b['net'] and close(a['x'], b['x']) and close(a['y'], b['y']) and close(a['hole'], b['hole']) and
            close(a['size'], b['size']) and a['span'][0] == b['span'][0] and a['span'][-1] == b['span'][-1])


def bucket(items, key):
    d = defaultdict(list)
    for i in items:
        d[key(i)].append(i)
    return d


def multiset_diff(old, new, match, key):
    """Objects of old with no partner in new, and objects of new with no partner in old (each partner used once)."""
    nb = bucket(new, key)
    used = set()
    gone = []
    for o in old:
        hit = None
        for dk in neighbours(key(o)):
            for n in nb.get(dk, []):
                if id(n) not in used and match(o, n):
                    hit = n
                    break
            if hit:
                break
        if hit is None:
            gone.append(o)
        else:
            used.add(id(hit))
    fresh = [n for n in new if id(n) not in used]
    return gone, fresh


def neighbours(k):
    net, gx, gy = k
    return [(net, gx + i, gy + j) for i in (-1, 0, 1) for j in (-1, 0, 1)]


def tkey(t):
    return (t['net'], int(min(t['x1'], t['x2']) // 1), int(min(t['y1'], t['y2']) // 1))


def vkey(v):
    return (v['net'], int(v['x'] // 1), int(v['y'] // 1))


def selects(items, pred):
    return [i for i in items if pred(i)]


def main():
    live, final = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
    # track ends can sit in different grid cells than their key; widen the key to the track's low corner and probe
    # the neighbouring cells (TOL << 1 mm, so a 1 mm grid with +-1 probing always finds a partner)
    rt, nt = multiset_diff(live['tracks'], final['tracks'], tmatch, tkey)
    rv, nv = multiset_diff(live['vias'], final['vias'], vmatch, vkey)
    print('tracks: live %d final %d -> remove %d add %d' % (len(live['tracks']), len(final['tracks']), len(rt), len(nt)))
    print('vias:   live %d final %d -> remove %d add %d' % (len(live['vias']), len(final['vias']), len(rv), len(nv)))

    # emit_copper selects a live object by the same predicate, so each removal must select exactly its own object
    ltb, lvb = bucket(live['tracks'], lambda t: t['net']), bucket(live['vias'], lambda v: v['net'])
    stay_t = [t for t in live['tracks'] if all(t is not r for r in rt)]
    bad = 0
    rts = {id(r) for r in rt}
    rvs = {id(r) for r in rv}
    for r in rt:
        sel = [t for t in ltb[r['net']] if tmatch(r, t)]
        if len(sel) != 1 or id(sel[0]) not in rts:
            bad += 1
            print('  track removal not unique:', r, 'selects', len(sel))
    for r in rv:
        sel = [v for v in lvb[r['net']] if vmatch(r, v)]
        if len(sel) != 1 or id(sel[0]) not in rvs:
            bad += 1
            print('  via removal not unique:', r, 'selects', len(sel))
    print('ambiguous removals:', bad)

    plan = {'remove': rt, 'remove_vias': rv,
            'tracks': nt, 'vias': [dict(v, **{'from': v['span'][0], 'to': v['span'][-1]}) for v in nv]}
    json.dump(plan, open(sys.argv[3], 'w'), indent=0)
    print('wrote', sys.argv[3])


if __name__ == '__main__':
    main()
