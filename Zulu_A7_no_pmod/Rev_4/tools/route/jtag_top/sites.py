"""No-PMOD Rev 4 (2026-11-25): JTAG header moved to a 1x6 through-hole row above X3; X3 1.7 mm west to the board
edge; BTN back to its Rev 3 spot. Site search for the Bottom parts the row displaces.

    python tools/route/jtag_top/sites.py OPTION      (OPTION: west = row x0 1.26 on the X2 grid; east = x0 11.76)

Obstacles: every Bottom pad and through-hole pad (X3 shifted -1.7 mm), the six new JTAG holes (1.524 round,
all layers), every Bottom body from body_check.build() (X2 housings included). A candidate site for a displaced
part: pads >= 0.10 mm from other-net copper pads and >= 0.30 mm inside the outline, body >= 0.10 mm from every
other Bottom body. Bottom tracks / Bottom-reaching vias of other nets within 0.09 mm are counted (rippable).
Parts are placed greedily (largest first), each placed part becoming an obstacle. Prints the plan.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, TOOLS)
import body_check  # noqa: E402

ROW_Y = 21.0
X0 = {'west': 1.26, 'east': 11.76}
DISPLACE = {'west': ['R34', 'C13', 'C11', 'C12', 'R35'], 'east': ['U10', 'R34']}
X3_DX = -1.7
PAD_R = 0.762


def box_gap(a, b):
    dx = max(a[0] - b[2], b[0] - a[2], 0)
    dy = max(a[1] - b[3], b[1] - a[3], 0)
    return math.hypot(dx, dy)


def pbox(p):
    return (p['x'] - p['w'] / 2, p['y'] - p['h'] / 2, p['x'] + p['w'] / 2, p['y'] + p['h'] / 2)


def seg_box_gap(t, b):
    n = max(2, int(math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) / 0.05) + 1)
    g = 9e9
    for i in range(n + 1):
        x = t['x1'] + (t['x2'] - t['x1']) * i / n
        y = t['y1'] + (t['y2'] - t['y1']) * i / n
        g = min(g, box_gap((x, y, x, y), b))
    return g - t['w'] / 2


def main():
    opt = sys.argv[1]
    M = json.load(open(os.path.join(TOOLS, 'route', 'illustration', 'base.json')))
    D = json.load(open(os.path.join(TOOLS, 'route', 'illustration', 'comps.json')))
    W, H = M['board']['w'], M['board']['h']
    comp = {c['ref']: c for c in D['comps']}
    B = body_check.build(M, D)['Bottom']
    holes = [(X0[opt] + 2.54 * k, ROW_Y) for k in range(6)]
    obst_pads = []                                   # (box, net)
    for p in M['pads']:
        if p['ref'] in DISPLACE[opt] or p['ref'] in ('JP3', 'JP4'):
            continue
        if p['drill'] or (p['layers'] and 'Bottom Layer' in p['layers']):
            q = dict(p)
            if p['ref'] == 'X3':
                q['x'] += X3_DX
            obst_pads.append((pbox(q), p['net']))
    for x, y in holes:
        obst_pads.append(((x - PAD_R, y - PAD_R, x + PAD_R, y + PAD_R), '*JTAG'))
    bodies = [b for r, v in B.items() if r not in DISPLACE[opt] for b in v['body']]
    btr = [t for t in M['tracks'] if t['layer'] == 'Bottom Layer']
    bvia = [v for v in M['vias'] if 'Bottom Layer' in v['span']]
    plan = []
    for ref in DISPLACE[opt]:
        ps = [p for p in M['pads'] if p['ref'] == ref]
        cx = sum(p['x'] for p in ps) / len(ps)
        cy = sum(p['y'] for p in ps) / len(ps)
        L, Wd = body_check.BODY[comp[ref]['pattern']][2:4]
        best = None
        for rot in (0, 90, 180, 270):
            c, s = round(math.cos(math.radians(rot))), round(math.sin(math.radians(rot)))
            rel = [(p, (p['x'] - cx) * c - (p['y'] - cy) * s, (p['x'] - cx) * s + (p['y'] - cy) * c,
                    (p['w'], p['h']) if rot % 180 == 0 else (p['h'], p['w'])) for p in ps]
            bw, bh = (L, Wd) if (round(comp[ref]['rot']) + rot) % 180 == 0 else (Wd, L)
            for i in range(-200, 201):
                for j in range(-200, 201):
                    nx, ny = cx + i * 0.05, cy + j * 0.05
                    d = math.hypot(nx - cx, ny - cy)
                    if d > 10 or (best and 3 * d > best[0]):
                        continue
                    nb = [((nx + dx - w / 2, ny + dy - h / 2, nx + dx + w / 2, ny + dy + h / 2), p['net'])
                          for p, dx, dy, (w, h) in rel]
                    if any(b[0] < 0.3 or b[1] < 0.3 or b[2] > W - 0.3 or b[3] > H - 0.3 for b, _ in nb):
                        continue
                    if any(n != on and box_gap(b, ob) < 0.10 for b, n in nb for ob, on in obst_pads):
                        continue
                    if any(n == on and n and box_gap(b, ob) < 0.0 for b, n in nb for ob, on in obst_pads):
                        continue
                    body = (nx - bw / 2, ny - bh / 2, nx + bw / 2, ny + bh / 2)
                    if any(box_gap(body, ob) < 0.10 for ob in bodies):
                        continue
                    rt = sum(1 for t in btr if any(t['net'] != n and seg_box_gap(t, b) < 0.09 for b, n in nb))
                    rv = sum(1 for v in bvia if any(v['net'] != n and box_gap((v['x'], v['y'], v['x'], v['y']), b) < v['size'] / 2 + 0.09 for b, n in nb))
                    score = 3 * d + 0.5 * rt + 2 * rv
                    if best is None or score < best[0]:
                        best = (score, d, rt, rv, rot, nx, ny, nb, body)
        if best is None:
            print('%s: NO SITE within 10 mm' % ref)
            continue
        score, d, rt, rv, rot, nx, ny, nb, body = best
        print('%-4s %-17s (%.2f,%.2f) -> (%.2f,%.2f) turn +%d, %.2f mm, rips %d tracks %d vias' % (
            ref, comp[ref]['pattern'], cx, cy, nx, ny, rot, d, rt, rv))
        plan.append({'ref': ref, 'from': [round(cx, 4), round(cy, 4)], 'to': [round(nx, 4), round(ny, 4)], 'turn': rot,
                     'pads': [[p['pad'], round(b[0] / 2 + b[2] / 2, 4), round(b[1] / 2 + b[3] / 2, 4)] for (p, *_), (b, _) in zip([(p,) for p in ps], nb)]})
        obst_pads += nb
        bodies.append(body)
    json.dump({'option': opt, 'holes': holes, 'parts': plan}, open(os.path.join(HERE, 'sites_%s.json' % opt), 'w'), indent=1)


if __name__ == '__main__':
    main()
