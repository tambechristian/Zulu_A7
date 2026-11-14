"""Exhaustive joint selection over the three strategies' candidates.

Lexicographic objective (task): coverage D14 > D13 > D15, then fewest new vias / microvias / VIPPO sites, then fewest
copper changes to the 13-R plan, then best exact new-geometry margin.

Step 1 (coverage + via budget, all candidates): D13 has candidates only in u3_end (2 x R132, both need gnd47), so full
coverage needs gnd47 + R132.  For D14/D15 the per-net minimum of new vias over every strategy is reported; the joint
optimum can only use per-net minima if a compatible triple exists, which step 2/3 prove.
Step 2: every (R132, D14, D15) triple at the minimum via count and minimum copper-change count is merged and measured
with lib.margins (checker-copy primitives, exact).  Margin of a triple = min over the entries contributed by its own
new geometry (entries already present in the 13-R plan's own measurement are excluded).
Step 3 (combine.py): the winner is written and proven with check.py.
usage: python rank.py   -> work/rank.json, rank.log
"""
import json, os, sys, collections, itertools
from multiprocessing import Pool
import lib

HERE = lib.HERE
W = os.path.join(HERE, 'work')
os.makedirs(W, exist_ok=True)


def ekey(e):
    # renamed objects (Dn -> SDRAM-Dn) keep their geometry: normalise the net name so their entries match
    m, cat, a, b = e
    a, b = a.replace('SDRAM-D', 'D'), b.replace('SDRAM-D', 'D')
    return (m, cat) + tuple(sorted((a, b)))


B = lib.C.B
_side = {c['ref']: c['side'] for c in B['components']}
ABOX = {}
for _ref, _v in B['component_outlines'].items():
    if _ref == 'X2':
        continue
    _bx = [_v[k] for k in _v if k in ('pads', 'Mech3', 'Mech4', 'Mech8', 'Mech3(region)', 'Mech4(region)', 'Mech8(region)')]
    if _bx:
        ABOX[_ref] = (_side.get(_ref), [min(b[0] for b in _bx), min(b[1] for b in _bx), max(b[2] for b in _bx), max(b[3] for b in _bx)])


def rbox(pr):
    xs = [pr['pad1']['x'], pr['pad2']['x']]; ys = [pr['pad1']['y'], pr['pad2']['y']]
    return [min(xs) - 0.15, min(ys) - 0.15, max(xs) + 0.15, max(ys) + 0.15]


def rr(a, b):
    return lib.C.d_rect_rect(((a[0] + a[2]) / 2, (a[1] + a[3]) / 2, (a[2] - a[0]) / 2, (a[3] - a[1]) / 2),
                             ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, (b[2] - b[0]) / 2, (b[3] - b[1]) / 2))


def cc_min(parts, base_parts):
    """check.py section-14 ComponentClearance (pad bbox for R0201, union of pads/Mech for the board's parts) of the
    given new parts against every same-side board part, every 13-R plan part and each other"""
    others = dict(ABOX)
    for pr in base_parts + parts:
        others[pr['ref']] = (pr['side'], rbox(pr))
    best = (9.0, None, None)
    for pr in parts:
        a = rbox(pr)
        for r2, (s2, b2) in others.items():
            if r2 == pr['ref'] or s2 != pr['side']:
                continue
            d = rr(a, b2)
            if d < best[0]:
                best = (round(d, 4), pr['ref'], r2)
    return best


def eval_plan(args):
    name, deltas, note, base_keys = args
    base = lib.load_base()
    P, errs = lib.merge(base, deltas, note)
    p = os.path.join(W, 'p_%s.json' % name)
    json.dump(P, open(p, 'w'))
    m = lib.margins(p)
    os.remove(p)
    own = [e for e in m['all'] if ekey(e) not in base_keys]
    return name, errs, m['apply_errors'], own


def full_entries(deltas, note, name):
    base = lib.load_base()
    P, errs = lib.merge(base, deltas, note)
    p = os.path.join(W, 'p_%s.json' % name)
    json.dump(P, open(p, 'w'))
    m = lib.margins(p)
    os.remove(p)
    return m


def main():
    pools, unl = lib.load_pools()
    out = dict(step1={}, step2={})
    L = []

    def log(*a):
        s = ' '.join(str(x) for x in a)
        L.append(s)
        print(s)

    log('== step 1: per-net candidate pools (all strategies, proven-alone only) ==')
    for n in ('D13', 'D14', 'D15'):
        cnt = collections.Counter((c['src'], c['family'], c['stats']['new_vias'], c['stats']['vippo'], c['silk_U1'], c['unlock'] or '-')
                                  for c in pools[n])
        log(n, 'candidates', len(pools[n]))
        for k, v in sorted(cnt.items(), key=lambda kv: (kv[0][2], kv[0][0], kv[0][1])):
            log('   src %-9s family %-9s new_vias %d vippo %d silk_U1 %-5s unlock %-5s : %d' % (k + (v,)))
        out['step1'][n] = {'%s|%s|v%d|vippo%d|silk%s|%s' % k: v for k, v in cnt.items()}
    log('D13 exists only as u3_end R132 (2 poses, gnd47 required) -> full coverage = gnd47 + R132 + D14 + D15.')
    log('Per-net minimum new vias: D14 %d, D15 %d (u1_end F4: pad-1 L4>L5>Bottom column only).' % (
        min(c['stats']['new_vias'] for c in pools['D14']), min(c['stats']['new_vias'] for c in pools['D15'])))

    # base measurement (13-R plan alone) -> keys to exclude
    m0 = full_entries([], 'base', 'base')
    k13 = {ekey(e) for e in m0['all']}
    # step 2a: R132 choice (its geometry is >= 4 mm from every F4 site; measured on 13-R + gnd47 + R132)
    log('\n== step 2a: R132 pose (13-R + gnd47 + R132) ==')
    r132 = []
    for c in pools['D13']:
        m = full_entries([unl['gnd47'], lib.polish(c['delta'])], 'r132', 'r132')
        own = [e for e in m['all'] if ekey(e) not in k13]
        r132.append((own[0][0], own[1][0] if len(own) > 1 else 1, c, own))
        log(c['id'], 'apply errors', m['apply_errors'], 'own smallest:')
        for e in own[:6]:
            log('     ', e)
    # rank by min, then the next distinct-object margin (the min is the shared R131 mask web)
    def second(own):
        vals = [e[0] for e in own if not ('R131-1' in e[2] + e[3] and 'R132-1' in e[2] + e[3])]
        return vals[0] if vals else 1.0
    r132.sort(key=lambda t: (-t[0], -second(t[3])))
    best132 = r132[0][2]
    log('chosen R132:', best132['id'], 'min', r132[0][0], 'next', second(r132[0][3]))
    out['step2']['r132'] = [dict(id=t[2]['id'], min=t[0], next=second(t[3]), own=t[3][:8]) for t in r132]

    # step 2b: D14 x D15 at minimum vias and minimum copper changes, exact margins on the full triple
    d14 = [c for c in pools['D14'] if c['stats']['new_vias'] == 2]
    d15 = [c for c in pools['D15'] if c['stats']['new_vias'] == 2]
    for lst in (d14, d15):
        for c in lst:
            c['pd'] = lib.polish(c['delta'])
            c['pch'] = lib.delta_stats(c['pd'])['copper_changes']
    m14 = min(c['pch'] for c in d14); m15 = min(c['pch'] for c in d15)
    log('\n== step 2b: D14 x D15 at 2+2 new vias ==')
    log('D14 2-via candidates %d (min copper changes %d: %d), D15 2-via candidates %d (min %d: %d)' % (
        len(d14), m14, sum(c['pch'] == m14 for c in d14), len(d15), m15, sum(c['pch'] == m15 for c in d15)))
    d14m = [c for c in d14 if c['pch'] == m14]
    d15m = [c for c in d15 if c['pch'] == m15]
    m1 = full_entries([unl['gnd47'], lib.polish(best132['delta'])], 'b1', 'b1')
    kb = {ekey(e) for e in m1['all']} | k13
    jobs = []
    for a, b in itertools.product(d14m, d15m):
        name = '%s__%s' % (a['id'].split(':')[1], b['id'].split(':')[1])
        jobs.append((name, [unl['gnd47'], lib.polish(best132['delta']), a['pd'], b['pd']], 'rank', kb))
    log('triples to measure:', len(jobs))
    res = []
    with Pool(6) as pool:
        for name, errs, aerr, own in pool.imap_unordered(eval_plan, jobs, chunksize=8):
            a, b = name.split('__')
            pa = [c for c in d14m if c['id'].endswith(':' + a)][0]['part']
            pb = [c for c in d15m if c['id'].endswith(':' + b)][0]['part']
            cc = cc_min([pa, pb], lib.load_base()['parts'])
            om = own[0][0] if own else 1.0
            res.append(dict(name=name, merge_errors=errs, apply_errors=aerr, own_min=om, cc=cc,
                            score=round(min(om, cc[0] - 0.254), 4), own=own[:12]))
    bad = [r for r in res if r['merge_errors'] or r['apply_errors']]
    log('merge/apply errors in', len(bad), 'triples')
    def tieb(r):
        vals = sorted({e[0] for e in r['own']})
        return tuple(-v for v in (vals + [1.0, 1.0, 1.0])[:3])
    res.sort(key=lambda r: (-r['score'], -r['own_min']) + tieb(r) + (r['name'],))
    log('top 15 by score = min(own new-geometry copper/h2h/mask margin, ComponentClearance - 0.254):')
    for r in res[:15]:
        log('  score %+.4f copper %+.4f CC %s  %s' % (r['score'], r['own_min'], r['cc'], r['name']), r['own'][:2])
    out['step2']['triples'] = res
    out['step2']['chosen_r132'] = best132['id']
    json.dump(out, open(os.path.join(W, 'rank.json'), 'w'), indent=1)
    open(os.path.join(HERE, 'rank.log'), 'w', newline='\n').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
