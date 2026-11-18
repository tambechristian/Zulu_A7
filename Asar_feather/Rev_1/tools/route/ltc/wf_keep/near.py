"""near.py model plan x0 y0 x1 y1 [layer]: list copper in a box."""
import json, sys
M = json.load(open(sys.argv[1]))
P = json.load(open(sys.argv[2])) if sys.argv[2] != '-' else {'tracks': [], 'vias': []}
x0, y0, x1, y1 = map(float, sys.argv[3:7])
lay = sys.argv[7] if len(sys.argv) > 7 else None
def inb(x, y): return x0 <= x <= x1 and y0 <= y <= y1
for src, D in (('M', M), ('P', P)):
    for i, t in enumerate(D['tracks']):
        if lay and t['layer'] != lay: continue
        # segment intersects box (sample)
        hit = any(inb(t['x1'] + (t['x2'] - t['x1']) * k / 20, t['y1'] + (t['y2'] - t['y1']) * k / 20) for k in range(21))
        if hit: print(src, 'T', i, t['net'], t['layer'][:3], t['w'], (t['x1'], t['y1']), (t['x2'], t['y2']))
    for i, v in enumerate(D['vias']):
        if inb(v['x'], v['y']): print(src, 'V', i, v['net'], v['x'], v['y'], v['size'], v['hole'], v.get('from'), v.get('to'), v.get('span'))
    for p in D.get('pads', []):
        if inb(p['x'], p['y']) and (not lay or lay in p['layers'] or 'Multi' in str(p['layers'])):
            print(src, 'P', p['ref'], p['pad'], p.get('net'), p['x'], p['y'], {k: p[k] for k in p if k not in ('ref', 'pad', 'net', 'x', 'y')})
