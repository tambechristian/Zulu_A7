exec(open('v1.py').read().split("def key")[0])
txt = open(r'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_4/Imported zulu_a7.PrjPcb/Project Outputs for Zulu_a7_no_pmod/Zulu_a7_no_pmod.NET').read()
nets = {}
for m in re.finditer(r'\(\s*\n([^\n]+)\n(.*?)\)', txt, re.S):
    nets[m.group(1).strip()] = [l.strip() for l in m.group(2).split('\n') if l.strip()]
print(len(nets))
pin2net = {}
for n, ns in nets.items():
    for x in ns: pin2net[x] = n
u2nets = {n for n, ns in nets.items() if any(x.startswith('U2-') for x in ns)}
BIG = {'GND', 'VCC3V3'}
parts = collections.defaultdict(set)
for n in u2nets:
    if n in BIG: continue
    for x in nets[n]:
        r = x.split('-')[0]
        if r != 'U2': parts[r].add(n)
def cen(MM, r):
    ps = [p for p in MM['pads'] if p['ref'] == r]
    return (round(sum(p['x'] for p in ps)/len(ps),2), round(sum(p['y'] for p in ps)/len(ps),2)) if ps else None
Cs = {c['ref']: c for c in D2['comps']}
u2p_old = {p['pad']: p for p in M['pads'] if p['ref']=='U2'}; u2p_new = {p['pad']: p for p in M2['pads'] if p['ref']=='U2'}
for r in sorted(parts):
    # distance from part pad on net to nearest U2 pin on same net, old and new
    ds = []
    for n in parts[r]:
        pins = [x.split('-',1)[1] for x in nets[n] if x.startswith('U2-')]
        rp = [p for p in M2['pads'] if p['ref']==r and p['net']==n]
        rpo = [p for p in M['pads'] if p['ref']==r and p['net']==n]
        if not rp: continue
        do = min(math.hypot(a['x']-u2p_old[q]['x'], a['y']-u2p_old[q]['y']) for a in rpo for q in pins if q in u2p_old)
        dn = min(math.hypot(a['x']-u2p_new[q]['x'], a['y']-u2p_new[q]['y']) for a in rp for q in pins if q in u2p_new)
        ds.append((n, round(do,2), round(dn,2)))
    print(r, Cs.get(r,{}).get('layer'), Cs.get(r,{}).get('pattern'), cen(M, r), '->', cen(M2, r), ds)
print('Q1 nets', [ (p['pad'],p['net']) for p in M['pads'] if p['ref']=='Q1'])
