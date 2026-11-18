"""frz.py model plan out : merge plan (remove, remove_vias) into model as fixed copper"""
import json, sys
M = json.load(open(sys.argv[1])); P = json.load(open(sys.argv[2]))
ST = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
def k(t):
    return (t['net'], t['layer'], frozenset({(round(t['x1'], 3), round(t['y1'], 3)), (round(t['x2'], 3), round(t['y2'], 3))}))
rk = {k(r) for r in P.get('remove', [])}
M['tracks'] = [t for t in M['tracks'] if k(t) not in rk]
rv = [(r['net'], round(r['x'], 3), round(r['y'], 3), r['hole']) for r in P.get('remove_vias', [])]
M['vias'] = [v for v in M['vias'] if (v['net'], round(v['x'], 3), round(v['y'], 3), v['hole']) not in rv]
def fix(v):
    v = dict(v)
    if 'span' not in v:
        a, b = sorted((ST.index(v['from']), ST.index(v['to'])))
        v['span'] = ST[a:b + 1]
    return v
M['tracks'] += P['tracks']; M['vias'] += [fix(v) for v in P['vias']]
json.dump(M, open(sys.argv[3], 'w'))
print('tracks', len(M['tracks']), 'vias', len(M['vias']))
