exec(open('v5.py').read().split("allnets")[0])
Cs = {c['ref']: c for c in D['comps']}
u1o = {p['pad']: p for p in M['pads'] if p['ref']=='U1'}; u1n = {p['pad']: p for p in M2['pads'] if p['ref']=='U1'}
u1nets = {p['net'] for p in u1o.values()}
refs = sorted({p['ref'] for p in M['pads'] if p['ref'] not in moved and p['ref'] not in ('X2',)})
rows = []
for r in refs:
    ps = [p for p in M['pads'] if p['ref']==r]
    best = None
    for p in ps:
        if p['net'] in ('', None): continue
        cand = [q for q in u1o.values() if q['net']==p['net']]
        if not cand: continue
        do = min(math.hypot(p['x']-q['x'], p['y']-q['y']) for q in cand)
        dn = min(math.hypot(p['x']-u1n[q['pad']]['x'], p['y']-u1n[q['pad']]['y']) for q in cand)
        if best is None or do < best[1]: best = (p['net'], round(do,2), round(dn,2))
    if best and best[1] < 6: rows.append((r, Cs[r]['layer'], Cs[r]['pattern'], *best))
for x in sorted(rows, key=lambda x: x[4]-x[5]): print(x)
