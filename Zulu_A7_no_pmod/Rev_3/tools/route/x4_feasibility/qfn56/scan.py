"""Scan legal FT2232H-56Q placements against the released board copper."""
import json
import sys

TOOLS = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_3/tools'
sys.path.insert(0, TOOLS)
import body_check as BC  # noqa: E402
import route_conn as C  # noqa: E402

M = json.load(open(TOOLS + '/route/bodies/base.json'))
P0 = json.load(open(TOOLS + '/route/x4_feasibility/qfn56/newpads_14.0_31.475_30.48.json'))
U20 = P0['u2']
X40 = P0['x4']
U2NETS = {p['net'] for p in M['pads'] if p['ref'] == 'U2' and p['net']}
SDRAM = set(
    ['D%d' % i for i in range(16)] + ['SDRAM-D%d' % i for i in range(16)] +
    ['A%d' % i for i in range(13)] +
    ['BS0', 'BS1', 'CAS#', 'RAS#', 'WE#', 'CKE', 'LDQM', 'UDQM', 'SDRAM-CS#', 'SDRAM-CLK']
)
CLR = 0.11
CX = 31.39


def inside(x, y):
    return 23.0 < x < 40.0 and 7.5 < y < 21.5


tracks = [
    t for t in M['tracks']
    if t['layer'] == 'Top Layer' and t['net'] not in U2NETS and
    (inside(t['x1'], t['y1']) or inside(t['x2'], t['y2']) or
     inside((t['x1'] + t['x2']) / 2, (t['y1'] + t['y2']) / 2))
]
vias = [
    v for v in M['vias']
    if 'Top Layer' in v['span'] and v['net'] not in U2NETS and inside(v['x'], v['y'])
]
x1 = [p for p in M['pads'] if p['ref'] == 'X1']
x4 = [dict(p, x=p['x'] + CX - 30.48) for p in X40]
x4_body = (CX - 3.95, 0.5, CX + 3.95, 8.1)


def box(p):
    return (
        p['x'] - p['w'] / 2, p['y'] - p['h'] / 2,
        p['x'] + p['w'] / 2, p['y'] + p['h'] / 2,
    )


def u2pads(xc, yc):
    return [dict(p, x=p['x'] + xc - 31.475, y=p['y'] + yc - 14.0) for p in U20]


results = []
for xi in range(33):
    xc = 29.5 + 0.125 * xi
    for yi in range(17):
        yc = 14.0 + 0.125 * yi
        pads = u2pads(xc, yc)
        u2_body = (xc - 4.0, yc - 4.0, xc + 4.0, yc + 4.0)
        if BC.gap(u2_body, x4_body) < 0.10:
            continue
        if min(
            C.pad_point(q, p['x'], p['y']) - min(p['w'], p['h']) / 2
            for q in pads for p in x1
        ) < 0.11:
            continue
        if min(BC.gap(box(q), box(p)) for q in pads for p in x4) < 0.11:
            continue
        bad = set()
        nets = set()
        for t in tracks:
            seg = (t['x1'], t['y1'], t['x2'], t['y2'])
            for p in pads:
                if (p['net'] != t['net'] or not p['net']) and C.pad_seg(p, seg) - t['w'] / 2 < CLR:
                    bad.add(('t', id(t)))
                    nets.add(t['net'])
                    break
        for v in vias:
            for p in pads:
                if (p['net'] != v['net'] or not p['net']) and C.pad_point(p, v['x'], v['y']) - v['size'] / 2 < CLR:
                    bad.add(('v', id(v)))
                    nets.add(v['net'])
                    break
        results.append((
            len(nets & SDRAM), len(nets), len(bad),
            round(xc, 4), round(yc, 4), sorted(nets),
        ))

results.sort(key=lambda r: r[:3])
print('tracks', len(tracks), 'vias', len(vias), 'legal', len(results))
for row in results[:30]:
    print(row)
