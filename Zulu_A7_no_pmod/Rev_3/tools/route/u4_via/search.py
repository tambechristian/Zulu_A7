"""Find a legal spot for the GND through via that U4's 0.40 mm move put inside U4 pad 4 (2026-11-19).
The via (43.175, 18.125, 0.35/0.20) joins U4-4 (Top) and C120-2 (Bottom, by a 0.3 mm track). Candidates on a 0.025 mm
grid: land >= 0.09 from other-net copper on every layer (planes are pours, ignored), >= 0.025 from any SMD pad edge
(no via in pad), hole >= 0.24 from other holes, and both new 0.3/0.2 mm feed tracks (Top to U4-4's centre, Bottom to
C120-2's centre) >= 0.09 from other-net copper on their layer. Prints the best 10 by total feed length."""
import json, math, sys
M = json.load(open('tools/route/release_gate/model.json'))
OLD = (43.175, 18.125)
P4 = [p for p in M['pads'] if p['ref'] == 'U4' and p['pad'] == '4'][0]
C120 = [p for p in M['pads'] if p['ref'] == 'C120' and p['pad'] == '2'][0]
R, H = 0.175, 0.10
def segd(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1; L = dx * dx + dy * dy
    k = 0 if L == 0 else max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / L))
    return math.hypot(px - x1 - k * dx, py - y1 - k * dy)
def boxd(px, py, p):
    return math.hypot(max(abs(px - p['x']) - p['w'] / 2, 0), max(abs(py - p['y']) - p['h'] / 2, 0))
def segbox(x1, y1, x2, y2, p):
    return min(boxd(x1 + (x2 - x1) * i / 40, y1 + (y2 - y1) * i / 40, p) for i in range(41))
def segseg(a, b):
    return min(segd(a[0] + (a[2] - a[0]) * i / 40, a[1] + (a[3] - a[1]) * i / 40, *b) for i in range(41))
tracks = [t for t in M['tracks']]
vias = [v for v in M['vias'] if not (v['net'] == 'GND' and abs(v['x'] - OLD[0]) < 1e-3 and abs(v['y'] - OLD[1]) < 1e-3)]
def ok(x, y):
    for p in M['pads']:
        on = p['drill'] or not p['layers'] or True
        d = boxd(x, y, p) - R
        if not p['drill'] and d < 0.025 and (p['net'] != 'GND' or d < 0.025):
            return None
        if p['net'] != 'GND' and d < 0.09:
            return None
    for v in vias:
        dd = math.hypot(v['x'] - x, v['y'] - y)
        if v['net'] != 'GND' and dd - v['size'] / 2 - R < 0.09:
            return None
        if dd - v['hole'] / 2 - H < 0.24:
            return None
    for t in tracks:
        if t['net'] != 'GND' and segd(x, y, t['x1'], t['y1'], t['x2'], t['y2']) - t['w'] / 2 - R < 0.09:
            return None
    feeds = [('Top Layer', (x, y, P4['x'], P4['y'])), ('Bottom Layer', (x, y, C120['x'], C120['y']))]
    for L, s in feeds:
        for t in tracks:
            if t['layer'] == L and t['net'] != 'GND' and segseg(s, (t['x1'], t['y1'], t['x2'], t['y2'])) - t['w'] / 2 - 0.15 < 0.09:
                return None
        for p in M['pads']:
            if p['net'] != 'GND' and (p['drill'] or not p['layers'] or L in p['layers']) and segbox(*s, p) - 0.15 < 0.09:
                return None
        for v in vias:
            if v['net'] != 'GND' and L in v['span'] and segd(v['x'], v['y'], *s) - v['size'] / 2 - 0.15 < 0.09:
                return None
    return math.hypot(x - P4['x'], y - P4['y']) + math.hypot(x - C120['x'], y - C120['y'])
res = []
for i in range(-60, 61):
    for j in range(-60, 61):
        x, y = round(OLD[0] + i * 0.025, 4), round(OLD[1] + j * 0.025, 4)
        c = ok(x, y)
        if c is not None:
            res.append((round(c, 3), x, y))
res.sort()
print(len(res), 'legal sites'); [print(r) for r in res[:10]]
json.dump(res[:30], open('tools/route/u4_via/sites.json', 'w'))
