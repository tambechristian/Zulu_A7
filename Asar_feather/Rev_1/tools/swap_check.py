"""Check a swap_apply.py output folder before anything goes near the board (2026-10-28, after the review that found
stage1.json re-netting no stub tracks).

    python tools/swap_check.py <outdir> <model_pre4.json> <stage1_model.json> [reference outdir]

Proves, with counts: the U1 pads of model.json differ from the source model exactly by perm.json's swap table;
every stub object of a touched ball carries its new net in stage1.json and model.json (none left for a ball
that ends unconnected); stage1.json + tools/route/stage3_sdram.json (minus the moved nets) is exactly model.json's
copper, so the board chain ClearRoutingCopper -> stage1.json -> stage3_sdram -> plan reproduces the routed model;
seed.json holds no moved-net copper and no duplicate; a reference folder's model.json must be identical.
Tracks are keyed end-order-free (the board export stores stage-1 stubs end-reversed).
"""
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from swap_eval import fanout  # noqa: E402
from swap_apply import tkey, vkey  # noqa: E402


def objs(P):
    out = Counter()
    for t in P['tracks']:
        out[(t['net'], tkey(t), round(t['w'], 3))] += 1
    for v in P['vias']:
        sp = v['span'] if 'span' in v else [v['from'], v['to']]   # the model lists every layer crossed
        out[(v['net'], vkey(v), sp[0], sp[-1])] += 1
    return out


def main():
    outdir, model_src, stage1_src = sys.argv[1:4]
    ref = sys.argv[4] if len(sys.argv) > 4 else None
    M = json.load(open(os.path.join(outdir, 'model.json')))
    S = json.load(open(os.path.join(outdir, 'seed.json')))
    P1 = json.load(open(os.path.join(outdir, 'stage1.json')))
    perm = json.load(open(os.path.join(outdir, 'perm.json')))
    M0 = json.load(open(model_src))
    fan = fanout(json.load(open(stage1_src)))
    S3 = json.load(open(os.path.join(HERE, 'route', 'stage3_sdram.json')))
    bad = []
    # 1. pads
    u0 = {p['pad']: p['net'] for p in M0['pads'] if p['ref'] == 'U1'}
    u1 = {p['pad']: p['net'] for p in M['pads'] if p['ref'] == 'U1'}
    moved = set()
    for net, (old, new) in perm['swap'].items():
        moved.add(net)
        if u0.get(old) != net:
            bad.append('swap table: %s was not on %s in the source model (%s)' % (net, old, u0.get(old)))
        if u1.get(new) != net:
            bad.append('model.json: %s is not on %s (%s)' % (net, new, u1.get(new)))
    touched = set(perm['perm'])
    for b in touched:
        if u1[b] and u1[b] not in moved:
            bad.append('model.json: touched ball %s carries unmoved net %s' % (b, u1[b]))
    for b in set(u0) | set(u1):
        if b not in touched and u0.get(b) != u1.get(b):
            bad.append('model.json: untouched ball %s changed %s -> %s' % (b, u0.get(b), u1.get(b)))
    other0 = Counter((p['ref'], p['pad'], p['net']) for p in M0['pads'] if p['ref'] != 'U1')
    other1 = Counter((p['ref'], p['pad'], p['net']) for p in M['pads'] if p['ref'] != 'U1')
    if other0 != other1:
        bad.append('model.json: non-U1 pads changed')
    if Counter(v for v in u0.values() if v) != Counter(v for v in u1.values() if v):
        bad.append('model.json: the U1 net multiset changed')
    # 2. stubs
    o1, om = objs(P1), objs(M)
    for b in touched:
        if b not in fan:
            continue
        keys = [tkey(t) for t in fan[b][0]] + [vkey(v) for v in fan[b][1]]
        want = u1[b]
        for k in keys:
            in1 = [o for o in o1 if o[1] == k]
            inm = [o for o in om if o[1] == k]
            if want:
                if {o[0] for o in in1} != {want} or sum(o1[o] for o in in1) != sum(om[o] for o in inm):
                    bad.append('stage1.json: stub %s of %s carries %s, want %s' % (k, b, [o[0] for o in in1], want))
                if {o[0] for o in inm} != {want}:
                    bad.append('model.json: stub %s of %s carries %s, want %s' % (k, b, [o[0] for o in inm], want))
            else:
                if in1 or inm:
                    bad.append('stub %s of the unconnected ball %s is still present (stage1 %s, model %s)' % (
                        k, b, in1, inm))
    # 3. board chain identity
    chain = o1 + Counter({k: n for k, n in objs(S3).items() if k[0] not in moved})
    if chain != om:
        miss = om - chain
        extra = chain - om
        bad.append('stage1 + stage3_sdram != model.json: %d missing, %d extra (e.g. %s / %s)' % (
            sum(miss.values()), sum(extra.values()), next(iter(miss), None), next(iter(extra), None)))
    # 4. seed
    os_ = objs(S)
    for k, n in os_.items():
        if k[0] in moved:
            bad.append('seed.json holds moved-net copper: %s' % (k,))
            break
    dup = sum(n - 1 for n in os_.values() if n > 1)
    if dup:
        bad.append('seed.json holds %d duplicate objects' % dup)
    if os_ & om:
        bad.append('seed.json and model.json share %d objects' % sum((os_ & om).values()))
    # 5. reference
    if ref:
        R = json.load(open(os.path.join(ref, 'model.json')))
        if R != M:
            bad.append('model.json differs from %s/model.json' % ref)
    print('model %d pads, %d tracks, %d vias; stage1 %d tracks, %d vias; seed %d tracks, %d vias; %d nets moved' % (
        len(M['pads']), len(M['tracks']), len(M['vias']), len(P1['tracks']), len(P1['vias']), len(S['tracks']),
        len(S['vias']), len(moved)))
    for b in bad:
        print('FAIL', b)
    print('FAIL' if bad else 'PASS')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
