import json, sys, copy
T = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools'
sys.path.insert(0, T)
import body_check as bc
from scan import fp, tobox
M = json.load(open(sys.argv[1])); cfg = json.load(open(sys.argv[2]))
D = copy.deepcopy(json.load(open(T + '/route/bodies/comps.json')))
C = {c['ref']: c for c in D['comps']}
for r, (x, y, rot) in cfg['caps'].items(): C[r]['rot'] = float(rot)
xs = [p for p in M['pads'] if p['ref'] == 'X4']
e = (min(p['x'] - p['w'] / 2 for p in xs), min(p['y'] - p['h'] / 2 for p in xs), max(p['x'] + p['w'] / 2 for p in xs), max(p['y'] + p['h'] / 2 for p in xs))
pads, body = fp(); bb = tobox(cfg['edge'], cfg['c'], body)
D['mech']['X4'] = {'side': cfg['side'], 'off': [bb[i] - e[i] for i in range(4)]}
C['X4']['layer'] = 'TOP' if cfg['side'] == 'Top' else 'BOTTOM'
print('X4 pad extent', [round(v, 3) for v in e], 'body', [round(v, 3) for v in bb])
P = bc.build(M, D)
gap = float(sys.argv[3]) if len(sys.argv) > 3 else 0.10
res = bc.check(P, set(cfg['caps']) | {'X4'}, gap)
w = {}
for r in res:
    k = r[:4]
    if k not in w or r[5] < w[k][5]: w[k] = r
for r in sorted(w.values(), key=lambda r: r[5]): print(r)
print('findings', len(w), 'at gap', gap)
# also connector pads vs other pads (0.2)
oth = [p for p in M['pads'] if p['ref'] != 'X4' and (p['layers'] is None or ('Top Layer' if cfg['side']=='Top' else 'Bottom Layer') in p['layers'])]
mn = min((bc.gap((a['x']-a['w']/2,a['y']-a['h']/2,a['x']+a['w']/2,a['y']+a['h']/2),(b['x']-b['w']/2,b['y']-b['h']/2,b['x']+b['w']/2,b['y']+b['h']/2)), b['ref'], b['pad'], a['pad']) for a in xs for b in oth)
print('closest foreign pad to X4 pads:', mn)
