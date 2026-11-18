"""freeze2.py <model> <plan> <out>: like scratchpad freeze.py, plus 'remove_vias'."""
import json, sys
M = json.load(open(sys.argv[1])); P = json.load(open(sys.argv[2]))
rm = {json.dumps(r, sort_keys=True) for r in P.get('remove', [])}
n0 = len(M['tracks'])
M['tracks'] = [t for t in M['tracks'] if json.dumps(t, sort_keys=True) not in rm]
rv = P.get('remove_vias', [])
v0 = len(M['vias'])
M['vias'] = [v for v in M['vias'] if not any(v['net'] == r['net'] and abs(v['x'] - r['x']) < 2e-3 and abs(v['y'] - r['y']) < 2e-3 and abs(v['hole'] - r['hole']) < 2e-3 for r in rv)]
ST = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
def fix(v):
    v = dict(v)
    if 'span' not in v:
        a, b = sorted((ST.index(v['from']), ST.index(v['to'])))
        v['span'] = ST[a:b + 1]
    return v
M['tracks'] += P['tracks']; M['vias'] += [fix(v) for v in P['vias']]
json.dump(M, open(sys.argv[3], 'w'))
print('tracks removed', n0 - len(M['tracks']) + len(P['tracks']), 'vias removed', v0 - len(M['vias']) + len(P['vias']), 'now', len(M['tracks']), len(M['vias']))
