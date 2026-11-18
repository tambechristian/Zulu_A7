"""freespot.py <placed model.json> REF fp x0 x1 y0 y1 [ignore_nets comma] [skip_refs comma]
Scan Bottom positions (0.05 grid, rot 0/90) where footprint fp fits: pads >= 0.2 from other pads,
>= 0.1 from other-net tracks/vias on Bottom (nets in ignore list are treated as removable)."""
import json, math, sys
sys.path.insert(0, '..')
import importlib.util
spec = importlib.util.spec_from_file_location('pc', '../place_check.py')
pc = importlib.util.module_from_spec(spec); spec.loader.exec_module(pc)
M = json.load(open(sys.argv[1])); ref = sys.argv[2]; fp = sys.argv[3]
x0, x1, y0, y1 = map(float, sys.argv[4:8])
ign = set(sys.argv[8].split(',')) if len(sys.argv) > 8 and sys.argv[8] else set()
skip = set(sys.argv[9].split(',')) if len(sys.argv) > 9 else set()
nets = {(p['ref'], p['pad']): p['net'] for p in M['pads']}
pc.PARTS[ref] = fp
L = 'Bottom Layer'
pads = [p for p in M['pads'] if p['ref'] != ref and p['ref'] not in skip and (L in p['layers'] or p.get('drill', 0) > 0)]
trs = [t for t in M['tracks'] if t['layer'] == L and t['net'] not in ign]
vis = [v for v in M['vias'] if L in v['span'] and v['net'] not in ign]
res = []
x = x0
while x <= x1:
    y = y0
    while y <= y1:
        for rot in (0, 90):
            ok = True
            for p in pc.pads_of(ref, 'B', x, y, rot, nets):
                for q in pads:
                    if abs(q['x'] - p['x']) > 3 or abs(q['y'] - p['y']) > 3: continue
                    if pc.rect_gap(p, q) < 0.2: ok = False; break
                if not ok: break
                for t in trs:
                    if t['net'] == p['net']: continue
                    if min(t['x1'], t['x2']) - 2 > p['x'] or max(t['x1'], t['x2']) + 2 < p['x']: continue
                    if min(t['y1'], t['y2']) - 2 > p['y'] or max(t['y1'], t['y2']) + 2 < p['y']: continue
                    if pc.seg_rect_gap(t, p) < 0.1: ok = False; break
                if not ok: break
                for v in vis:
                    if v['net'] == p['net']: continue
                    dx = max(abs(v['x'] - p['x']) - p['w'] / 2, 0); dy = max(abs(v['y'] - p['y']) - p['h'] / 2, 0)
                    if math.hypot(dx, dy) - v['size'] / 2 < 0.1: ok = False; break
                if not ok: break
            if ok: res.append((round(x, 3), round(y, 3), rot))
        y += 0.05
    x += 0.05
print(len(res))
# cluster print
import collections
C = collections.Counter((round(r[0]*2)/2, round(r[1]*2)/2, r[2]) for r in res)
for k in sorted(C): print(k, C[k])
