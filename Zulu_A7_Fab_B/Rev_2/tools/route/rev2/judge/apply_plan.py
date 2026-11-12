"""Build base_moved - remove + plan with emit_copper's own matching; report misses/multi-hits, through vias on SMD
pads, USB lengths.  python apply.py <base_moved> <plan> <out_model>"""
import json, math, sys
STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
b = json.load(open(sys.argv[1])); P = json.load(open(sys.argv[2]))


def span(v):
    return v['span'] if 'span' in v else STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]


def tmatch(t, r):
    if t['net'] != r['net'] or t['layer'] != r['layer'] or abs(t['w'] - r['w']) >= 0.002:
        return False
    a = all(abs(p - q) < 0.002 for p, q in zip((t['x1'], t['y1'], t['x2'], t['y2']), (r['x1'], r['y1'], r['x2'], r['y2'])))
    c = all(abs(p - q) < 0.002 for p, q in zip((t['x1'], t['y1'], t['x2'], t['y2']), (r['x2'], r['y2'], r['x1'], r['y1'])))
    return a or c


kill = set(); bad = 0
for r in P['remove']:
    hits = [i for i, t in enumerate(b['tracks']) if tmatch(t, r)]
    if len(hits) != 1:
        bad += 1; print('track remove hits', len(hits), r)
    kill.update(hits)
killv = set()
for r in P['remove_vias']:
    sp = span(r)
    hits = [i for i, v in enumerate(b['vias']) if v['net'] == r['net'] and abs(v['hole'] - r['hole']) < 0.002 and
            abs(v['x'] - r['x']) < 0.002 and abs(v['y'] - r['y']) < 0.002 and span(v)[0] == sp[0] and span(v)[-1] == sp[-1]]
    if len(hits) != 1:
        bad += 1; print('via remove hits', len(hits), r)
    killv.update(hits)
print('remove tracks matched', len(kill), 'of', len(P['remove']), '; vias', len(killv), 'of', len(P['remove_vias']), '; bad', bad)
out = dict(b)
out['tracks'] = [t for i, t in enumerate(b['tracks']) if i not in kill] + P['tracks']
nv = [dict(v, span=span(v)) for v in P['vias']]
for v in nv:
    v.pop('from', None); v.pop('to', None)
out['vias'] = [v for i, v in enumerate(b['vias']) if i not in killv] + nv
json.dump(out, open(sys.argv[3], 'w'))
# duplicates in the plan
seen = {}
dup = 0
for t in P['tracks']:
    k = (t['net'], t['layer'], round(t['w'], 3), tuple(sorted([(round(t['x1'], 3), round(t['y1'], 3)), (round(t['x2'], 3), round(t['y2'], 3))])))
    dup += k in seen; seen[k] = 1
print('duplicate plan tracks', dup)
# through vias whose land overlaps any SMD pad (round lands for round pads)


def overlap(v, p):
    r = v['size'] / 2
    if p['shape'] in ('round', 'circle', 'ellipse') and abs(p['w'] - p['h']) < 1e-6:
        return math.hypot(v['x'] - p['x'], v['y'] - p['y']) < r + p['w'] / 2 - 1e-6
    rot = p.get('rot', 0) % 180
    w, h = (p['h'], p['w']) if abs(rot - 90) < 1 else (p['w'], p['h'])
    dx = max(abs(v['x'] - p['x']) - w / 2, 0); dy = max(abs(v['y'] - p['y']) - h / 2, 0)
    return math.hypot(dx, dy) < r - 1e-6


smd = [p for p in out['pads'] if not p.get('drill')]
thr = [v for v in out['vias'] if span(v)[0] == 'Top Layer' and span(v)[-1] == 'Bottom Layer']
hits = [(v['net'], v['x'], v['y'], p['ref'] + '-' + p['pad']) for v in thr for p in smd if overlap(v, p)]
print('through vias', len(thr), '; on SMD pads', len(hits), hits[:10])
newmv = [(v['net'], v['x'], v['y'], p['ref'] + '-' + p['pad']) for v in nv for p in smd
         if overlap(v, p) and (span(v)[0] in p['layers'] or span(v)[-1] in p['layers'])]
print('new vias touching an SMD pad on their own layer', len(newmv), newmv)
for n in ('USB_D_P', 'USB_D_N'):
    ts = [t for t in out['tracks'] if t['net'] == n]
    print(n, 'tracks', len(ts), 'layers', sorted({t['layer'] for t in ts}), 'len %.4f' % sum(math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) for t in ts),
          'widths', sorted({t['w'] for t in ts}), 'vias', sum(1 for v in out['vias'] if v['net'] == n))
print('model: tracks', len(out['tracks']), 'vias', len(out['vias']))
