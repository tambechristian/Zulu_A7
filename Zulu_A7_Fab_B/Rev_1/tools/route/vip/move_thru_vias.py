"""Move every Top-Bottom through via out of the SMD pads it overlaps (Fab B, 2026-11-11, user decision: no
through via in a pad; microvias in pads stay as VIPPO).

    python tools/route/vip/move_thru_vias.py <model.json> <PcbDoc> <out_plan.json>

For each through via whose 0.35 land overlaps an SMD pad (any net) on Top or Bottom:
  * candidate centres P on a 0.025 mm grid within 1.5 mm, nearest first;
  * the new land must not touch any SMD pad (gap >= 0.0, and >= the clearance to other-net pads), must keep the
    clearance (0.09; 0.10 / 0.20 to SDRAM / SDRAM-CLK copper on L3/L4) to all other-net copper on all six layers,
    0.24 mm hole-to-hole to every other hole, 0.30 mm to the board edge;
  * on every layer where copper of the via's net met the old via (the pad on its layer, tracks ending in the land),
    a jumper track old -> P is added, width = max(width of the copper it replaces on that layer, the board's Width
    rule minimum for the net on that layer, 0.15 for pads); the jumper must keep the clearance on that layer;
  * a candidate is scored by its distance; moves are applied one at a time so later vias see earlier ones.
The planes (L2 GND, L5 VCC3V3 polygons) are repoured by Altium afterwards; other-net vias get their voids then.
"""
import json
import math
import re
import sys

import olefile

STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
OUTER = ('Top Layer', 'Bottom Layer')
CLEAR = 0.09
LAYKEY = {'Top Layer': 'TOPLAYER', 'L3-SIG': 'MIDLAYER1', 'L4-SIG': 'MIDLAYER2', 'Bottom Layer': 'BOTTOMLAYER'}

M = json.load(open(sys.argv[1]))
o = olefile.OleFileIO(sys.argv[2])


def recs(stream):
    return [r.decode('latin1') for r in o.openstream(stream).read().split(b'\x00') if b'|' in r]


def kv(s):
    return dict(p.split('=', 1) for p in s.split('|') if '=' in p)


def mil(v):
    return float(v.replace('mil', '')) * 0.0254 if v.endswith('mil') else float(v.replace('mm', ''))


classes = {}
for s in recs('Classes6/Data'):
    d = kv(s)
    if d.get('KIND') == '0':
        classes[d.get('NAME')] = {d[k] for k in d if k.startswith('M') and k[1:].isdigit()}
rules = sorted((d for d in map(kv, recs('Rules6/Data')) if d.get('RULEKIND') == 'Width' and d.get('ENABLED') == 'TRUE'),
               key=lambda d: int(d['PRIORITY']))


def match(expr, net):
    for term in expr.split(' Or '):
        term = term.strip()
        if term == 'All':
            return True
        m = re.match(r"InNet\('(.*)'\)", term)
        if m and m.group(1) == net:
            return True
        m = re.match(r"InNetClass\('(.*)'\)", term)
        if m and net in classes.get(m.group(1), ()):
            return True
    return False


def wmin(net, layer):
    r = next(r for r in rules if match(r['SCOPE1EXPRESSION'], net))
    lk = LAYKEY.get(layer)
    return mil(r.get(lk + '_MINWIDTH', r['MINLIMIT'])) if lk else mil(r['MINLIMIT'])


SDRAM = classes.get('SDRAM_DATA', set()) | classes.get('SDRAM_ADDR', set()) | classes.get('SDRAM_CTRL', set())
SDCLK = classes.get('SDRAM-CLK', set()) | classes.get('SDRAM_CLK', set())


def clr(net_other, layer):
    if layer in ('L3-SIG', 'L4-SIG'):
        if net_other in SDCLK:
            return 0.20
        if net_other in SDRAM:
            return 0.10
    return CLEAR


def vspan(v):
    return v['span']


def rect_circle_gap(p, x, y, r):
    dx = max(abs(x - p['x']) - p['w'] / 2, 0)
    dy = max(abs(y - p['y']) - p['h'] / 2, 0)
    return math.hypot(dx, dy) - r


def seg_pt(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    k = 0 if L2 == 0 else max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / L2))
    return math.hypot(px - x1 - k * dx, py - y1 - k * dy)


def seg_seg(a, b):
    (ax1, ay1, ax2, ay2), (bx1, by1, bx2, by2) = a, b

    def ccw(p, q, r):
        return (r[1] - p[1]) * (q[0] - p[0]) - (q[1] - p[1]) * (r[0] - p[0])
    p1, p2, p3, p4 = (ax1, ay1), (ax2, ay2), (bx1, by1), (bx2, by2)
    d1, d2, d3, d4 = ccw(p3, p4, p1), ccw(p3, p4, p2), ccw(p1, p2, p3), ccw(p1, p2, p4)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)) and d1 * d2 < 0 and d3 * d4 < 0:
        return 0.0
    return min(seg_pt(ax1, ay1, *b), seg_pt(ax2, ay2, *b), seg_pt(bx1, by1, *a), seg_pt(bx2, by2, *a))


def seg_rect(seg, p):
    x1, y1, x2, y2 = seg
    hw, hh = p['w'] / 2, p['h'] / 2
    cx, cy = p['x'], p['y']
    if abs(x1 - cx) <= hw and abs(y1 - cy) <= hh or abs(x2 - cx) <= hw and abs(y2 - cy) <= hh:
        return 0.0
    edges = [(cx - hw, cy - hh, cx + hw, cy - hh), (cx + hw, cy - hh, cx + hw, cy + hh),
             (cx + hw, cy + hh, cx - hw, cy + hh), (cx - hw, cy + hh, cx - hw, cy - hh)]
    return min(seg_seg(seg, e) for e in edges)


pads = M['pads']
tracks = list(M['tracks'])
vias = list(M['vias'])
W, H = M['board']['w'], M['board']['h']
holes_pad = [p for p in pads if p['drill']]

thru = [v for v in vias if len(v['span']) == 6]
smd = [p for p in pads if not p['drill']]
todo = []
for v in thru:
    hit = [p for p in smd if p['layers'][0] in OUTER and rect_circle_gap(p, v['x'], v['y'], v['size'] / 2) < 0]
    if hit:
        todo.append((v, hit))
print('through vias in SMD pads:', len(todo))


def fits(net, P, size, hole, skip_via):
    x, y = P
    r = size / 2
    if x - r < 0.30 or y - r < 0.30 or x + r > W - 0.30 or y + r > H - 0.30:
        return False
    for p in pads:
        on = p['layers'] if not p['drill'] else STACK
        g = rect_circle_gap(p, x, y, r)
        if not p['drill'] and p['layers'][0] in OUTER and g < 0.0:
            return False                      # no via land in any SMD pad, whatever the net
        if p['net'] != net and g < max(clr(p['net'], L) for L in on):
            return False
        if p['drill'] and math.hypot(p['x'] - x, p['y'] - y) - p['drill'] / 2 - hole / 2 < 0.24:
            return False
    for t in tracks:
        if t['net'] == net:
            continue
        if seg_pt(x, y, t['x1'], t['y1'], t['x2'], t['y2']) - t['w'] / 2 - r < clr(t['net'], t['layer']):
            return False
    for v in vias:
        if v is skip_via:
            continue
        d = math.hypot(v['x'] - x, v['y'] - y)
        if d - v['hole'] / 2 - hole / 2 < 0.24:
            return False
        if v['net'] != net and d - v['size'] / 2 - r < max(clr(v['net'], L) for L in v['span']):
            return False
    return True


def seg_fits(net, layer, seg, w):
    for p in pads:
        on = p['layers'] if not p['drill'] else STACK
        if layer not in on or p['net'] == net:
            continue
        if seg_rect(seg, p) - w / 2 < clr(p['net'], layer):
            return False
    for t in tracks:
        if t['layer'] != layer or t['net'] == net:
            continue
        if seg_seg(seg, (t['x1'], t['y1'], t['x2'], t['y2'])) - w / 2 - t['w'] / 2 < clr(t['net'], layer):
            return False
    for v in vias:
        if layer not in v['span'] or v['net'] == net:
            continue
        if seg_pt(v['x'], v['y'], *seg) - w / 2 - v['size'] / 2 < clr(v['net'], layer):
            return False
    return True


plan = {'remove': [], 'remove_vias': [], 'tracks': [], 'vias': [], 'report': []}
fail = []
for v, hit in todo:
    net, ox, oy, r = v['net'], v['x'], v['y'], v['size'] / 2
    # what met the old via, per layer
    need = {}
    for L in STACK:
        ws = [t['w'] for t in tracks if t['layer'] == L and t['net'] == net and
              min(math.hypot(t['x1'] - ox, t['y1'] - oy), math.hypot(t['x2'] - ox, t['y2'] - oy)) <= r]
        ps = [p for p in pads if p['net'] == net and not p['drill'] and p['layers'][0] == L and
              rect_circle_gap(p, ox, oy, r) < 0]
        if ws or ps:
            need[L] = max(ws + [0.15 if ps else 0] + [wmin(net, L) if L not in ('L2-GND', 'L5-VCC3V3') else 0])
    cands = []
    for i in range(-60, 61):
        for j in range(-60, 61):
            d = 0.025 * math.hypot(i, j)
            if 0 < d <= 1.5:
                cands.append((d, ox + 0.025 * i, oy + 0.025 * j))
    cands.sort()
    vias.remove(v)
    done = None
    for d, x, y in cands:
        if not fits(net, (x, y), v['size'], v['hole'], None):
            continue
        segs = [(L, (ox, oy, x, y), w) for L, w in need.items()]
        if all(seg_fits(net, L, s, w) for L, s, w in segs):
            done = (x, y, segs, d)
            break
    if not done:
        vias.append(v)
        fail.append((net, ox, oy, [p['ref'] + '-' + p['pad'] for p in hit]))
        continue
    x, y, segs, d = done
    nv = dict(v, x=round(x, 4), y=round(y, 4))
    vias.append(nv)
    plan['remove_vias'].append(v)
    plan['vias'].append(nv)
    for L, s, w in segs:
        t = {'net': net, 'layer': L, 'w': round(w, 4), 'x1': ox, 'y1': oy, 'x2': round(x, 4), 'y2': round(y, 4)}
        tracks.append(t)
        plan['tracks'].append(t)
    plan['report'].append({'net': net, 'from': [ox, oy], 'to': [nv['x'], nv['y']], 'moved': round(d, 4),
                           'pads': [p['ref'] + '-' + p['pad'] for p in hit], 'jumpers': {L: w for L, s, w in segs}})
    print('%-8s (%.3f,%.3f) -> (%.3f,%.3f) %.3f mm  %s  jumpers %s' % (net, ox, oy, x, y, d,
          ','.join(p['ref'] + '-' + p['pad'] for p in hit), {L: round(w, 3) for L, s, w in segs}))
print('moved', len(plan['vias']), 'failed', len(fail))
for f in fail:
    print('FAILED', f)
json.dump(plan, open(sys.argv[3], 'w'), indent=0)
