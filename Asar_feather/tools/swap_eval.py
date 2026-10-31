"""Measure every legal single ball swap for the open connections of a routing plan (2026-10-27).

For each open net X on a swappable U1 ball a, and each legal target ball b (an unconnected ball, or one carrying a
swappable net Y that is legal on a), the swap is applied to a copy of the board: X and Y lose every track and via
they own (their stage-1 fan-out stubs stay, re-netted with their balls), the pads swap nets, and the router then
joins the islands of X and Y, nearest first, with no rip-up. gain = (open connections of X and Y before) - (after).
XADC inputs move as a P/N pair, so those jobs swap two balls and re-route four nets. A no-swap job per net gives
the baseline the same budget would reach anyway.

    python tools/swap_eval.py <model.json> <plan.json> <stage1_model.json> --out swaps.json
        [--pops 1500000] [--procs 20] [--nets X,Y] [--targets nc|same|all]

As a module: swapped(Mx, fan, swaps) -> the model after a list of (ball_a, ball_b) swaps; fanout(S1) -> the
stage-1 copper per U1 ball; choose(results) -> a greedy disjoint set of the measured swaps with gain > 0.
"""
import argparse
import copy
import json
import math
import os
import sys
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import route_conn as C  # noqa: E402
import router as R  # noqa: E402
import swap_rules as W  # noqa: E402
from diagnose_open import with_plan  # noqa: E402

G = {}


def fanout(S1):
    """{ball: (tracks, vias)} -- the stage-1 copper of each U1 ball's own island (its escape stub and via)"""
    out = {}
    for net, gs in C.islands(S1).items():
        for g in gs:
            u1 = [S1['pads'][i]['pad'] for i in g['pads'] if S1['pads'][i]['ref'] == 'U1']
            if len(u1) == 1 and len(g['pads']) == 1 and (g['tracks'] or g['vias']):
                out[u1[0]] = ([S1['tracks'][i] for i in g['tracks']], [S1['vias'][i] for i in g['vias']])
    return out


def swapped(Mx, fan, swaps, side=False):
    """the model after the ball swaps [(a, b), ...]: nets of the swapped balls exchange, every track and via of
    those nets goes (side=True: only the island that holds each swapped ball loses its copper, the net's other
    islands keep theirs), and each ball keeps its own stage-1 stub under its new net (an unconnected ball has none)"""
    Ms = dict(Mx)
    Ms['pads'] = [dict(p) for p in Mx['pads']]
    pad_at = {p['pad']: p for p in Ms['pads'] if p['ref'] == 'U1'}
    pad_idx = {p['pad']: i for i, p in enumerate(Mx['pads']) if p['ref'] == 'U1'}
    cur = {b: p['net'] for b, p in pad_at.items()}      # the swaps apply in order: [(b, c), (a, b)] is a rotation
    touched = []
    for a, b in swaps:
        cur[a], cur[b] = cur[b], cur[a]
        touched += [a, b]
    touched = list(dict.fromkeys(touched))
    nets = {pad_at[b]['net'] for b in touched if pad_at[b]['net']}
    newnet = {b: cur[b] for b in touched}
    if side:
        isl = C.islands(Mx)
        drop_t, drop_v = set(), set()
        for ball in newnet:
            n = Mx['pads'][pad_idx[ball]]['net']
            for g in isl.get(n, []) if n else []:
                if pad_idx[ball] in g['pads']:
                    drop_t |= set(g['tracks'])
                    drop_v |= set(g['vias'])
        Ms['tracks'] = [t for i, t in enumerate(Mx['tracks']) if i not in drop_t]
        Ms['vias'] = [v for i, v in enumerate(Mx['vias']) if i not in drop_v]
    else:
        Ms['tracks'] = [t for t in Mx['tracks'] if t['net'] not in nets]
        Ms['vias'] = [v for v in Mx['vias'] if v['net'] not in nets]
    for ball, n in newnet.items():
        pad_at[ball]['net'] = n
        if n and ball in fan:
            Ms['tracks'] += [dict(t, net=n) for t in fan[ball][0]]
            Ms['vias'] += [dict(v, net=n) for v in fan[ball][1]]
    return Ms, nets


def centre(M, g):
    b = R.bbox(M, g)
    return (b[0] + b[2]) / 2, (b[1] + b[3]) / 2


MARGINS = (2.5, 6.0, 60.0)                             # the searches exhaust their pocket, so the budget is rarely the limit


def route_all(Ms, nets, pops, open_before=None):
    """join every island of these nets on the model, nearest first, no rip-up; returns {net: open after}.
    Stops early once a net stays open and every net still to route was closed before (the gain cannot be > 0)."""
    B = R.Board(Ms)
    Rt = R.Router(B, pops)
    isl = C.islands(Ms)
    for q, net in enumerate(nets):
        groups = [dict(g) for g in isl.get(net, [])]
        if len(groups) < 2:
            continue
        main_g, rest = groups[0], groups[1:]
        failed = False
        while rest:
            mc = centre(Ms, main_g)
            rest.sort(key=lambda g: math.dist(mc, centre(Ms, g)))
            gi = rest.pop(0)
            r = None
            for mg in MARGINS:
                win = R.window(B, [R.bbox(Ms, main_g), R.bbox(Ms, gi)], mg)
                r = Rt.route(net, R.island_mask(B, Ms, main_g, win), R.island_mask(B, Ms, gi, win), win)
                if r:
                    break
            if r:
                Rt.commit(net, *r)
                for k in ('pads', 'tracks', 'vias'):
                    main_g[k] = main_g[k] + gi[k]
            else:
                failed = True
        if failed and open_before is not None and not any(open_before.get(n, 0) for n in nets[q + 1:]):
            break
    Mz = dict(Ms)
    Mz['tracks'] = Ms['tracks'] + Rt.out_t
    Mz['vias'] = Ms['vias'] + [dict(v, span=R.STACK[R.STACK.index(v['from']):R.STACK.index(v['to']) + 1])
                               for v in Rt.out_v]
    oc = C.open_count(C.islands(Mz))
    return {n: oc.get(n, 0) for n in nets}, len(Rt.out_t), len(Rt.out_v)


def init(model, plan, stage1, pops, margins=None):
    global MARGINS
    if margins:
        MARGINS = tuple(margins)
    M = json.load(open(model))
    P = json.load(open(plan))
    G['Mx'] = with_plan(M, P)
    G['fan'] = fanout(json.load(open(stage1)))
    G['open'] = C.open_count(C.islands(G['Mx']))
    G['pops'] = pops


def job(swaps):
    Mx, fan = G['Mx'], G['fan']
    pad_at = {p['pad']: p['net'] for p in Mx['pads'] if p['ref'] == 'U1'}
    if swaps:
        Ms, nets = swapped(Mx, fan, swaps, side=True)
        nets = sorted(nets, key=lambda n: (n not in G['open'], n))
    else:
        return None
    before = sum(G['open'].get(n, 0) for n in nets)
    after, nt, nv = route_all(Ms, nets, G['pops'], G['open'])
    final = {p['pad']: p['net'] for p in Ms['pads'] if p['ref'] == 'U1'}
    touched = list(dict.fromkeys(b for sw in swaps for b in sw))
    return {'swaps': swaps,
            'moves': {b: [pad_at[b], final[b]] for b in touched},
            'before': before, 'after': after, 'gain': before - sum(after.values()), 'tracks': nt, 'vias': nv}


def candidates(Mx, opens, want, targets, reach=None):
    """reach: reach.json ({ball: {'net', 'reach': [nets whose far end the ball's pocket touches]}}); with it, a
    target ball must reach X's far end and X's ball must reach the far end of the net it takes over"""
    pad_at = {p['pad']: p['net'] for p in Mx['pads'] if p['ref'] == 'U1'}

    def can(net, ball):
        return reach is None or (ball in reach and net in reach[ball]['reach'])
    ball_of = {}
    for b, n in pad_at.items():
        if n and W.kind(n) != 'fixed' and n not in W.POWER:
            ball_of.setdefault(n, []).append(b)
    jobs = []
    seen = set()

    def add(sw):
        key = tuple(sorted(sw)) if len(sw) == 1 else tuple(sw)
        if key not in seen:
            seen.add(key)
            jobs.append(list(sw))
    done_pairs = set()
    for X in sorted(opens):
        if opens[X] <= 0 or W.kind(X) in ('fixed',) or X in W.POWER or (want and X not in want):
            continue
        balls = ball_of.get(X, [])
        if len(balls) != 1:
            continue
        a = balls[0]
        k = W.kind(X)
        if k == 'xadc':
            pair = X[:-1]
            if pair in done_pairs:
                continue
            done_pairs.add(pair)
            pa, na = ball_of.get(pair + 'P', [None])[0], ball_of.get(pair + 'N', [None])[0]
            if not pa or not na:
                continue
            add([(pa, pa)])                          # baseline: both nets re-routed in place
            pairs = {}
            for b, info in W.BALLS.items():
                p = W.ad_pair(b)
                if p:
                    pairs.setdefault(p[0], {})[p[1]] = b
            for adn, pn in pairs.items():
                if 'P' not in pn or 'N' not in pn or pn['P'] in (pa, na):
                    continue
                yp, yn = pad_at.get(pn['P'], ''), pad_at.get(pn['N'], '')
                if W.legal(pair + 'P', pn['P']) and W.legal(pair + 'N', pn['N']) and \
                        (not yp or (W.kind(yp) != 'fixed' and W.legal(yp, pa))) and \
                        (not yn or (W.kind(yn) != 'fixed' and W.legal(yn, na))):
                    add([(pa, pn['P']), (na, pn['N'])])
            continue
        if can(X, a):
            add([(a, a)])                            # baseline: X re-routed in place with this budget
        for b, info in W.BALLS.items():
            if b == a or b not in pad_at or not W.legal(X, b) or not can(X, b):
                continue
            Y = pad_at[b]
            if Y:
                if W.kind(Y) == 'fixed' or Y in W.POWER or not W.legal(Y, a) or len(ball_of.get(Y, [])) != 1:
                    continue
                if not can(Y, a):
                    continue
                if W.kind(Y) == 'xadc':
                    continue                          # a pair; handled from the XADC side only
                if targets == 'nc':
                    continue
                if targets == 'same' and not (W.kind(Y) == k or (k in ('io', 'header', 'clock') and
                                                               W.kind(Y) in ('io', 'header', 'clock'))):
                    continue
            add([(a, b)])
        if reach is None:
            continue
        # rotations: X takes b (net Y), Y moves to a spare ball c whose pocket reaches Y's far end, a is vacated
        for b, info in W.BALLS.items():
            if b == a or b not in pad_at or not W.legal(X, b) or not can(X, b):
                continue
            Y = pad_at[b]
            if not Y or W.kind(Y) in ('fixed', 'xadc') or Y in W.POWER or len(ball_of.get(Y, [])) != 1:
                continue
            for c in sorted(reach):
                if c in (a, b) or pad_at.get(c, 'x') or not W.legal(Y, c) or not can(Y, c):
                    continue
                add([(b, c), (a, b)])
    return jobs


def choose(results):
    """greedy: best gain first, disjoint balls and nets"""
    used_b, used_n, out = set(), set(), []
    for r in sorted((r for r in results if r and r['gain'] > 0), key=lambda r: (-r['gain'], r['vias'] + r['tracks'])):
        balls = {b for sw in r['swaps'] for b in sw}
        nets = {n for b in balls for n in r['moves'][b] if n}
        if balls & used_b or nets & used_n:
            continue
        used_b |= balls
        used_n |= nets
        out.append(r)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('model')
    ap.add_argument('plan')
    ap.add_argument('stage1')
    ap.add_argument('--out', default='')
    ap.add_argument('--pops', type=int, default=800000)
    ap.add_argument('--procs', type=int, default=20)
    ap.add_argument('--nets', default='')
    ap.add_argument('--targets', default='all', choices=['nc', 'same', 'all'])
    ap.add_argument('--limit', type=int, default=0, help='run only the first N jobs (smoke test)')
    ap.add_argument('--reach', default='', help='reach.json: only swaps whose pockets reach the far ends are tried')
    ap.add_argument('--margins', default='2.5,6,60', help='window margins (mm) tried per connection; a swap chosen '
                    'with --reach has a whole-board path, so 60 alone saves the failing small windows')
    a = ap.parse_args()
    global MARGINS
    MARGINS = tuple(float(m) for m in a.margins.split(','))
    init(a.model, a.plan, a.stage1, a.pops)
    Mx, opens = G['Mx'], G['open']
    want = set(a.nets.split(',')) if a.nets else None
    jobs = candidates(Mx, opens, want, a.targets, json.load(open(a.reach)) if a.reach else None)
    pad_at = {p['pad']: p['net'] for p in Mx['pads'] if p['ref'] == 'U1'}
    # most promising first: baselines, then unconnected targets, then same-kind targets, then the rest
    jobs.sort(key=lambda sw: (0 if sw[0][0] == sw[0][1] else 1 if not pad_at.get(sw[0][1]) else
                              2 if W.kind(pad_at[sw[0][0]]) == W.kind(pad_at[sw[0][1]]) else 3))
    if a.limit:
        jobs = jobs[:a.limit]
    print('%d swap jobs for %d open nets' % (len(jobs), len([n for n in opens if opens[n] > 0])), flush=True)
    with Pool(min(a.procs, len(jobs)), initializer=init, initargs=(a.model, a.plan, a.stage1, a.pops, MARGINS)) as pool:
        res = []
        for r in pool.imap_unordered(job, jobs, chunksize=1):
            res.append(r)
            if r:
                print('%-40s before %d after %s gain %+d  (%d tracks, %d vias)' % (
                    ' '.join('%s>%s' % sw for sw in r['swaps']), r['before'], r['after'], r['gain'], r['tracks'],
                    r['vias']), flush=True)
            if a.out:
                json.dump(res, open(a.out, 'w'), indent=1)
    best = choose(res)
    print('greedy disjoint set: %d swaps, expected gain %d' % (len(best), sum(r['gain'] for r in best)))
    for r in best:
        print('  %s  %+d  %s' % (' '.join('%s>%s' % sw for sw in r['swaps']), r['gain'],
                                 ' '.join('%s:%s>%s' % (b, m[0] or '-', m[1] or '-') for b, m in r['moves'].items())))


if __name__ == '__main__':
    main()
