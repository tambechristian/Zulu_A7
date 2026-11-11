"""python islands.py <tools dir> <model> <plan> NET...: islands of each net after merging a plan (pads + extents)."""
import json, sys
sys.path.insert(0, sys.argv[1])
import route_conn as C
M = json.load(open(sys.argv[2])); P = json.load(open(sys.argv[3]))
S = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
M['tracks'] += P['tracks']
for v in P['vias']:
    v = dict(v); v.setdefault('span', S[S.index(v['from']):S.index(v['to']) + 1]); M['vias'].append(v)
I = C.islands(M)
for n in sys.argv[4:]:
    print('==', n)
    for g in I[n]:
        pads = [(M['pads'][i]['ref'], M['pads'][i]['pad'], round(M['pads'][i]['x'], 2), round(M['pads'][i]['y'], 2), M['pads'][i]['layers'][0][:3]) for i in g['pads']]
        xs = [M['tracks'][i]['x1'] for i in g['tracks']] + [M['tracks'][i]['x2'] for i in g['tracks']]
        ys = [M['tracks'][i]['y1'] for i in g['tracks']] + [M['tracks'][i]['y2'] for i in g['tracks']]
        ext = (round(min(xs), 1), round(min(ys), 1), round(max(xs), 1), round(max(ys), 1)) if xs else None
        print('  pads', pads[:6], '+%d' % max(0, len(pads) - 6), 'tracks', len(g['tracks']), 'vias', len(g['vias']), 'ext', ext, 'plane', g['plane'])
