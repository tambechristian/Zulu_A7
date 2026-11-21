"""Find a legal spot for U2's designator near U2 (2026-11-19). READ-ONLY.

    python tools/route/u2_label/find_spot.py

The designator sat in X2's pin-label row (DRC Silk-to-Silk with 'C8' and 'C9'). Rules on the board: Silk To Solder
Mask 0.254 mm (pads only; this board's mask opening equals the pad, calibrated on the DRC's U2-1 0.185 mm item),
Silk To Silk 0.254 mm. Candidates keep MARGIN from every Top pad (and through-hole pad), every other printing Top
Overlay text and track, the board edge, and stay off every Top part body (silk under a part is hidden).
"""
import json
import math
import os
import struct
import sys

import olefile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import body_check  # noqa: E402

U = 2.54e-6
MARGIN = 0.30
PCB = os.path.join(ROOT, 'Imported zulu_a7.PrjPcb', 'Zulu_a7_no_pmod.PcbDoc')
M = json.load(open(os.path.join(TOOLS, 'route', 'illustration', 'base.json')))
D = json.load(open(os.path.join(TOOLS, 'route', 'illustration', 'comps.json')))
W, H = M['board']['w'], M['board']['h']

f = olefile.OleFileIO(PCB)
comps = []
for r in f.openstream('Components6/Data').read().decode('latin-1', 'replace').split(chr(0)):
    if 'PATTERN=' in r:
        comps.append(dict(x.split('=', 1) for x in r.strip('|').split('|') if '=' in x))


def ink(t):
    """Altium stroke-font ink box (x0, y0, x1, y1) of a text dict, stroke included."""
    n, h, e = len(t['text']), t['h'], t['stroke'] / 2
    w = sum((5 / 6 if c in '1I' else 1) for c in t['text'][:-1]) * h + (1 / 3 if t['text'][-1] in '1I' else 2 / 3) * h
    x, y = t['x'], t['y']
    return {0: (x - e, y - e, x + w + e, y + h + e), 90: (x - h - e, y - e, x + e, y + w + e),
            180: (x - w - e, y - h - e, x + e, y + e), 270: (x - e, y - w - e, x + h + e, y + e)}[t['rot']]


texts, d, i = [], f.openstream('Texts6/Data').read(), 0
while i + 5 <= len(d):
    i += 1
    subs = []
    for _ in range(2):
        n = struct.unpack('<I', d[i:i + 4])[0]
        subs.append(d[i + 4:i + 4 + n])
        i += 4 + n
    b, s = subs
    if b[0] != 33:
        continue
    comp = struct.unpack('<H', b[7:9])[0]
    if comp != 0xFFFF and not (b[41] == 1 and comp < len(comps) and comps[comp].get('NAMEON') == 'TRUE'):
        continue
    texts.append(dict(text=s[1:1 + s[0]].decode('latin-1') if s else '', comp=comp,
                      ref=comps[comp].get('SOURCEDESIGNATOR') if comp != 0xFFFF else None,
                      x=struct.unpack('<i', b[13:17])[0] * U, y=struct.unpack('<i', b[17:21])[0] * U,
                      h=struct.unpack('<i', b[21:25])[0] * U, rot=round(struct.unpack('<d', b[27:35])[0]) % 360,
                      stroke=struct.unpack('<i', b[36:40])[0] * U))
u2 = [t for t in texts if t['ref'] == 'U2' and t['text'] == 'U2']
assert len(u2) == 1, u2
u2 = u2[0]
others = [ink(t) for t in texts if t is not u2 and t['text'].strip()]
d, i = f.openstream('Tracks6/Data').read(), 0
while i + 5 <= len(d):
    ln = struct.unpack('<I', d[i + 1:i + 5])[0]
    b = d[i + 5:i + 5 + ln]
    i += 5 + ln
    if b[0] == 33:
        x1, y1, x2, y2, w = [struct.unpack('<i', b[13 + 4 * k:17 + 4 * k])[0] * U for k in range(5)]
        others.append((min(x1, x2) - w / 2, min(y1, y2) - w / 2, max(x1, x2) + w / 2, max(y1, y2) + w / 2))
pads = [(p['x'] - p['w'] / 2, p['y'] - p['h'] / 2, p['x'] + p['w'] / 2, p['y'] + p['h'] / 2) for p in M['pads']
        if p['drill'] or not p['layers'] or 'Top Layer' in p['layers']]
bodies = [v['body'][0] for r, v in body_check.build(M, D)['Top'].items() if v['body']]
u2body = body_check.build(M, D)['Top']['U2']['body'][0]


def gap(a, b):
    dx = max(a[0] - b[2], b[0] - a[2])
    dy = max(a[1] - b[3], b[1] - a[3])
    if dx < 0 and dy < 0:
        return max(dx, dy)
    return math.hypot(max(dx, 0), max(dy, 0))


def legal(box):
    if box[0] < MARGIN or box[1] < MARGIN or box[2] > W - MARGIN or box[3] > H - MARGIN:
        return None
    g = min(min(gap(box, o) for o in others), min(gap(box, p) for p in pads))
    if g < MARGIN or any(gap(box, b) < 0.05 for b in bodies):
        return None
    return g


print('current U2 designator: x %.3f y %.3f h %.3f stroke %.3f rot %d, ink %s, legal %s' % (
    u2['x'], u2['y'], u2['h'], u2['stroke'], u2['rot'], [round(v, 3) for v in ink(u2)], legal(ink(u2))))
print('U2 body', [round(v, 3) for v in u2body])
cands = []
for rot in (0, 90):
    for ix in range(-120, 121):
        for iy in range(-120, 121):
            t = dict(u2, x=30.5 + ix * 0.05, y=14.55 + iy * 0.05, rot=rot)
            box = ink(t)
            g = legal(box)
            if g is None:
                continue
            cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
            dist = gap(box, u2body)
            cands.append((round(dist, 2), rot, round(t['x'], 3), round(t['y'], 3), round(g, 3),
                          [round(v, 2) for v in box]))
cands.sort()
for c in cands[:15]:
    print(c)
json.dump(dict(current=u2, best=cands[:15]), open(os.path.join(HERE, 'spots.json'), 'w'), indent=1)
