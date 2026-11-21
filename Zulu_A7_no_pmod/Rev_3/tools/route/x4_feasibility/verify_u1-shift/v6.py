exec(open('v1.py').read().split("def key")[0])
Cs = {c['ref']: c for c in D['comps']}; C2 = {c['ref']: c for c in D2['comps']}
def pads(MM, r): return [p for p in MM['pads'] if p['ref']==r]
for r in ['U3','U1','U2','U4','Q1','R24']:
    ps = pads(M, r); print(r, Cs[r]['layer'], Cs[r]['rot'], round(min(p['x'] for p in ps),2), round(max(p['x'] for p in ps),2), round(min(p['y'] for p in ps),2), round(max(p['y'] for p in ps),2))
def near(MM, net, ref):
    return [p for p in MM['pads'] if p['net']==net and p['ref']==ref]
print('ref side  net_U1side dU1(old->new)  net_U3side dU3(old->new)')
for i in range(119, 135):
    r = 'R%d' % i
    po, pn = pads(M, r), pads(M2, r)
    row = [r, Cs[r]['layer'], '->', C2[r]['layer']]
    for k in range(2):
        net = po[k]['net']
        for tgt in ('U1', 'U3'):
            a = near(M, net, tgt); b = near(M2, net, tgt)
            if a:
                do = math.hypot(po[k]['x']-a[0]['x'], po[k]['y']-a[0]['y']); dn = math.hypot(pn[k]['x']-b[0]['x'], pn[k]['y']-b[0]['y'])
                row += [net, tgt, round(do,2), round(dn,2)]
    print(*row)
# SDRAM nets U1<->U3 manhattan length
txt = open(r'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_3/Imported zulu_a7.PrjPcb/Project Outputs for Zulu_a7_no_pmod/Zulu_a7_no_pmod.NET').read()
d_old, d_new = [], []
for net in sorted({p['net'] for p in M['pads'] if p['ref']=='U3' and p['net'] and p['net'].startswith('SDRAM')}):
    a = near(M, net, 'U1'); u = near(M, net, 'U3'); b = near(M2, net, 'U1')
    if a and u:
        d_old.append(abs(a[0]['x']-u[0]['x'])+abs(a[0]['y']-u[0]['y'])); d_new.append(abs(b[0]['x']-u[0]['x'])+abs(b[0]['y']-u[0]['y']))
print('direct U1-U3 SDRAM nets', len(d_old), 'manhattan old min/mean/max', [round(f(d_old),2) for f in (min, lambda x: sum(x)/len(x), max)], 'new', [round(f(d_new),2) for f in (min, lambda x: sum(x)/len(x), max)])
