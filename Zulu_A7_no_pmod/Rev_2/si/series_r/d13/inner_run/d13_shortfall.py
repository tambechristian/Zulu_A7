"""For every R0201 position along D13's L3 run (both pads within 0.45 mm of the run, 0.025 grid, 4 rotations, Top
and Bottom stacks): the binding blocker = the most negative margin over both pads' exact site rules plus the
R box vs component boxes (0.254 Altium on the extract boxes / section-10 bodies).  Per 0.5 mm of run arc length
and side, the LEAST-blocked position is reported with its blocker and shortfall."""
import json, collections, math
import search as S
d = json.load(open('d13_blockers.json'))
rows = d['rows']
idx = {(r['side'], round(r['x'], 3), round(r['y'], 3)): r for r in rows}
plan_refs = {'R%d' % k for k in range(119, 132)}
out = collections.defaultdict(dict)
for (side, x, y), r in idx.items():
    for rot, (dx, dy) in S.ROT.items():
        k2 = (side, round(x + dx, 3), round(y + dy, 3))
        if k2 not in idx:
            continue
        r2 = idx[k2]
        worst = (9.0, 'none')
        blk = {}
        for rr_, tag in ((r, 'pad1'), (r2, 'pad2')):
            for k, v in rr_['fails'].items():
                key = v[1]
                if key not in blk or v[0] < blk[key][0]:
                    blk[key] = (round(v[0], 4), '%s %s' % (tag, k))
                if v[0] < worst[0]:
                    worst = (v[0], '%s %s %s' % (tag, k, v[1]))
        bb = [min(x, r2['x']) - 0.15, min(y, r2['y']) - 0.15, max(x, r2['x']) + 0.15, max(y, r2['y']) + 0.15]
        for ref, (s_, b) in S.ABOX.items():
            if s_ == side:
                v = S.rr(bb, b) - 0.254
                if v < -1e-6:
                    blk['%s box' % ref] = (round(v, 4), 'ComponentClearance 0.254 R box vs %s box%s' % (ref, ' (plan R)' if ref in plan_refs else ''))
                if v < worst[0]:
                    worst = (v, 'R box vs %s box (ComponentClearance 0.254%s)' % (ref, ', plan R' if ref in plan_refs else ''))
        for ref, (s_, bx) in S.BBOX10.items():
            if s_ == side:
                v = min(S.rr(bb, b) for b in bx) - 0.254
                if v < -1e-6:
                    blk['%s body' % ref] = (round(v, 4), 'R box vs %s body (section-10 box, 0.254)' % ref)
                if v < worst[0]:
                    worst = (v, 'R box vs %s body (0.254)' % ref)
        s_mid = S.proj(*([S.run_poly('D13')[1]] + [(x + r2['x']) / 2, (y + r2['y']) / 2]))[1]
        b = int(s_mid // 0.5)
        cur = out[side].get(b)
        score = (len(blk), -worst[0])
        if cur is None or score < cur['_score']:
            out[side][b] = dict(arc=[b * 0.5, b * 0.5 + 0.5], pad1=[x, y], pad2=[r2['x'], r2['y']], rot=rot,
                                shortfall=round(worst[0], 4), blocker=worst[1], n_blockers=len(blk),
                                all_blockers=sorted([[v[0], k, v[1]] for k, v in blk.items()]), _score=score)
res = {s: [{k: v for k, v in out[s][b].items() if k != '_score'} for b in sorted(out[s])] for s in out}
json.dump(res, open('d13_shortfall.json', 'w'), indent=1)
for s in res:
    print('==', s)
    for e in res[s]:
        print('  arc %.1f-%.1f fewest-blocker R pads %s/%s rot %d: %d blockers: %s' % (e['arc'][0], e['arc'][1], e['pad1'], e['pad2'], e['rot'], e['n_blockers'], '; '.join('%s %+.3f (%s)' % (b[1], b[0], b[2]) for b in e['all_blockers'])))
