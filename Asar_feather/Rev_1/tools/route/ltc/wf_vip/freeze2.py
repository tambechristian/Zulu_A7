"""freeze2.py <model> <plan> <out>: like scratchpad freeze.py, plus 'remove_vias'."""
import json, sys
M = json.load(open(sys.argv[1])); P = json.load(open(sys.argv[2]))
ST = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
def key(t):
    return (t['net'], t['layer'], frozenset({(round(t['x1'], 3), round(t['y1'], 3)), (round(t['x2'], 3), round(t['y2'], 3))}))
rm = {key(r) for r in P.get('remove', [])}
n0 = len(M['tracks'])
M['tracks'] = [t for t in M['tracks'] if key(t) not in rm]
rv = [(r['net'], round(r['x'], 3), round(r['y'], 3), round(r['hole'], 3)) for r in P.get('remove_vias', [])]
v0 = len(M['vias'])
M['vias'] = [v for v in M['vias'] if (v['net'], round(v['x'], 3), round(v['y'], 3), round(v['hole'], 3)) not in rv]
def fix(v):
    v = dict(v)
    if 'span' not in v:
        a, b = sorted((ST.index(v['from']), ST.index(v['to'])))
        v['span'] = ST[a:b + 1]
    return v
M['tracks'] += P['tracks']; M['vias'] += [fix(v) for v in P['vias']]
json.dump(M, open(sys.argv[3], 'w'))
print('removed tracks', n0 - len(M['tracks']) + len(P['tracks']), 'removed vias', v0 - len(M['vias']) + len(P['vias']))
