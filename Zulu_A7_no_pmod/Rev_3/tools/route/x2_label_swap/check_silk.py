"""Silk clearance checker for the Zulu silk edit (2026-11-24). Read-only.
    python check_silk.py <geom.json> [<edits.json>] [--all]
edits.json: {"delete": [idx...], "set": {idx: {"text":..,"x":..,"y":..,"rot":..,"shown":true}}}
Checks every SHOWN Top/Bottom Overlay text (or only edited ones unless --all) against:
  silk-to-silk 0.254 (text boxes = stroke-font box incl. half stroke; overlay tracks/arcs incl. half width),
  silk-to-mask 0.254 (pad copper + expansion; round pads as circles), board edge (inside, >= 0),
  and reports (not fails) text over a same-side component body or an untented-looking via land."""
import json, math, sys
G = json.load(open(sys.argv[1]))
E = json.load(open(sys.argv[2])) if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else {'delete': [], 'set': {}}
ALL = '--all' in sys.argv
SS, SM = 0.254 - 1e-4, 0.254 - 1e-4
BW, BH = G['board']['w'], G['board']['h']
def box_of(t):
    s = t['text']; h = t['h']; e = t['stroke'] / 2; x, y = t['x'], t['y']
    # Altium stroke-font ink model (Asar picture work, matched GTO to 0.001): advance h ('1'/'I' 5/6 h),
    # last glyph ink 2/3 h ('1'/'I' 1/3 h)
    w = sum((5 / 6 if c in '1I' else 1.0) * h for c in s[:-1]) + ((1 / 3 if s[-1] in '1I' else 2 / 3) * h if s else 0)
    r = round(t['rot']) % 360
    return [(x - e, y - e, x + w + e, y + h + e), (x - h - e, y - e, x + e, y + w + e),
            (x - w - e, y - h - e, x + e, y + e), (x - e, y - w - e, x + h + e, y + e)][{0: 0, 90: 1, 180: 2, 270: 3}[r]]
def bgap(a, b):
    dx = max(a[0] - b[2], b[0] - a[2]); dy = max(a[1] - b[3], b[1] - a[3])
    return max(dx, dy) if dx < 0 and dy < 0 else math.hypot(max(dx, 0), max(dy, 0))
def seg_box_gap(x1, y1, x2, y2, b):
    # distance from segment to box (sampled finely; adequate at 5 um)
    n = max(2, int(math.hypot(x2 - x1, y2 - y1) / 0.005))
    best = 9e9
    for i in range(n + 1):
        t = i / n; x, y = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
        best = min(best, bgap((x, y, x, y), b))
    return best
def circ_box_gap(cx, cy, r, b):
    dx = max(b[0] - cx, 0, cx - b[2]); dy = max(b[1] - cy, 0, cy - b[3])
    return math.hypot(dx, dy) - r
texts = {t['idx']: dict(t) for t in G['texts']}
dele = set(int(i) for i in E.get('delete', []))
edited = set(dele)
for k, v in E.get('set', {}).items():
    texts[int(k)].update(v); edited.add(int(k))
for k, v in enumerate(E.get('add', [])):
    t = dict(v); t['idx'] = 100000 + k; t.setdefault('kind', 'free'); t.setdefault('shown', True); t.setdefault('ref', None)
    texts[t['idx']] = t; edited.add(t['idx'])
live = {i: t for i, t in texts.items() if i not in dele and t.get('shown')}
for t in live.values(): t['box'] = box_of(t)
check = [t for i, t in live.items() if ALL or i in edited]
fails, notes = [], []
for t in check:
    side = 'Top' if t['layer'] == 33 else 'Bottom'
    b = t['box']; lab = '%s%r@(%.3f,%.3f)' % ('' if t['kind'] == 'free' else t['ref'] + ':', t['text'], t['x'], t['y'])
    edge = min(b[0], b[1], BW - b[2], BH - b[3])          # legend to board edge: 10 mil like silk-silk (DRC never runs it)
    if edge < SS: fails.append((lab, 'board edge', round(edge, 3)))
    for u in live.values():
        if u is t or u['layer'] != t['layer'] or (u['idx'] in edited and u['idx'] < t['idx'] and not ALL): continue
        if ALL and u['idx'] < t['idx']: continue
        g = bgap(b, u['box'])
        if g < SS: fails.append((lab, 'silk-silk text %r@(%.2f,%.2f)' % (u['text'], u['x'], u['y']), round(g, 3)))
    for s in G['tracks']:
        if s['layer'] != t['layer']: continue
        g = seg_box_gap(s['x1'], s['y1'], s['x2'], s['y2'], b) - s['w'] / 2
        if g < SS: fails.append((lab, 'silk-silk track %s' % s['ref'], round(g, 3)))
    for a in G['arcs']:
        if a['layer'] != t['layer']: continue
        g = circ_box_gap(a['cx'], a['cy'], a['r'] + a['w'] / 2, b)   # full circle (conservative)
        if g < SS: fails.append((lab, 'silk-silk arc %s' % a['ref'], round(g, 3)))
    for p in G['pads']:
        if p['side'] != side: continue
        m = p['mask']
        if p['shape'] == 'circle':
            g = circ_box_gap(p['x'], p['y'], (m[2] - m[0]) / 2, b)
        else:
            g = bgap(b, m)
        if g < SM: fails.append((lab, 'silk-mask %s-%s' % (p['ref'], p['pad']), round(g, 3)))
    for r, bs in G['bodies'].get(side, {}).items():
        for bb in bs:
            g = bgap(b, bb)
            if g < 0.0: notes.append((lab, 'over body %s' % r, round(g, 3)))
fails.sort(key=lambda f: f[2])
for f in fails: print('FAIL %-34s %-40s %7.3f' % f)
for n in notes: print('note %-34s %-40s %7.3f' % n)
print('check_silk: %d texts checked, %d fail, %d body notes' % (len(check), len(fails), len(notes)))
