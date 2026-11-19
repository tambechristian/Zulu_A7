"""D13 blocker map: every column site within 0.45 mm of D13's L3 run (0.025 grid), Top and Bottom stacks; for each
site the failing rules (exact, search.py's site_eval) and whether the R0201 body there would overlap a component
body (U2 on Top, U3 on Bottom: section-10 body boxes).  Aggregated per 0.5 mm of run arc length."""
import json, collections, math
import search as S
net = 'D13'
runL, segs, used = S.run_poly(net)
tot = sum(math.hypot(s[2]-s[0], s[3]-s[1]) for s in segs)
rows = []
allx = [v for s in segs for v in (s[0], s[2])]; ally = [v for s in segs for v in (s[1], s[3])]
for side in ('Top', 'Bottom'):
    x = min(allx) - 0.5
    while x <= max(allx) + 0.5:
        y = min(ally) - 0.5
        while y <= max(ally) + 0.5:
            pj = S.proj(segs, x, y)
            if pj[0] <= 0.45:
                ok, m = S.site_eval(net, side, runL, x, y)
                fails = {k: v for k, v in m.items() if v[0] < -1e-6}
                # body under the pad (section 10 boxes, same side)
                pb = [x - 0.15, y - 0.15, x + 0.15, y + 0.15]
                body = [r for r, (s_, bx) in S.BBOX10.items() if s_ == side and r not in ('R119','R120','R121','R122','R123','R124','R125','R126','R127','R128','R129','R130','R131')
                        and min(S.rr(pb, b) for b in bx) < 0.254 - 1e-6]
                rows.append(dict(side=side, x=round(x, 4), y=round(y, 4), s=round(pj[1], 3), d=round(pj[0], 3), ok=ok,
                                 fails={k: [round(v[0], 4), v[1]] for k, v in fails.items()}, body=body))
            y += 0.025
        x += 0.025
out = {}
for side in ('Top', 'Bottom'):
    bins = collections.defaultdict(list)
    for r in rows:
        if r['side'] == side:
            bins[int(r['s'] // 0.5)].append(r)
    summ = []
    for b in sorted(bins):
        rs = bins[b]
        objc = collections.Counter()
        for r in rs:
            for k, v in r['fails'].items():
                objc['%s: %s' % (k, v[1])] += 1
            for bb in r['body']:
                objc['component clearance/body: %s' % bb] += 1
        free = [r for r in rs if r['ok'] and not r['body']]
        okclr = [r for r in rs if r['ok']]
        summ.append(dict(s_from=b * 0.5, s_to=b * 0.5 + 0.5, sites=len(rs), legal_rules=len(okclr), legal_and_no_body=len(free),
                         free_sites=[(r['x'], r['y']) for r in free][:20], top_blockers=objc.most_common(8)))
    out[side] = summ
json.dump(dict(run_len=tot, segs=segs, bins=out, rows=rows), open('d13_blockers.json', 'w'), indent=0)
for side in out:
    print('==', side)
    for b in out[side]:
        print(' s %.1f-%.1f sites %d rules-legal %d free %d %s' % (b['s_from'], b['s_to'], b['sites'], b['legal_rules'], b['legal_and_no_body'], b['free_sites'][:6]))
        for o, c in b['top_blockers'][:6]:
            print('      %4d %s' % (c, o))
