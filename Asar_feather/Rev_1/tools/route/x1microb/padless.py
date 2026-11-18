"""Pad-less copper components (planes do NOT join objects): leftover stubs that DRC's antenna check misses when
both ends land on plane-tied vias. python padless.py model.json [model.json ...]"""
import json, sys
sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1/tools')
sys.path.insert(0, '.')
import route_conn_all as C
for f in sys.argv[1:]:
    M = json.load(open(f))
    M2 = dict(M, planes={})
    I = C.islands(M2)
    out = []
    for net, isl in I.items():
        for g in isl:
            if not g['pads'] and (len(g['tracks']) > 0):
                xs = [M['tracks'][i]['x1'] for i in g['tracks']] + [M['vias'][i]['x'] for i in g['vias']]
                ys = [M['tracks'][i]['y1'] for i in g['tracks']] + [M['vias'][i]['y'] for i in g['vias']]
                out.append((net, len(g['tracks']), len(g['vias']), round(min(xs), 2), round(min(ys), 2)))
    print(f, 'pad-less components with tracks:', len(out))
    for o in sorted(out): print('  ', o)
