import json
import sys
sys.path.insert(0, '.')
import geo

M = json.load(open(sys.argv[1] if len(sys.argv) > 1 else 'model_a.json'))
P = json.load(open(sys.argv[2] if len(sys.argv) > 2 else 'plan_a.json'))
for t in P['tracks']:
    print('T %-9s %.4f (%.4f,%.4f)-(%.4f,%.4f)' % (t['net'], t['w'], t['x1'], t['y1'], t['x2'], t['y2']), geo.track_report(M, t, 3))
for v in P['vias']:
    sp = geo.STACK[geo.STACK.index(v['from']):geo.STACK.index(v['to']) + 1]
    print('V %-9s (%.4f,%.4f) %s-%s' % (v['net'], v['x'], v['y'], sp[0][:3], sp[-1][:3]),
          geo.via_report(M, v['net'], v['x'], v['y'], v['size'], v['hole'], sp, 3))
# moved pads vs everything on Bottom
for p in M['pads']:
    if p['ref'] in ('JP3', 'JP4'):
        r = []
        for k, o in geo.items_on(M, 'Bottom Layer'):
            if o.get('net') == p['net'] or (k == 'p' and o is p):
                continue
            if k == 'p':
                d = geo.C.pad_point(o, p['x'], p['y']) - 0.5
            elif k == 't':
                d = geo.C.seg_dist(o['x1'], o['y1'], o['x2'], o['y2'], p['x'], p['y']) - 0.5 - o['w'] / 2
            else:
                import math
                d = math.hypot(o['x'] - p['x'], o['y'] - p['y']) - 0.5 - o['size'] / 2
            r.append((round(d, 4), k, o.get('net') or o.get('ref'), o.get('ref', '')))
        r.sort()
        print('PAD %s-%s %s (%.3f,%.3f)' % (p['ref'], p['pad'], p['net'], p['x'], p['y']), r[:3])
