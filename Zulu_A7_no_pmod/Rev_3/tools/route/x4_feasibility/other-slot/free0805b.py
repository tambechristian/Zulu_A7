from scan import *
import numpy as np, collections
sys.path.insert(0, T)
import route_conn as RC
CX = 7.1
o, cu, pb, bb = evaluate('E', 'Top', CX, copper=False)
MOVED = {'C140', 'C141', 'C142', 'C143', 'C144', 'C145', 'X4'}
obst_pad, obst_body = [], []
for ref, v in P['Top'].items():
    b = ref.split('[')[0]
    if b in MOVED: continue
    obst_pad += [x for x, _ in v['pads']]; obst_body += v['body']
obst_pad += [b for _, b in pb]; obst_body += [bb]
OP = np.array(obst_pad); OB = np.array(obst_body)
def gapv(b, A):
    dx = np.maximum(A[:, 0] - b[2], b[0] - A[:, 2]); dy = np.maximum(A[:, 1] - b[3], b[1] - A[:, 3])
    ov = (dx < 0) & (dy < 0)
    return np.where(ov, np.maximum(dx, dy), np.hypot(np.maximum(dx, 0), np.maximum(dy, 0)))
TT = [t for t in M['tracks'] if t['layer'] == 'Top Layer']
TB = np.array([(min(t['x1'], t['x2']) - t['w'] / 2, min(t['y1'], t['y2']) - t['w'] / 2, max(t['x1'], t['x2']) + t['w'] / 2, max(t['y1'], t['y2']) + t['w'] / 2) for t in TT])
VV = [v for v in M['vias'] if 'Top Layer' in v['span']]
def fp0805(x, y, rot):
    if rot == 90:
        return [(x - 0.75, y - 1.5, x + 0.75, y - 0.2), (x - 0.75, y + 0.2, x + 0.75, y + 1.5)], (x - 0.625, y - 1.0, x + 0.625, y + 1.0)
    return [(x - 1.5, y - 0.75, x - 0.2, y + 0.75), (x + 0.2, y - 0.75, x + 1.5, y + 0.75)], (x - 1.0, y - 0.625, x + 1.0, y + 0.625)
def legal(x, y, rot):
    pads, body = fp0805(x, y, rot)
    for p in pads:
        if p[0] < 0.3 or p[1] < 0.3 or p[2] > W - 0.3 or p[3] > H - 0.3: return False
        if (gapv(p, OP) < PADGAP).any() or (gapv(p, OB) < BODYGAP).any(): return False
    if (gapv(body, OP) < BODYGAP).any() or (gapv(body, OB) < BODYGAP).any(): return False
    return True
def copper(x, y, rot, net1):
    pads, body = fp0805(x, y, rot); hits = []
    for i, p in enumerate(pads):
        own = net1 if i == 0 else 'GND'
        pd = {'ref': 'C', 'shape': 'rect', 'x': (p[0] + p[2]) / 2, 'y': (p[1] + p[3]) / 2, 'w': p[2] - p[0], 'h': p[3] - p[1]}
        near = np.nonzero(gapv(p, TB) < CU)[0]
        for k in near:
            t = TT[k]
            if t['net'] != own and RC.pad_seg(pd, (t['x1'], t['y1'], t['x2'], t['y2'])) - t['w'] / 2 < CU: hits.append(t['net'])
        for v in VV:
            if v['net'] != own and RC.pad_point(pd, v['x'], v['y']) - v['size'] / 2 < CU: hits.append(v['net'] + '(via)')
    return hits
res = []
for xi in np.arange(1.0, 60.0, 0.2):
    for yi in np.arange(1.0, 24.5, 0.2):
        for rot in (0, 90):
            x, y = round(float(xi), 2), round(float(yi), 2)
            if legal(x, y, rot):
                res.append((x, y, rot, copper(x, y, rot, 'VCC1V0')))
print(len(res), 'legal')
clean = [r for r in res if not r[3]]
print(len(clean), 'clean (no foreign Top copper; VCC1V0 assumed for pad 1)')
cl = collections.defaultdict(list)
for r in clean: cl[(int(r[0] // 3) * 3, int(r[1] // 3) * 3)].append(r)
for k in sorted(cl): print(k, len(cl[k]), cl[k][0][:3], cl[k][-1][:3])
json.dump(res, open('free0805.json', 'w'))
