import json, math, collections, sys, re
sys.path.insert(0, r'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_3/tools')
import body_check as bc
T = r'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_3/tools/route/bodies/'
U = r'C:/Users/tambe/AppData/Local/Temp/claude/604b57bd2ceda17d/52f614a9-b2f5-42ff-ae9c-6f659acff616/scratchpad/feas/u1-shift/'
M = json.load(open(T+'base.json')); D = json.load(open(T+'comps.json'))
M2 = json.load(open(U+'candidate_model.json')); D2 = json.load(open(U+'candidate_comps.json'))
print(M2.keys(), len(M2['pads']), len(M2['tracks']), len(M2['vias']))
def key(p): return (p['ref'], p['pad'])
a = {key(p): p for p in M['pads']}; b = {key(p): p for p in M2['pads']}
chg = collections.defaultdict(list)
for k in set(a)|set(b):
    pa, pb = a.get(k), b.get(k)
    if pa is None or pb is None: chg[k[0]].append(('added' if pa is None else 'removed', k[1])); continue
    if (pa['x'],pa['y'],pa['w'],pa['h'],pa['layers'],pa['net']) != (pb['x'],pb['y'],pb['w'],pb['h'],pb['layers'],pb['net']):
        chg[k[0]].append((k[1], round(pb['x']-pa['x'],3), round(pb['y']-pa['y'],3), pa['layers']!=pb['layers'], pa['net']!=pb['net']))
for r in sorted(chg):
    ds = collections.Counter((c[1],c[2]) if len(c)==5 else c[0] for c in chg[r])
    print(r, dict(ds), 'layerchg' if any(len(c)==5 and c[3] for c in chg[r]) else '', 'NETCHG' if any(len(c)==5 and c[4] for c in chg[r]) else '')
Ca = {c['ref']: c for c in D['comps']}; Cb = {c['ref']: c for c in D2['comps']}
for r in Cb:
    if Ca.get(r) != Cb[r]: print('comps diff', r, Ca.get(r), Cb[r])
for r in set(D2['mech'])|set(D['mech']):
    if D['mech'].get(r) != D2['mech'].get(r): print('mech diff', r, D['mech'].get(r), D2['mech'].get(r))
