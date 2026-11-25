import json, math, hashlib, os, glob, collections
import engine as G


def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()


def split_unlock(rec):
    keys = ('remove', 'remove_vias', 'tracks', 'vias', 'parts', 'renet_pads', 'microvias')
    core = {k: [] for k in keys}
    unl = {k: [] for k in keys}
    for k in keys:
        for e in rec.get(k, []):
            (unl if e.get('net') == 'GND' else core)[k].append(e)
    return core, unl


def hull(pts):
    pts = sorted(set(pts))
    if len(pts) <= 2:
        return pts

    def cr(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cr(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def footprint(rec, grow=0.10):
    """per layer: convex hull (mm) of every shape the delta ADDS (pads, tracks, vias) grown by 0.10 mm (the largest
    copper rule that applies to them), the R body box, + the existing objects it REMOVES/renames"""
    pts = collections.defaultdict(list)

    def circ(L, x, y, r):
        for k in range(16):
            a = 2 * math.pi * k / 16
            pts[L].append((round(x + r * math.cos(a), 4), round(y + r * math.sin(a), 4)))
    for t in rec['tracks']:
        L = G.LIN[t['layer']]
        circ(L, t['x1'], t['y1'], t['w'] / 2 + grow)
        circ(L, t['x2'], t['y2'], t['w'] / 2 + grow)
    for v in rec['vias']:
        for L in G.span(G.LIN[v['from']], G.LIN[v['to']]):
            circ(L, v['x'], v['y'], v['size'] / 2 + grow)
    for p in rec['parts']:
        for k in ('1', '2'):
            pd = p['pad' + k]
            for dx in (-0.15 - grow, 0.15 + grow):
                for dy in (-0.15 - grow, 0.15 + grow):
                    pts[p['side']].append((round(pd['x'] + dx, 4), round(pd['y'] + dy, 4)))
        bx = G.body_box(p)
        pts[p['side'] + ' body (0.63x0.33 max)'] += [(bx[0], bx[1]), (bx[2], bx[1]), (bx[2], bx[3]), (bx[0], bx[3])]
    return dict(hull_per_layer={L: hull(v) for L, v in pts.items()},
                removes=[dict(layer=t['layer'], net=t['net'], x1=t['x1'], y1=t['y1'], x2=t['x2'], y2=t['y2'], why=t.get('why', 'remove')) for t in rec['remove']],
                removes_vias=rec['remove_vias'])


def cid_of(net, c):
    return '%s_%s_%s_%g_%g_r%d' % (net, c['family'], c['unlock'], c['x'], c['y'], c['rot'])


fc = json.load(open('fullcheck_results.json')) if os.path.exists('fullcheck_results.json') else {}
out = dict(meta=dict(
    strategy='u3_end', base_plan='si/series_r/dq_series_r_plan.json', base_plan_md5=md5(G.base.PLAN13),
    board_extract_md5=md5(os.path.join(G.base.SR, 'board_extract.json')), pcbdoc_md5=G.C.B['source']['pcbdoc_md5'],
    grid_mm=0.05, rotations=[0, 90, 180, 270],
    router='0.02 mm raster Dijkstra + exact string-pull; every routed object >= rule + 2.5 um (DESIGN_MARGIN)',
    quick_check='engine.Cand.verify with check.py primitives (dist / gap_rule / width_rule / mask_exp): clearance per layer and class, '
                'hole-to-hole 0.24 on a shared span, width rules, pad mask web >= 0.10, R body vs same-side bodies/pads boxes',
    full_check='check.py (copy of d10/fold/check.py) on 13-R plan + candidate: 0 apply errors, split ok, 0 new shorts, no net gains '
               'islands, 0 antennae, 0 clearance/hole/width/mask violations, L2/L5 one live island, no plane object newly off the main island',
    families={'BF': 'Bottom R, stub removed, Bottom feed U3 pad -> pad1, Bottom fold-back return pad2 -> existing first via (south-row pattern)',
              'XF-Bottom': 'Bottom R; stub + first via become SDRAM-Dn; Bottom track via -> pad1; pad2 L5>Bottom + L4>L5 (+L3>L4) via-in-pad '
                           'column; inner re-join at K; inner route via..K removed',
              'XF-Top': 'Top R (R134 pattern); stub + first via become SDRAM-Dn; Top track from the via land -> pad1; pad2 Top>L2 + L2>L3 '
                        '(+ L3>L4 buried 0.27) via-in-pad column; inner re-join at K; inner route via..K removed'},
    pad_convention='pad 1 = SDRAM-Dn (U3 side), pad 2 = Dn (U1 side); R132 D13, R133 D14, R134 D15',
    coordinates='mm, PcbDoc origin, y up',
    how_to_combine='delta = emit_copper-format lists to append to dq_series_r_plan.json (plus SDRAM-Dn into net_class_add.SDRAM_DATA); '
                   'a candidate with requires_unlock also needs unlocks[<name>].rec appended once; prove any union with check.py'),
    unlocks=dict(gnd47=dict(description='non-critical re-route: U2-47 GND Top run (38.175,17.125)-(38.175,18.2)-(38.35,18.4) removed; U2-47 '
                                        're-tied to L2-GND by its own Top>L2 microvia 0.30/0.15 at (38.22,17.16) with a 0.18 mm Top stub. It '
                                        'opens the U2 NE corridor (between USB5V0 and U2-48) into the Top pocket east of U2. The GND through '
                                        'via (38.35,18.4) stays (it still serves U3-54 on Bottom). Required by every D13 and D14 candidate.',
                            rec=None)),
    nets={}, candidates=[], pairwise={}, joint_routed=[])
blk = json.load(open('blockers.json'))
for f in sorted(glob.glob('cands_1[345]_*.json')):
    if '_on1' in f:
        continue
    d = json.load(open(f))
    tag = os.path.basename(f)[6:-5]
    rj = json.load(open('rejects_%s.json' % tag))
    out['nets'].setdefault(d['net'], dict(searches=[], blockers=[b for b in blk if b['title'].startswith(d['net'] + ' ')]))
    out['nets'][d['net']]['searches'].append(dict(family=d['family'], unlock=d['unlock'], rbox=d['rbox'], placements=d['tasks'], legal=d['legal'],
                                                  top_reject_reasons=rj['reasons'][:12]))
    if tag == '15_XF-Top_gnd47':
        continue          # same family in the unlocked world; kept only as a search record (the unlock adds nothing for D15)
    for c in d['cands']:
        core, unl = split_unlock(c['rec'])
        if c['unlock'] == 'gnd47' and out['unlocks']['gnd47']['rec'] is None:
            out['unlocks']['gnd47']['rec'] = unl
        cid = cid_of(d['net'], c)
        p = c['rec']['parts'][0]
        out['candidates'].append(dict(id=cid, net=d['net'], ref=p['ref'], family=c['family'], requires_unlock=None if c['unlock'] == 'none' else c['unlock'],
                                      part=dict(side=p['side'], x=p['x'], y=p['y'], rot=p['rot'], pad1=p['pad1'], pad2=p['pad2']),
                                      delta=core, footprint=footprint(core), metrics=c['metrics'], worst_margins=c['worst_detail'],
                                      soft_flags=c['soft'], component_clearance_nearest=c['cc'], full_check=fc.get(cid)))
out['pairwise']['D14+D13'] = dict(
    compatible_pairs=0,
    method='D13 searched (XF-Top, 0.05 grid, 4 rot) on 13-R + each of the 19 D14 candidates, and D14 searched on 13-R + each of the 2 D13 '
           'candidates: 0 legal in both orders',
    reason='both first-via Top lands sit under U2 in one pocket whose only exit is the U2 NE corridor; D13 (west via) is always the outer/north '
           'track there and D14 the inner/south one; D13 can only re-join its L3 route from a column at ~(38.4,16.3) (south part of the pocket) '
           'while D14 can only re-join L4 from a column at ~(39.85-40.0,16.8-17.25) (east part); the outer track must cross the inner one on Top.')
out['pairwise']['D13+D15'] = dict(compatible_pairs=0, method='D15 searched (XF-Top, box 38.2-40.6 x 15.8-17.6) on 13-R + each D13 candidate: 0 legal')
for i, c14 in enumerate(json.load(open('cands_14_XF-Top_gnd47.json'))['cands']):
    cid14 = cid_of('D14', c14)
    on = json.load(open('cands_15_XF-Top_none_on14_%02d.json' % i))['cands']
    out['joint_routed'].append(dict(base=cid14, note='D15 candidates routed on 13-R + this D14 candidate (incl. gnd47); valid only together with it',
                                    d15=[dict(id='D15_on_%s_%g_%g_r%d' % (cid14, e['x'], e['y'], e['rot']), part=dict(side='Top', x=e['x'], y=e['y'], rot=e['rot']),
                                              delta=e['rec'], metrics=e['metrics'], worst_margins=e['worst'], soft_flags=e['soft']) for e in on]))
out['pairwise']['D14+D15'] = dict(compatible_pairs=sum(len(j['d15']) for j in out['joint_routed']),
                                  per_D14={j['base']: len(j['d15']) for j in out['joint_routed']})
json.dump(out, open('candidates.json', 'w'), indent=1)
print({n: len([c for c in out['candidates'] if c['net'] == n]) for n in ('D13', 'D14', 'D15')}, out['pairwise']['D14+D15']['compatible_pairs'])
print(os.path.getsize('candidates.json'))
