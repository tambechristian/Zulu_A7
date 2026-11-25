"""sites.py model.json REF radius step [rots: 0,90] [side]
For each displacement (dx,dy) on a grid within radius and each extra rotation, move REF's pads (rigidly, rotated
about the pad-extent centre), then score: body/pad conflicts (body_check rules: body-body gap >= 0.15, body over other pad
gap >= 0.10, pad-pad gap >= 0.15 for different parts), edge 0.30, and the copper to rip: other-net tracks/vias on the
part's outer layer within 0.09 of a pad, and ANY via whose land touches a pad (through/microvia in pad)."""
import json, sys, math, copy
sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_4/tools')
import body_check as BC

mp, REF, RAD, STEP = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
ROTS = [int(r) for r in (sys.argv[5] if len(sys.argv) > 5 else '0').split(',')]
M = json.load(open(mp))
D = json.load(open(BC.COMPS)); C = {c['ref']: c for c in D['comps']}
FLIP = len(sys.argv) > 6 and sys.argv[6] == 'flip'
if FLIP:
    C[REF]['layer'] = 'TOP' if C[REF]['layer'] == 'BOTTOM' else 'BOTTOM'
side = 'Top' if C[REF]['layer'] == 'TOP' else 'Bottom'
LAY = 'Top Layer' if side == 'Top' else 'Bottom Layer'
W, H = M['board']['w'], M['board']['h']
mine = [p for p in M['pads'] if p['ref'] == REF]
if FLIP:
    mx = sum(p['x'] for p in mine) / len(mine)
    mine = [dict(p, x=2 * mx - p['x'], layers=['Top Layer' if side == 'Top' else 'Bottom Layer']) for p in mine]
e = BC.ext([(p['x'] - p['w'] / 2, p['y'] - p['h'] / 2, p['x'] + p['w'] / 2, p['y'] + p['h'] / 2) for p in mine])
cx, cy = (e[0] + e[2]) / 2, (e[1] + e[3]) / 2
others = [p for p in M['pads'] if p['ref'] != REF]


def seg_d(px, py, t):
    x1, y1, x2, y2 = t['x1'], t['y1'], t['x2'], t['y2']
    dx, dy = x2 - x1, y2 - y1
    L = dx * dx + dy * dy
    u = 0 if L == 0 else max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / L))
    return math.hypot(px - x1 - u * dx, py - y1 - u * dy)


def box_pt(b, x, y):
    return math.hypot(max(b[0] - x, 0, x - b[2]), max(b[1] - y, 0, y - b[3]))


def box_seg(b, t):
    # distance from box to segment (sampled)
    n = max(2, int(math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) / 0.05))
    return min(box_pt(b, t['x1'] + (t['x2'] - t['x1']) * i / n, t['y1'] + (t['y2'] - t['y1']) * i / n) for i in range(n + 1))


tracks = [t for t in M['tracks'] if t['layer'] == LAY]
vias = [v for v in M['vias'] if LAY in v['span']]
res = []
nearrefs = {p['ref'] for p in others if abs(p['x'] - cx) < RAD + 12 and abs(p['y'] - cy) < RAD + 12}
near = [p for p in others if p['ref'] in nearrefs]
others = near
base_rot = C[REF]['rot']
steps = int(RAD / STEP)
for rot in ROTS:
    for i in range(-steps, steps + 1):
        for j in range(-steps, steps + 1):
            dx, dy = i * STEP, j * STEP
            if math.hypot(dx, dy) > RAD + 1e-9:
                continue
            new = []
            for p in mine:
                q = dict(p)
                rx, ry = p['x'] - cx, p['y'] - cy
                if rot == 90:
                    rx, ry = -ry, rx
                    q['w'], q['h'] = p['h'], p['w']
                q['x'], q['y'] = round(cx + rx + dx, 4), round(cy + ry + dy, 4)
                new.append(q)
            boxes = [((q['x'] - q['w'] / 2, q['y'] - q['h'] / 2, q['x'] + q['w'] / 2, q['y'] + q['h'] / 2), q) for q in new]
            if any(b[0] < 0.3 or b[1] < 0.3 or b[2] > W - 0.3 or b[3] > H - 0.3 for b, _ in boxes):
                continue
            MM = {'pads': near + new}
            C[REF]['rot'] = (base_rot + rot) % 360
            parts = BC.build(MM, D)
            C[REF]['rot'] = base_rot
            bad = [r for r in BC.check(parts, {REF}, 0.15) if not (r[1] == 'body_pad' and r[5] >= 0.10)]
            # pad-pad
            for b, q in boxes:
                for p in others:
                    if (LAY in (p['layers'] or BC.STACK)):
                        pb = (p['x'] - p['w'] / 2, p['y'] - p['h'] / 2, p['x'] + p['w'] / 2, p['y'] + p['h'] / 2)
                        if BC.gap(b, pb) < 0.15:
                            bad.append((side, 'pad_pad', REF, p['ref'], p['pad'], round(BC.gap(b, pb), 3)))
            if bad:
                continue
            rip_t, rip_v, vip = set(), set(), 0
            for b, q in boxes:
                for k, t in enumerate(tracks):
                    if t['net'] != q['net'] and box_seg(b, t) < t['w'] / 2 + 0.09:
                        rip_t.add(k)
                for k, v in enumerate(vias):
                    d = box_pt(b, v['x'], v['y'])
                    if d < v['size'] / 2 + (0.09 if v['net'] != q['net'] else 0):
                        rip_v.add(k)
            res.append((len(rip_v), len(rip_t), round(math.hypot(dx, dy), 3), rot, round(dx, 3), round(dy, 3)))
res.sort()
print(REF, side, 'centre', round(cx, 3), round(cy, 3), 'legal sites', len(res))
for r in res:
    print('vias_hit %d tracks_hit %d dist %.3f rot +%d  d=(%.3f, %.3f)' % r)
