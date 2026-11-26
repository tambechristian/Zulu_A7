"""Silkscreen function labels for the LEDs (2026-11-26, user request). READ-ONLY.

    python tools/route/led_labels/find_spots.py

Labels: LD0 'LD0', LD1 'LD1', LD2 'LD2', LD3 'PWR', LD4 'CHRG', LD5 'DONE', LD6 'RXTX'. Same text style as the
board's X2 pin labels, the smallest silk on the board that PCBWay has already accepted: stroke font, height 0.8 mm,
stroke 0.15 mm.

Board rules: Silk To Solder Mask 0.254 mm (pads only; mask opening = pad), Silk To Silk 0.254 mm. Each candidate
keeps MARGIN from:
- every Top / through-hole pad;
- every printing Top Overlay text, track, arc and fill;
- the board edge.

It also stays off every Top part body (silk under a part is hidden). Silk may cross vias: all are tented or plugged. A label must sit nearer its
own LED than any other LED, by at least 0.3 mm. The set is chosen jointly: the labels keep MARGIN from each other,
and the total distance to their LEDs is minimal. Writes spots.json beside this file.
"""
import itertools
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
MARGIN = 0.26
TH, TS = 0.8, 0.15
LABELS = {'LD0': 'LD0', 'LD4': 'CHRG', 'LD6': 'RXTX'}   # LD1/LD2/PWR/DONE do not fit (see docs/led_labels.md); user chose these 3
PCB = os.path.join(ROOT, 'Imported zulu_a7.PrjPcb', 'Zulu_a7_no_pmod.PcbDoc')
M = json.load(open(os.path.join(TOOLS, 'route', 'illustration', 'base.json')))
D = json.load(open(os.path.join(TOOLS, 'route', 'illustration', 'comps.json')))
W, H = M['board']['w'], M['board']['h']
f = olefile.OleFileIO(PCB)
comps = [dict(x.split('=', 1) for x in r.strip('|').split('|') if '=' in x)
         for r in f.openstream('Components6/Data').read().decode('latin-1', 'replace').split(chr(0)) if 'PATTERN=' in r]


def ink(text, x, y, rot, h=TH, stroke=TS):
    """Altium stroke-font ink box (same model as tools/route/u2_label/find_spot.py)."""
    e = stroke / 2
    w = sum((5 / 6 if c in '1I' else 1) for c in text[:-1]) * h + (1 / 3 if text[-1] in '1I' else 2 / 3) * h
    return {0: (x - e, y - e, x + w + e, y + h + e), 90: (x - h - e, y - e, x + e, y + w + e)}[rot]


def records(stream, nsub):
    d, i, out = f.openstream(stream).read(), 0, []
    while i + 5 <= len(d):
        i += 1
        subs = []
        for _ in range(nsub):
            n = struct.unpack('<I', d[i:i + 4])[0]
            subs.append(d[i + 4:i + 4 + n])
            i += 4 + n
        out.append(subs)
    return out


silk = []
for b, s in records('Texts6/Data', 2):
    if b[0] != 33:
        continue
    comp = struct.unpack('<H', b[7:9])[0]
    if comp != 0xFFFF and not (b[41] == 1 and comp < len(comps) and comps[comp].get('NAMEON') == 'TRUE'):
        continue
    txt = s[1:1 + s[0]].decode('latin-1') if s else ''
    if not txt.strip():
        continue
    x, y, h = [struct.unpack('<i', b[13 + 4 * k:17 + 4 * k])[0] * U for k in range(3)]
    rot = round(struct.unpack('<d', b[27:35])[0]) % 360
    st = struct.unpack('<i', b[36:40])[0] * U
    if rot in (0, 90):
        silk.append(ink(txt, x, y, rot, h, st))
    else:
        bx = ink(txt, x, y, (rot - 180) % 360, h, st)
        silk.append((2 * x - bx[2], 2 * y - bx[3], 2 * x - bx[0], 2 * y - bx[1]))
for (b,) in records('Tracks6/Data', 1):
    if b[0] == 33:
        x1, y1, x2, y2, w = [struct.unpack('<i', b[13 + 4 * k:17 + 4 * k])[0] * U for k in range(5)]
        silk.append((min(x1, x2) - w / 2, min(y1, y2) - w / 2, max(x1, x2) + w / 2, max(y1, y2) + w / 2))
for (b,) in records('Arcs6/Data', 1):
    if b[0] == 33:
        x, y, r = [struct.unpack('<i', b[13 + 4 * k:17 + 4 * k])[0] * U for k in range(3)]
        w = struct.unpack('<i', b[41:45])[0] * U
        silk.append((x - r - w / 2, y - r - w / 2, x + r + w / 2, y + r + w / 2))
for (b,) in records('Fills6/Data', 1):
    if b[0] == 33:
        x1, y1, x2, y2 = [struct.unpack('<i', b[13 + 4 * k:17 + 4 * k])[0] * U for k in range(4)]
        silk.append((min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)))
pads = [(p['x'] - p['w'] / 2, p['y'] - p['h'] / 2, p['x'] + p['w'] / 2, p['y'] + p['h'] / 2) for p in M['pads']
        if p['drill'] or not p['layers'] or 'Top Layer' in p['layers']]
holes = [(v['x'] - v['hole'] / 2, v['y'] - v['hole'] / 2, v['x'] + v['hole'] / 2, v['y'] + v['hole'] / 2) for v in M['vias']]
top = body_check.build(M, D)['Top']
bodies = [v['body'][0] for r, v in top.items() if v['body']]
own = {}
for ref in LABELS:
    pp = [p for p in M['pads'] if p['ref'] == ref]
    own[ref] = (min(p['x'] - p['w'] / 2 for p in pp), min(p['y'] - p['h'] / 2 for p in pp),
                max(p['x'] + p['w'] / 2 for p in pp), max(p['y'] + p['h'] / 2 for p in pp))
    if top.get(ref, {}).get('body'):
        bb = top[ref]['body'][0]
        own[ref] = (min(own[ref][0], bb[0]), min(own[ref][1], bb[1]), max(own[ref][2], bb[2]), max(own[ref][3], bb[3]))
leds = {r: own[r] for r in own}
leds.update({r: v['body'][0] for r, v in top.items() if r.startswith('LD') and v['body'] and r not in leds})


def gap(a, b):
    dx = max(a[0] - b[2], b[0] - a[2])
    dy = max(a[1] - b[3], b[1] - a[3])
    if dx < 0 and dy < 0:
        return max(dx, dy)
    return math.hypot(max(dx, 0), max(dy, 0))


def near(lst, c, r=7.0):
    return [o for o in lst if gap(o, (c[0] - r, c[1] - r, c[2] + r, c[3] + r)) <= 0]


def legal(box, L):
    if box[0] < 0.3 or box[1] < 0.3 or box[2] > W - 0.3 or box[3] > H - 0.3:
        return None
    g = min(gap(box, o) for o in L['obs'])
    # via holes are not obstacles: every via on this board is tented or plugged (FAB_NOTES VIA TENTING)
    if g < MARGIN or any(gap(box, b) < 0.05 for b in L['bodies']):
        return None
    return g


cands = {}
for ref, text in LABELS.items():
    c0 = own[ref]
    cx, cy = (c0[0] + c0[2]) / 2, (c0[1] + c0[3]) / 2
    out = []
    L = dict(obs=near(silk + pads, c0), bodies=near(bodies, c0), holes=near(holes, c0))
    for rot in (0, 90):
        for ix in range(-140, 141):
            for iy in range(-140, 141):
                x, y = round(cx + ix * 0.025, 3), round(cy + iy * 0.025, 3)
                box = ink(text, x, y, rot)
                d = gap(box, own[ref])
                if d > 3.0 or d < MARGIN:
                    continue
                if any(gap(box, v) < d + 0.3 for r, v in leds.items() if r != ref):
                    continue
                g = legal(box, L)
                if g is None:
                    continue
                # prefer reading direction 0 and a label level with the LED
                out.append((round(d + (0.4 if rot else 0) + 0.2 * abs((box[1] + box[3]) / 2 - cy), 3), rot, x, y, round(g, 3),
                            tuple(round(v, 3) for v in box)))
    out.sort()
    cands[ref] = out
    print('%s %-4s %5d candidates' % (ref, text, len(out)))
    seen = set()
    for c in out:
        k = (c[1], round(c[2]), round(c[3]))
        if k in seen: continue
        seen.add(k); print('   ', c)
        if len(seen) >= 12: break

# joint choice: top 60 per label, keep MARGIN between labels, minimise total score
TOP = {r: [c for i, c in enumerate(v) if i < 400][::7][:60] for r, v in cands.items()}
best, bestset = None, None
refs = sorted(TOP, key=lambda r: len(TOP[r]))


def search(i, chosen, total):
    global best, bestset
    if best is not None and total >= best:
        return
    if i == len(refs):
        best, bestset = total, dict(chosen)
        return
    r = refs[i]
    for c in TOP[r]:
        if all(gap(c[5], o[5]) >= MARGIN for o in chosen.values()):
            chosen[r] = c
            search(i + 1, chosen, total + c[0])
            del chosen[r]


search(0, {}, 0.0)
print('joint total', best)
for r in LABELS:
    c = bestset[r]
    print('%s %-4s rot %d at (%.3f, %.3f) ink %s, own-LED gap score %.3f, clearance %.3f' % (r, LABELS[r], c[1], c[2], c[3], c[5], c[0], c[4]))
json.dump({r: dict(text=LABELS[r], rot=bestset[r][1], x=bestset[r][2], y=bestset[r][3], ink=bestset[r][5],
                   clearance=bestset[r][4]) for r in LABELS},
          open(os.path.join(HERE, 'spots.json'), 'w'), indent=1)
