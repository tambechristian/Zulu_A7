"""Find Top-side 0805 spots (pads clear of all Top parts and of Top copper of other nets) with the E-edge connector placed."""
from scan import *
import numpy as np
CX = 7.1
o, cu, pb, bb = evaluate('E', 'Top', CX)
MOVED = {'C140', 'C141', 'C142', 'C143', 'C144', 'C145', 'X4'}
obst_pad, obst_body = [], []
for ref, v in P['Top'].items():
    b = ref.split('[')[0]
    if b in MOVED: continue
    obst_pad += [x for x, _ in v['pads']]
    obst_body += v['body']
obst_pad += [b for _, b in pb]
obst_body += [bb]
def fp0805(x, y, rot):
    # pads 1.3 (along) x 1.5 (across) at +-0.85 along; body 2.0 x 1.25
    if rot == 90:
        pads = [(x - 0.75, y - 0.85 - 0.65, x + 0.75, y - 0.85 + 0.65), (x - 0.75, y + 0.85 - 0.65, x + 0.75, y + 0.85 + 0.65)]
        body = (x - 0.625, y - 1.0, x + 0.625, y + 1.0)
    else:
        pads = [(x - 0.85 - 0.65, y - 0.75, x - 0.85 + 0.65, y + 0.75), (x + 0.85 - 0.65, y - 0.75, x + 0.85 + 0.65, y + 0.75)]
        body = (x - 1.0, y - 0.625, x + 1.0, y + 0.625)
    return pads, body
TT = [t for t in M['tracks'] if t['layer'] == 'Top Layer']
VV = [v for v in M['vias'] if 'Top Layer' in v['span']]
def ok(x, y, rot, net1, extra=()):
    pads, body = fp0805(x, y, rot)
    for p in pads:
        if p[0] < 0.3 or p[1] < 0.3 or p[2] > W - 0.3 or p[3] > H - 0.3: return None
        for q in obst_pad + [e for e in extra]:
            if bc.gap(p, q) < PADGAP: return None
        for q in obst_body:
            if bc.gap(p, q) < BODYGAP: return None
    for q in obst_pad:
        if bc.gap(body, q) < BODYGAP: return None
    for q in obst_body:
        if bc.gap(body, q) < BODYGAP: return None
    # copper: count foreign (not GND / not net1) tracks and vias under the pads
    hit = 0; L = 0
    for i, p in enumerate(pads):
        own = net1 if i == 0 else 'GND'
        for t in TT:
            if t['net'] == own: continue
            if seg_box_gap(t, p) < CU: hit += 1; L += math.hypot(t['x2']-t['x1'], t['y2']-t['y1'])
        for v in VV:
            if v['net'] == own: continue
            dx = max(p[0] - v['x'], 0, v['x'] - p[2]); dy = max(p[1] - v['y'], 0, v['y'] - p[3])
            if math.hypot(dx, dy) - v['size'] / 2 < CU: hit += 1
    return hit, L
if __name__ == '__main__':
    res = []
    for xi in np.arange(1.0, 60.0, 0.1):
        for yi in np.arange(1.0, 24.5, 0.1):
            for rot in (0, 90):
                r = ok(round(xi, 2), round(yi, 2), rot, 'VCC1V0')
                if r is not None:
                    res.append((r[0], round(r[1], 2), round(xi, 2), round(yi, 2), rot))
    print(len(res), 'legal spots (body/pad-clear)')
    clean = [r for r in res if r[0] == 0]
    print(len(clean), 'with no foreign Top copper under the pads')
    # cluster
    import collections
    cl = collections.defaultdict(list)
    for r in clean: cl[(int(r[2] // 2), int(r[3] // 2))].append(r)
    for k in sorted(cl, key=lambda k: -len(cl[k])): print(k, len(cl[k]), cl[k][0], cl[k][-1])
    json.dump(res, open('free0805.json', 'w'))
