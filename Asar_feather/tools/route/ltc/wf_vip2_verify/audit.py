"""audit.py <final model> <plan>: geometric audit of the wf_vip2 block copper."""
import json, sys, math
M = json.load(open(sys.argv[1])); P = json.load(open(sys.argv[2]))
NETS = {'PWR_SW', 'USB5V0', 'VBATT', 'VU', 'GND', 'PWR_PROG', 'PWR_FB2', 'PWR_PGOODALL'}
BOX = (8.5, 9.5, 16.5, 16.5)
def inbox(x, y): return BOX[0] <= x <= BOX[2] and BOX[1] <= y <= BOX[3]
pads = [p for p in M['pads'] if inbox(p['x'], p['y'])]
print('== plan vias vs pads (outer-layer landing)')
for v in P['vias']:
    for L in (v['from'], v['to']):
        if L not in ('Top Layer', 'Bottom Layer'):
            continue
        r = v['size'] / 2
        hits = [p for p in pads if L in p['layers'] and abs(v['x'] - p['x']) < p['w'] / 2 + r and abs(v['y'] - p['y']) < p['h'] / 2 + r]
        for p in hits:
            full = abs(v['x'] - p['x']) + r <= p['w'] / 2 + 1e-6 and abs(v['y'] - p['y']) + r <= p['h'] / 2 + 1e-6
            print('  %s via %.2f/%.2f (%.3f,%.3f) %s on %s-%s %s %s' % (v['net'], v['size'], v['hole'], v['x'], v['y'], L[:3], p['ref'], p['pad'], p['net'], 'FULL' if full else 'PARTLY OFF PAD'))
print('== all vias (any) partly over a pad on outer layers, block box')
for v in M['vias']:
    if not inbox(v['x'], v['y']):
        continue
    r = v['size'] / 2
    for p in pads:
        for L in ('Top Layer', 'Bottom Layer'):
            if L not in p['layers'] or L not in v['span']:
                continue
            ox = p['w'] / 2 + r - abs(v['x'] - p['x']); oy = p['h'] / 2 + r - abs(v['y'] - p['y'])
            if ox > 0 and oy > 0:
                full = abs(v['x'] - p['x']) + r <= p['w'] / 2 + 1e-6 and abs(v['y'] - p['y']) + r <= p['h'] / 2 + 1e-6
                if not full:
                    print('  %s via %.2f/%.2f (%.3f,%.3f) span %s-%s overlaps %s-%s (%s) PARTLY' % (v['net'], v['size'], v['hole'], v['x'], v['y'], v['span'][0][:3], v['span'][-1][:3], p['ref'], p['pad'], p['net']))
print('== plan track widths per net/layer (min)')
mw = {}
for t in P['tracks']:
    k = (t['net'], t['layer']); mw[k] = min(mw.get(k, 9), t['w'])
for k in sorted(mw): print('  ', k, mw[k])
print('== acute angles (<90 deg interior) among block-net tracks, same net+layer, shared endpoint')
T = [t for t in M['tracks'] if t['net'] in NETS and (inbox(t['x1'], t['y1']) or inbox(t['x2'], t['y2']))]
def ends(t): return [((round(t['x1'], 3), round(t['y1'], 3)), (t['x2'], t['y2'])), ((round(t['x2'], 3), round(t['y2'], 3)), (t['x1'], t['y1']))]
seen = set()
for i, a in enumerate(T):
    for j in range(i + 1, len(T)):
        b = T[j]
        if a['net'] != b['net'] or a['layer'] != b['layer']:
            continue
        for pa, oa in ends(a):
            for pb, ob in ends(b):
                if pa == pb:
                    va = (oa[0] - pa[0], oa[1] - pa[1]); vb = (ob[0] - pb[0], ob[1] - pb[1])
                    la, lb = math.hypot(*va), math.hypot(*vb)
                    if la < 1e-6 or lb < 1e-6: continue
                    ang = math.degrees(math.acos(max(-1, min(1, (va[0] * vb[0] + va[1] * vb[1]) / la / lb))))
                    if ang < 89.9:
                        print('  %s %s at %s angle %.1f (w %.3f/%.3f)' % (a['net'], a['layer'][:6], pa, ang, a['w'], b['w']))
def segd(px, py, t):
    ax, ay, bx, by = t['x1'], t['y1'], t['x2'], t['y2']
    dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy
    u = 0 if L2 == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - ax - u * dx, py - ay - u * dy)
def segseg(a, b):
    # min distance between two segments (sampled)
    best = 9
    for k in range(41):
        u = k / 40
        best = min(best, segd(a['x1'] + u * (a['x2'] - a['x1']), a['y1'] + u * (a['y2'] - a['y1']), b),
                   segd(b['x1'] + u * (b['x2'] - b['x1']), b['y1'] + u * (b['y2'] - b['y1']), a))
    return best
print('== PWR_SW neighbours: edge-to-edge copper gaps < 0.35 mm (same layer) and overlaps on other layers')
SW = [t for t in M['tracks'] if t['net'] == 'PWR_SW']
for s in SW:
    for t in M['tracks']:
        if t['net'] == 'PWR_SW': continue
        d = segseg(s, t) - s['w'] / 2 - t['w'] / 2
        if t['layer'] == s['layer'] and d < 0.35:
            print('  SAME %s: %s w%.2f gap %.3f' % (t['layer'][:6], t['net'], t['w'], d))
        elif t['layer'] != s['layer'] and d < 0 and t['net'] != 'GND':
            print('  CROSS on %s: %s w%.2f (SW on %s)' % (t['layer'], t['net'], t['w'], s['layer'][:6]))
    for p in pads:
        if 'Bottom Layer' in p['layers'] and p['net'] != 'PWR_SW':
            dx = max(0, abs(segd(p['x'], p['y'], s)))
            # rect distance approx: sample
            best = 9
            for k in range(81):
                u = k / 80; x = s['x1'] + u * (s['x2'] - s['x1']); y = s['y1'] + u * (s['y2'] - s['y1'])
                ex = max(0, abs(x - p['x']) - p['w'] / 2); ey = max(0, abs(y - p['y']) - p['h'] / 2)
                best = min(best, math.hypot(ex, ey) - s['w'] / 2)
            if best < 0.35:
                print('  PAD %s-%s %s gap %.3f' % (p['ref'], p['pad'], p['net'], best))
print('== L8 footprint shadow (inner-layer copper under L8 pads/body, x 11.9-14.2, y 10.35-13.75)')
for t in M['tracks']:
    if t['layer'] in ('L3-SIG', 'L4-SIG'):
        for k in range(21):
            u = k / 20; x = t['x1'] + u * (t['x2'] - t['x1']); y = t['y1'] + u * (t['y2'] - t['y1'])
            if 11.9 <= x <= 14.2 and 10.35 <= y <= 13.75:
                print('  %s %s w%.3f (%.2f,%.2f)-(%.2f,%.2f)' % (t['net'], t['layer'], t['w'], t['x1'], t['y1'], t['x2'], t['y2'])); break
print('== VU vias in block box')
for v in M['vias']:
    if v['net'] in ('VU', 'VBATT', 'USB5V0') and inbox(v['x'], v['y']):
        print('  %s (%.3f,%.3f) %.2f/%.2f %s-%s' % (v['net'], v['x'], v['y'], v['size'], v['hole'], v['span'][0][:3], v['span'][-1][:3]))
