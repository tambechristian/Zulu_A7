"""Apply a chosen set of ball swaps to the routing inputs (2026-10-27).

    python tools/swap_apply.py <swaps.json> <model_pre4.json> <stage1_model.json> <outdir> [plan.json ...]
                               [--stage1-src <previous round's stage1.json>]   (round 2+: model = the
                               previous round's model.json, plans = its best plan)

swaps.json is a list of [ball_a, ball_b] pairs (or the swap_eval.py result list, whose 'swaps' are taken).
Writes to <outdir>:
    model.json   the pre-stage-4 model after the swaps: pads exchange nets, every track and via of the swapped
                 nets is dropped (the SDRAM bus of a swapped SDRAM net included), each swapped ball keeps its
                 stage-1 stub under its new net; the plans' copper is NOT in it
    seed.json    the given plans' copper minus the swapped nets, for router.py --seed
    perm.json    {'perm': {ball: new ball}, 'swap': {net: [old ball, new ball]}} for apply_pin_swap.py
    stage1.json  the stage-1 plan (tools/route/stage1_u1.json) with the swapped balls' stubs re-netted, for the
                 board: ClearRoutingCopper, then this, then the SDRAM plan minus the swapped nets, then the rest
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import swap_rules as W  # noqa: E402
from swap_eval import fanout, swapped  # noqa: E402


def tkey(t):
    """a track's identity independent of its end order (board exports store stage-1 stubs end-reversed)"""
    return ('t', t['layer'], tuple(sorted([(round(t['x1'], 3), round(t['y1'], 3)), (round(t['x2'], 3), round(t['y2'], 3))])))


def vkey(v):
    return ('v', round(v['x'], 3), round(v['y'], 3))


def main():
    argv = sys.argv[1:]
    src1 = os.path.join(HERE, 'route', 'stage1_u1.json')   # the stage-1 plan the re-netted stage1.json starts from
    if '--stage1-src' in argv:                              # a later round starts from the previous round's stage1.json
        i = argv.index('--stage1-src')
        src1 = argv[i + 1]
        del argv[i:i + 2]
    sw, model, stage1, outdir = argv[:4]
    plans = argv[4:]
    S = json.load(open(sw))
    swaps = [tuple(s) for r in S for s in (r['swaps'] if isinstance(r, dict) else [r])]
    M = json.load(open(model))
    S1 = json.load(open(stage1))
    fan = fanout(S1)
    pad_at = {p['pad']: p['net'] for p in M['pads'] if p['ref'] == 'U1'}
    count = {}
    for p in M['pads']:
        if p['ref'] == 'U1' and p['net']:
            count[p['net']] = count.get(p['net'], 0) + 1
    touched = list(dict.fromkeys(b for s in swaps for b in s))
    for b in touched:
        if pad_at[b] and count[pad_at[b]] != 1:
            sys.exit('REFUSED: %s sits on more than one ball' % pad_at[b])
    Ms, nets = swapped(M, fan, swaps)                # the swaps apply in order, so chains and rotations work
    final = {p['pad']: p['net'] for p in Ms['pads'] if p['ref'] == 'U1'}
    for q in touched:
        if final[q] and not W.legal(final[q], q):
            sys.exit('REFUSED: %s may not move to %s' % (final[q], q))
    for q in touched:                                # an XADC input and its mate must end on the same ADn pair
        n = final[q]
        if n and W.kind(n) == 'xadc':
            mate = n[:-1] + ('N' if n.endswith('P') else 'P')
            mb = [b for b, m in final.items() if m == mate]
            pa, pb = W.ad_pair(q), (W.ad_pair(mb[0]) if mb else None)
            if not mb or not pa or not pb or pa[0] != pb[0]:
                sys.exit('REFUSED: %s on %s and %s on %s are not one ADn pair' % (n, q, mate, mb[0] if mb else '?'))
    if sorted(n for n in final.values() if n) != sorted(n for n in pad_at.values() if n):
        sys.exit('REFUSED: the swaps lose or duplicate a net')
    os.makedirs(outdir, exist_ok=True)
    json.dump(Ms, open(os.path.join(outdir, 'model.json'), 'w'))
    seed = {'vias': [], 'tracks': [], 'remove': [], 'log': []}
    for f in plans:
        P = json.load(open(f))
        seed['vias'] += [v for v in P['vias'] if v['net'] not in nets]
        seed['tracks'] += [t for t in P['tracks'] if t['net'] not in nets]
    seen, dedup = set(), {'vias': [], 'tracks': []}  # a plan can hold a track twice; the board wants it once
    for v in seed['vias']:
        k = (v['net'], vkey(v), v['from'], v['to'])
        if k not in seen:
            seen.add(k)
            dedup['vias'].append(v)
    for t in seed['tracks']:
        k = (t['net'], tkey(t), round(t['w'], 3))
        if k not in seen:
            seen.add(k)
            dedup['tracks'].append(t)
    if len(dedup['tracks']) != len(seed['tracks']) or len(dedup['vias']) != len(seed['vias']):
        print('seed: %d duplicate tracks and %d duplicate vias dropped' % (
            len(seed['tracks']) - len(dedup['tracks']), len(seed['vias']) - len(dedup['vias'])))
    seed.update(dedup)
    json.dump(seed, open(os.path.join(outdir, 'seed.json'), 'w'), indent=0)
    pins = {q: q for q in touched}                   # pins[q]: the ball whose symbol pin now sits at q
    for a, b in swaps:
        pins[a], pins[b] = pins[b], pins[a]
    perm = {pins[q]: q for q in touched}             # the pin at pins[q] is renamed to q
    swap = {final[q]: [pins[q], q] for q in touched if final[q]}
    json.dump({'perm': perm, 'swap': swap}, open(os.path.join(outdir, 'perm.json'), 'w'), indent=1)
    renet = {pad_at[q]: final[q] for q in touched if pad_at[q]}   # the stub at q keeps its place, changes net
    P1 = json.load(open(src1))
    keyed = set()
    for ball in touched:
        if ball in fan:
            for t in fan[ball][0]:
                keyed.add(tkey(t))
            for v in fan[ball][1]:
                keyed.add(vkey(v))
    out1 = {'vias': [], 'tracks': [], 'remove': P1.get('remove', []),
            'log': P1.get('log', []) + ['%s with swaps: %s' % (os.path.basename(src1), swaps)]}
    nt = nv = 0
    for t in P1['tracks']:
        k = tkey(t)
        if k in keyed:
            t = dict(t, net=renet[t['net']])
            nt += 1
        out1['tracks'].append(t)
    for v in P1['vias']:
        k = vkey(v)
        if k in keyed:
            v = dict(v, net=renet[v['net']])
            nv += 1
        out1['vias'].append(v)
    # a ball whose new net is '' (unconnected) keeps no stub
    out1['tracks'] = [t for t in out1['tracks'] if t['net']]
    out1['vias'] = [v for v in out1['vias'] if v['net']]
    json.dump(out1, open(os.path.join(outdir, 'stage1.json'), 'w'), indent=0)
    own = sum(len(fan[b][0]) + len(fan[b][1]) for b in touched if b in fan)
    if nt + nv != own:
        sys.exit('stage1.json: re-netted %d tracks + %d vias but the touched balls own %d stub objects' % (nt, nv, own))
    print('%d swaps over nets %s' % (len(swaps), ' '.join(sorted(nets))))
    print('model: %d tracks, %d vias; seed: %d tracks, %d vias; stage1: %d tracks, %d vias re-netted' % (
        len(Ms['tracks']), len(Ms['vias']), len(seed['tracks']), len(seed['vias']), nt, nv))
    for net, (old, new) in sorted(swap.items()):
        print('  %-14s %s -> %s' % (net, old, new))


if __name__ == '__main__':
    main()
