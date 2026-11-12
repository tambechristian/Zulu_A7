"""isl.py <model.json> [plan ...] : islands of every open net (pads, track/via counts, bbox)"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import elib as E
M = E.load(sys.argv[1])
for p in sys.argv[2:]:
    P = E.load(p)
    M = E.apply(M, P.get('remove', []), P.get('remove_vias', []), P['tracks'], P['vias'])
I = E.C.islands(M)
oc = E.C.open_count(I)
for n, k in sorted(oc.items()):
    if not k:
        continue
    print(n, 'open', k)
    for g in I[n]:
        xs = [M['pads'][i]['x'] for i in g['pads']] + [M['tracks'][i]['x1'] for i in g['tracks']] + [M['vias'][i]['x'] for i in g['vias']]
        ys = [M['pads'][i]['y'] for i in g['pads']] + [M['tracks'][i]['y1'] for i in g['tracks']] + [M['vias'][i]['y'] for i in g['vias']]
        print('   pads', ['%s.%s' % (M['pads'][i]['ref'], M['pads'][i]['pad']) for i in g['pads']][:8], 't%d v%d' % (len(g['tracks']), len(g['vias'])),
              'plane' if g['plane'] else '', 'bbox %.2f,%.2f-%.2f,%.2f' % (min(xs), min(ys), max(xs), max(ys)) if xs else '')
