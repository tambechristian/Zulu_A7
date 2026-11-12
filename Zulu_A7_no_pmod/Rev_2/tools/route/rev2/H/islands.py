"""islands.py <model.json> <plan.json> [nets]: islands of each open net (pads, track count, layers, bbox) for model + plan"""
import json, sys
sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools')
import route_conn as C
import compose_plan as CP
M = json.load(open(sys.argv[1]))
P = json.load(open(sys.argv[2])); P.setdefault('remove', []); P.setdefault('remove_vias', [])
Mx = CP.apply(M, P)
want = set(sys.argv[3].split(',')) if len(sys.argv) > 3 else None
isl = C.islands(Mx)
oc = C.open_count(isl)
for n in sorted(oc):
    if want and n not in want: continue
    print('==', n, 'open', oc[n])
    for g in isl[n]:
        pads = ['%s-%s(%.2f,%.2f)' % (Mx['pads'][i]['ref'], Mx['pads'][i]['pad'], Mx['pads'][i]['x'], Mx['pads'][i]['y']) for i in g['pads']]
        xs = [Mx['tracks'][i]['x1'] for i in g['tracks']] + [Mx['tracks'][i]['x2'] for i in g['tracks']] + [Mx['pads'][i]['x'] for i in g['pads']]
        ys = [Mx['tracks'][i]['y1'] for i in g['tracks']] + [Mx['tracks'][i]['y2'] for i in g['tracks']] + [Mx['pads'][i]['y'] for i in g['pads']]
        lay = sorted({Mx['tracks'][i]['layer'] for i in g['tracks']})
        print('   pads', pads[:8], 'tracks', len(g['tracks']), 'vias', len(g['vias']), 'layers', lay,
              'bbox %.2f,%.2f-%.2f,%.2f' % (min(xs), min(ys), max(xs), max(ys)) if xs else '', 'plane' if g['plane'] else '')
