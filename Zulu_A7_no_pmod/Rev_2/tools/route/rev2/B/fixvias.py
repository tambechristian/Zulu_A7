"""fixvias.py <route_in> <route_out> x,y[:dx,dy] ...  replace a through GND/VCC tie via at x,y by a Bottom>L5>L4>L3>L2
microvia column (no Top land); with :nx,ny the through via instead moves to nx,ny and the plan tracks ending at x,y
are re-ended there (a straight stretch, checked by route_check afterwards)."""
import json, sys
P = json.load(open(sys.argv[1]))
for arg in sys.argv[3:]:
    xy, _, mv = arg.partition(':')
    x, y = map(float, xy.split(','))
    hit = [v for v in P['vias'] if abs(v['x'] - x) < 1e-3 and abs(v['y'] - y) < 1e-3 and v['from'] == 'Top Layer' and v['to'] == 'Bottom Layer']
    assert len(hit) == 1, arg
    v = hit[0]
    P['vias'].remove(v)
    if mv:
        nx, ny = map(float, mv.split(','))
        P['vias'].append(dict(v, x=nx, y=ny))
        for t in P['tracks']:
            for a, b in (('x1', 'y1'), ('x2', 'y2')):
                if t['net'] == v['net'] and abs(t[a] - x) < 1e-3 and abs(t[b] - y) < 1e-3:
                    t[a], t[b] = nx, ny
    else:
        for f, t_, s in (('L5-VCC3V3', 'Bottom Layer', 0.3), ('L4-SIG', 'L5-VCC3V3', 0.3), ('L3-SIG', 'L4-SIG', 0.27), ('L2-GND', 'L3-SIG', 0.3)):
            P['vias'].append({'net': v['net'], 'x': x, 'y': y, 'size': s, 'hole': 0.15, 'from': f, 'to': t_})
json.dump(P, open(sys.argv[2], 'w'), indent=1)
