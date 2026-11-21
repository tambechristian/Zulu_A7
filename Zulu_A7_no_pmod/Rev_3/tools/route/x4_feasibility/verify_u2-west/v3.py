"""Full copper clearance audit (all items, not only new ones) in a window, for a model (+ optional plan)."""
import json, math, sys, collections
T0 = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_3/tools'
sys.path.insert(0, T0)
import route_conn as RC
STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
SDR = set(['A%d' % i for i in range(13)] + ['BS0', 'BS1', 'CAS#', 'RAS#', 'WE#', 'CKE', 'LDQM', 'UDQM', 'SDRAM-CLK',
           'SDRAM-CS#'] + ['D%d' % i for i in range(16)] + ['SDRAM-D%d' % i for i in range(16)])
WIN = (12, -1, 42, 26.5)

def load(model, plan=None):
    M = json.load(open(model))
    if plan:
        P = json.load(open(plan))
        M['tracks'] = M['tracks'] + P['tracks']
        M['vias'] = M['vias'] + [dict(v, span=v.get('span') or STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]) for v in P['vias']]
    return M

def items(M):
    out = []
    for p in M['pads']:
        L = p['layers'] or STACK
        out.append(('pad', p, set(L), p['net'], p['ref'] + '.' + p['pad']))
    for t in M['tracks']:
        out.append(('trk', t, {t['layer']}, t['net'], 'T%.3f,%.3f' % (t['x1'], t['y1'])))
    for v in M['vias']:
        out.append(('via', v, set(v['span']), v['net'], 'V%.3f,%.3f' % (v['x'], v['y'])))
    return [o for o in out if inwin(o)]

def inwin(o):
    k, g = o[0], o[1]
    if k == 'trk': x, y = (g['x1'] + g['x2']) / 2, (g['y1'] + g['y2']) / 2
    else: x, y = g['x'], g['y']
    return WIN[0] <= x <= WIN[2] and WIN[1] <= y <= WIN[3]

def dist(a, b):
    ka, A = a[0], a[1]; kb, B = b[0], b[1]
    if ka > kb: (ka, A), (kb, B) = (kb, B), (ka, A)
    seg = lambda t: (t['x1'], t['y1'], t['x2'], t['y2'])
    if ka == 'pad' and kb == 'pad':
        if RC.pad_round(A) and RC.pad_round(B):
            return math.hypot(A['x'] - B['x'], A['y'] - B['y']) - (min(A['w'], A['h']) + min(B['w'], B['h'])) / 2
        if RC.pad_round(A) or RC.pad_round(B):
            c, r = (A, B) if RC.pad_round(A) else (B, A)
            return RC.pad_point(r, c['x'], c['y']) - min(c['w'], c['h']) / 2
        dx = abs(A['x'] - B['x']) - (A['w'] + B['w']) / 2; dy = abs(A['y'] - B['y']) - (A['h'] + B['h']) / 2
        return math.hypot(dx, dy) if dx > 0 and dy > 0 else max(dx, dy)
    if ka == 'pad' and kb == 'trk': return RC.pad_seg(A, seg(B)) - B['w'] / 2
    if ka == 'pad' and kb == 'via': return RC.pad_point(A, B['x'], B['y']) - B['size'] / 2
    if ka == 'trk' and kb == 'trk': return RC.seg_seg(seg(A), seg(B)) - (A['w'] + B['w']) / 2
    if ka == 'trk' and kb == 'via': return RC.seg_dist(*seg(A), B['x'], B['y']) - (A['w'] + B['size']) / 2
    return math.hypot(A['x'] - B['x'], A['y'] - B['y']) - (A['size'] + B['size']) / 2

def audit(M, tag):
    I = items(M)
    # grid bucket
    G = collections.defaultdict(list)
    def bb(o):
        k, g = o[0], o[1]
        if k == 'trk': return (min(g['x1'], g['x2']) - g['w'], min(g['y1'], g['y2']) - g['w'], max(g['x1'], g['x2']) + g['w'], max(g['y1'], g['y2']) + g['w'])
        if k == 'via': return (g['x'] - g['size'], g['y'] - g['size'], g['x'] + g['size'], g['y'] + g['size'])
        return (g['x'] - g['w'], g['y'] - g['h'], g['x'] + g['w'], g['y'] + g['h'])
    for i, o in enumerate(I):
        b = bb(o)
        for gx in range(int(b[0]), int(b[2]) + 1):
            for gy in range(int(b[1]), int(b[3]) + 1):
                G[(gx, gy)].append(i)
    seen = set(); bad = []
    for cell, L in G.items():
        for x in range(len(L)):
            for y in range(x + 1, len(L)):
                i, j = L[x], L[y]
                if (i, j) in seen: continue
                seen.add((i, j))
                a, b = I[i], I[j]
                sh = a[2] & b[2] & set(STACK)
                if not sh: continue
                if a[0] == 'pad' and b[0] == 'pad' and a[4].split('.')[0] == b[4].split('.')[0]: continue
                same = a[3] and a[3] == b[3]
                if a[0] == 'via' and b[0] == 'via':
                    hh = math.hypot(a[1]['x'] - b[1]['x'], a[1]['y'] - b[1]['y']) - (a[1]['hole'] + b[1]['hole']) / 2
                    if hh < 0.24 - 1e-6 and not (math.hypot(a[1]['x'] - b[1]['x'], a[1]['y'] - b[1]['y']) < 1e-3):
                        bad.append(('hole', round(hh, 3), a[3], a[4], b[3], b[4]))
                if same: continue
                c = 0.10 if (a[3] in SDR or b[3] in SDR) and sh & {'L3-SIG', 'L4-SIG'} else 0.09
                # planes: L2/L5 copper of plane nets are pours, ignore pour-layer clearances (not modelled)
                d = dist(a, b)
                if d < c - 1e-4:
                    bad.append(('clr', round(d, 3), a[3], a[4], b[3], b[4], sorted(sh)[0]))
    return bad

if __name__ == '__main__':
    base = audit(load(T0 + '/route/bodies/base.json'), 'base')
    key = lambda r: r[:1] + tuple(sorted([(r[2], r[3]), (r[4], r[5])]))
    kb = set(map(key, base))
    print('base board window findings:', len(kb))
    for model, plan in [(sys.argv[1], None), (sys.argv[1], sys.argv[2])] if len(sys.argv) > 2 else [(sys.argv[1], None)]:
        r = audit(load(model, plan), model)
        new = [x for x in r if key(x) not in kb]
        print('\n%s + %s: %d findings, %d not in base' % (model.split('/')[-1], plan and plan.split('/')[-1], len(r), len(new)))
        for x in sorted(new, key=lambda x: x[1])[:60]: print('  ', x)
