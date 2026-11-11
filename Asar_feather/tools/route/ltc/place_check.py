"""LTC3556 power-block placement checker (2026-11-10).

    python place_check.py <model.json> <placement.json> <out.png> [x0 x1 y0 y1]

placement.json: {"REF": [side, x, y, rot], ...} with side "B"/"T", (x, y) the footprint origin in board mm, rot in
degrees. Pads are generated from the library geometry below (Bottom: board = c + Rot(rot)(lx, -ly); Top: + (lx, ly)),
the parts' old pads are dropped from the model, and every placed pad is checked against
  - pads of other parts on the same side (and drilled pads on any side): >= GAP mm edge to edge,
  - copper of OTHER nets on the same outer layer (tracks, vias): >= CLR mm,
  - the board edge: >= EDGE mm.
Writes the placed model next to the png (same name, .json) for the router.
"""
import json
import math
import sys

GAP, CLR, EDGE = 0.20, 0.10, 0.30
QFN = ([(str(i), -1.90, 1.75 - 0.5 * (i - 1), 0.70, 0.25) for i in range(1, 9)] +
       [(str(i), -1.25 + 0.5 * (i - 9), -2.40, 0.25, 0.70) for i in range(9, 15)] +
       [(str(i), 1.90, -1.75 + 0.5 * (i - 15), 0.70, 0.25) for i in range(15, 23)] +
       [(str(i), 1.25 - 0.5 * (i - 23), 2.40, 0.25, 0.70) for i in range(23, 29)] + [('29', 0, 0, 2.65, 3.65)])
FP = {'QFN28-UFD-4X5': QFN,
      'R0201': [('1', -0.3, 0, 0.3, 0.3), ('2', 0.3, 0, 0.3, 0.3)], 'C0201': [('1', -0.3, 0, 0.3, 0.3), ('2', 0.3, 0, 0.3, 0.3)],
      'R0402': [('1', -0.65, 0, 0.7, 0.9), ('2', 0.65, 0, 0.7, 0.9)], 'C0402': [('1', -0.65, 0, 0.7, 0.9), ('2', 0.65, 0, 0.7, 0.9)],
      'C0603': [('1', -0.85, 0, 1.1, 1.0), ('2', 0.85, 0, 1.1, 1.0)],
      'C0805': [('1', -0.85, 0, 1.3, 1.5), ('2', 0.85, 0, 1.3, 1.5)],
      'IND2520': [('1', -1.175, 0, 1.05, 2.3), ('2', 1.175, 0, 1.05, 2.3)],
      'SOT23-5': [('1', -0.95, -1.25, 0.6, 1.1), ('2', 0.0, -1.25, 0.6, 1.1), ('3', 0.95, -1.25, 0.6, 1.1),
                  ('4', 0.95, 1.25, 0.6, 1.1), ('5', -0.95, 1.25, 0.6, 1.1)]}
# 2026-11-10 (SC189A back): U7 + L3 (its 1.5 uH) + C149 (0805 in) + C84 (out); L9/C168 the unloaded Buck1 slot, C167
# the VIN1 cap; R111/R112/C162 gone
PARTS = {'U8': 'QFN28-UFD-4X5', 'L1': 'IND2520', 'L2': 'IND2520', 'L3': 'IND2520', 'L8': 'IND2520', 'L9': 'IND2520',
         'U7': 'SOT23-5',
         'C78': 'C0805', 'C80': 'C0805', 'C82': 'C0603', 'C84': 'C0603', 'C147': 'C0603', 'C148': 'C0603', 'C149': 'C0805',
         'C150': 'C0603', 'C151': 'C0603', 'C160': 'C0402', 'C161': 'C0402', 'C163': 'C0201', 'C164': 'C0201',
         'C165': 'C0201', 'C166': 'C0201', 'C167': 'C0402', 'C168': 'C0603', 'R102': 'R0402', 'R103': 'R0402',
         'R107': 'R0402', 'R108': 'R0402', 'R113': 'R0201', 'R114': 'R0201', 'R115': 'R0201', 'R116': 'R0201',
         'R117': 'R0201', 'R118': 'R0201', 'LD3': 'LED0603', 'LD4': 'LED0603'}


def pads_of(ref, side, x, y, rot, nets):
    a = math.radians(rot)
    out = []
    for name, lx, ly, w, h in FP[PARTS[ref]]:
        ly2 = -ly if side == 'B' else ly
        px = x + lx * math.cos(a) - ly2 * math.sin(a)
        py = y + lx * math.sin(a) + ly2 * math.cos(a)
        if round(rot) % 180:
            w, h = h, w
        out.append({'ref': ref, 'pad': name, 'net': nets.get((ref, name), ''), 'x': round(px, 4), 'y': round(py, 4),
                    'shape': 'rect', 'w': w, 'h': h, 'layers': ['Bottom Layer' if side == 'B' else 'Top Layer'],
                    'drill': 0.0, 'plated': False})
    return out


def rect_gap(a, b):
    dx = abs(a['x'] - b['x']) - (a['w'] + b['w']) / 2
    dy = abs(a['y'] - b['y']) - (a['h'] + b['h']) / 2
    if dx < 0 and dy < 0:
        return max(dx, dy)
    return math.hypot(max(dx, 0), max(dy, 0))


def seg_rect_gap(t, p):
    # distance from a track centreline segment to a rectangle, minus half width (sampled)
    n = max(2, int(math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) / 0.02))
    best = 9e9
    for k in range(n + 1):
        x = t['x1'] + (t['x2'] - t['x1']) * k / n
        y = t['y1'] + (t['y2'] - t['y1']) * k / n
        dx = max(abs(x - p['x']) - p['w'] / 2, 0)
        dy = max(abs(y - p['y']) - p['h'] / 2, 0)
        best = min(best, math.hypot(dx, dy))
    return best - t['w'] / 2


def main():
    M = json.load(open(sys.argv[1]))
    P = json.load(open(sys.argv[2]))
    out = sys.argv[3]
    view = [float(v) for v in sys.argv[4:8]] if len(sys.argv) > 7 else [0, M['board']['w'], 0, M['board']['h']]
    nets = {(p['ref'], p['pad']): p['net'] for p in M['pads']}
    placed = []
    for ref, (side, x, y, rot) in P.items():
        if PARTS.get(ref) not in FP:
            continue
        placed += pads_of(ref, side, x, y, rot, nets)
    moved = {r for r in P if PARTS.get(r) in FP}
    M['pads'] = [p for p in M['pads'] if p['ref'] not in moved] + placed
    W, H = M['board']['w'], M['board']['h']
    probs = []
    for p in placed:
        L = p['layers'][0]
        e = min(p['x'] - p['w'] / 2, W - p['x'] - p['w'] / 2, p['y'] - p['h'] / 2, H - p['y'] - p['h'] / 2)
        if e < EDGE:
            probs.append('%s-%s edge %.3f' % (p['ref'], p['pad'], e))
        for q in M['pads']:
            if q['ref'] == p['ref']:
                continue
            if L in q['layers'] or q.get('drill', 0) > 0:
                g = rect_gap(p, q)
                lim = GAP if (q['ref'] != p['ref']) else 0
                if q['net'] == p['net'] and q['net'] and q['ref'] in moved:
                    lim = 0.1
                if g < lim:
                    probs.append('%s-%s vs %s-%s gap %.3f' % (p['ref'], p['pad'], q['ref'], q['pad'], g))
        for t in M['tracks']:
            if t['layer'] == L and t['net'] != p['net'] and abs(t['x1'] - p['x']) < 4 and abs(t['y1'] - p['y']) < 4:
                g = seg_rect_gap(t, p)
                if g < CLR:
                    probs.append('%s-%s vs track %s %.3f' % (p['ref'], p['pad'], t['net'], g))
        for v in M['vias']:
            if L in v['span'] and v['net'] != p['net'] and abs(v['x'] - p['x']) < 3 and abs(v['y'] - p['y']) < 3:
                dx = max(abs(v['x'] - p['x']) - p['w'] / 2, 0)
                dy = max(abs(v['y'] - p['y']) - p['h'] / 2, 0)
                g = math.hypot(dx, dy) - v['size'] / 2
                if g < CLR:
                    probs.append('%s-%s vs via %s %.3f' % (p['ref'], p['pad'], v['net'], g))
    seen = set()
    for s in probs:
        k = tuple(sorted(s.split(' vs ')))
        if k not in seen:
            seen.add(k)
            print('PROBLEM', s)
    print('%d problems' % len(seen))
    json.dump(M, open(out[:-4] + '.json', 'w'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle
    fig, ax = plt.subplots(figsize=(14, 14 * (view[3] - view[2]) / (view[1] - view[0]) + 0.5))
    ax.set_xlim(view[0], view[1]); ax.set_ylim(view[2], view[3]); ax.set_aspect('equal'); ax.grid(True, lw=0.3)
    for t in M['tracks']:
        if t['layer'] == 'Bottom Layer':
            ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], lw=max(1, t['w'] * 25), color='tab:blue', alpha=0.5)
    for v in M['vias']:
        if 'Bottom Layer' in v['span']:
            ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, color='tab:green'))
    for p in M['pads']:
        if 'Bottom Layer' in p['layers'] or p.get('drill', 0) > 0:
            mv = p['ref'] in moved
            ax.add_patch(Rectangle((p['x'] - p['w'] / 2, p['y'] - p['h'] / 2), p['w'], p['h'], fc='gold' if mv else 'orange',
                                   ec='red' if mv else 'black', lw=0.8, alpha=0.85))
            if view[0] < p['x'] < view[1] and view[2] < p['y'] < view[3]:
                ax.text(p['x'], p['y'], '%s-%s\n%s' % (p['ref'], p['pad'], p['net'][:9]), fontsize=4.5, ha='center',
                        va='center', clip_on=True)
    plt.savefig(out, dpi=85, bbox_inches='tight')


if __name__ == '__main__':
    main()
