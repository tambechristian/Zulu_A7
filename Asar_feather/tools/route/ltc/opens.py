"""python opens.py <model.json> [plan.json ...]: open connections per net after merging plans (remove lists applied)."""
import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
import route_conn as C
M = json.load(open(sys.argv[1]))
k = lambda t: (t['net'], t['layer'], round(t['x1'], 3), round(t['y1'], 3), round(t['x2'], 3), round(t['y2'], 3))
for p in sys.argv[2:]:
    P = json.load(open(p))
    rm = {k(t) for t in P.get('remove', [])}
    M['tracks'] = [t for t in M['tracks'] if k(t) not in rm] + P['tracks']
    for v in P['vias']:
        v = dict(v)
        if 'span' not in v:
            S = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
            v['span'] = S[S.index(v['from']):S.index(v['to']) + 1]
        M['vias'].append(v)
I = C.islands(M)
op = {n: len([i for i in v if i['pads']]) - 1 for n, v in I.items()}
op = {n: c for n, c in op.items() if c > 0}
print(sum(op.values()), op)
