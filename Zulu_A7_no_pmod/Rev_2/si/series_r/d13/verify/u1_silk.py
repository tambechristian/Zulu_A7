"""u1_silk.py -- find legal positions for U1's visible designator ("U1", h 0.8001, stroke 0.1524, TopOverlay)
on the after-board of a plan: >= SilkToSolderMask 0.254 from every Top pad mask opening (plan pads included),
>= SilkToSilk 0.254 from every other visible overlay text, inside the board by >= 0.254.  Text box = anchor
bottom-left, width n*h*1.0 (conservative stroke advance) + stroke.  Writes u1_silk_<tag>.json/.log here.
Usage: python u1_silk.py --plan PLAN --tag TAG"""
import argparse, json, math, os

HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/')
SR = os.path.normpath(os.path.join(HERE, '..', '..')).replace('\\', '/')
ap = argparse.ArgumentParser()
ap.add_argument('--plan', required=True)
ap.add_argument('--tag', required=True)
A = ap.parse_args()
B = json.load(open(SR + '/board_extract.json'))
P = json.load(open(A.plan))
mil = 0.0254
rules = {r['NAME']: r for r in B['rules']}
S2M = float(rules['SilkToSolderMaskClearance']['MINSILKSCREENTOMASKGAP'][:-3]) * mil
S2S = float(rules['SilkToSilkClearance']['SILKTOSILKCLEARANCE'][:-3]) * mil
EXP = {'U1': float(rules['SolderMaskExpansion_U1']['EXPANSION'][:-3]) * mil,
       'X3': float(rules['SolderMaskExpansion_X3']['EXPANSION'][:-3]) * mil}
EXP_DEF = float(rules['SolderMaskExpansion']['EXPANSION'][:-3]) * mil

ops = []   # (kind, geom): ('rect', x0,y0,x1,y1) or ('circ', x, y, r)
for p in B['pads']:
    if p['layer'] not in ('Top', 'Multi'):
        continue
    e = EXP.get(p['ref'], EXP_DEF)
    if p['shape'] == 'round' and abs(p['w'] - p['h']) < 1e-9:
        ops.append(('circ', p['x'], p['y'], p['w'] / 2 + e, '%s-%s' % (p['ref'], p['pad'])))
    else:
        ops.append(('rect', p['x'] - p['w'] / 2 - e, p['y'] - p['h'] / 2 - e, p['x'] + p['w'] / 2 + e, p['y'] + p['h'] / 2 + e,
                    '%s-%s' % (p['ref'], p['pad'])))
for part in P.get('parts', []):
    if part['side'] != 'Top':
        continue
    for k in ('pad1', 'pad2'):
        q = part[k]
        ops.append(('rect', q['x'] - 0.15 - EXP_DEF, q['y'] - 0.15 - EXP_DEF, q['x'] + 0.15 + EXP_DEF, q['y'] + 0.15 + EXP_DEF,
                    '%s-%s' % (part['ref'], k[-1])))
texts = []
for t in B['texts']:
    if t['layer'] != 'TopOverlay' or t['hidden'] or (t['comp'] == 'U1' and t['designator']):
        continue
    n = max(1, len(t['text']))
    h, sw = t['height'], t.get('stroke') or 0.15
    w = n * h
    if int(round(t['rot'])) % 180 == 0:
        texts.append((t['x'] - sw / 2, t['y'] - sw / 2, t['x'] + w + sw / 2, t['y'] + h + sw / 2, t['text']))
    else:
        texts.append((t['x'] - h - sw / 2, t['y'] - sw / 2, t['x'] + sw / 2, t['y'] + w + sw / 2, t['text']))
u1 = next(t for t in B['texts'] if t['comp'] == 'U1' and t['designator'])
H, SW = u1['height'], u1['stroke']
W = 2 * H


def rect_rect(a, b):
    dx = max(a[0] - b[2], b[0] - a[2], 0)
    dy = max(a[1] - b[3], b[1] - a[3], 0)
    return math.hypot(dx, dy)


def rect_circ(a, x, y, r):
    dx = max(a[0] - x, x - a[2], 0)
    dy = max(a[1] - y, y - a[3], 0)
    return math.hypot(dx, dy) - r


def check(x, y):
    box = (x - SW / 2, y - SW / 2, x + W + SW / 2, y + H + SW / 2)
    if box[0] < S2M or box[1] < S2M or box[2] > 60.96 - S2M or box[3] > 25.4 - S2M:
        return None
    m1 = 9.0
    for o in ops:
        g = rect_circ(box, o[1], o[2], o[3]) if o[0] == 'circ' else rect_rect(box, o[1:5])
        m1 = min(m1, g)
        if g < S2M:
            return None
    m2 = min((rect_rect(box, t[:4]) for t in texts), default=9)
    if m2 < S2S:
        return None
    return m1, m2


log = []
log.append('U1 designator now at (%.4f, %.4f) h %.4f stroke %.4f; box %.3f x %.3f (conservative)' % (u1['x'], u1['y'], H, SW, W + SW, H + SW))
cur = check(u1['x'], u1['y'])
log.append('current position legal on this plan: %s' % (cur is not None))
cands = []
x = 36.0
while x <= 53.0:
    y = 10.0
    while y <= 24.5:
        r = check(x, y)
        if r:
            d = math.hypot(x - u1['x'], y - u1['y'])
            cands.append((round(d, 3), round(x, 3), round(y, 3), round(r[0], 4), round(r[1], 4)))
        y += 0.05
    x += 0.05
cands.sort()
log.append('%d legal anchors on a 0.05 grid in x 36-53, y 10-24.5; nearest 15 (dist, x, y, min mask gap, min silk gap):' % len(cands))
for c in cands[:15]:
    log.append('   %s' % (c,))
# a robust pick: maximise the worse of the two margins among anchors within 2 mm
near = [c for c in cands if c[0] <= 2.5]
best = max(near, key=lambda c: min(c[3] - S2M, c[4] - S2S)) if near else None
log.append('most robust anchor within 2.5 mm: %s' % (best,))
open(HERE + '/u1_silk_%s.log' % A.tag, 'w').write('\n'.join(log) + '\n')
json.dump(dict(current_legal=cur is not None, nearest=cands[:30], robust=best), open(HERE + '/u1_silk_%s.json' % A.tag, 'w'), indent=1)
print('\n'.join(log))
