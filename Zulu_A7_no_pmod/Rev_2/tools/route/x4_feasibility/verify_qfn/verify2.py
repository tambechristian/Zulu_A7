import json, math, sys, collections, copy
T = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools'
sys.path.insert(0, T)
import route_conn as C
import body_check as BC
M0 = json.load(open(T + '/route/bodies/base.json'))
D0 = json.load(open(T + '/route/bodies/comps.json'))
tag = sys.argv[1] if len(sys.argv) > 1 else 'vu'
MA = json.load(open('modelA_d6_vu.json' if tag == 'vu' else 'modelA_d6.json'))
PL = json.load(open('best_plan_vu_d6.json' if tag == 'vu' else 'best_plan_d6.json'))
STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
def span(v):
    return v.get('span') or STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]
M = copy.deepcopy(MA)
M['tracks'] += PL['tracks']
M['vias'] += [dict(v, span=span(v)) for v in PL['vias']]
L = lambda t: math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1'])
oc = C.open_count(C.islands(M))
print('OPEN after plan', {k: v for k, v in oc.items() if v})
ob = C.open_count(C.islands(json.load(open(T + '/route/bodies/base.json'))))
print('OPEN in base', {k: v for k, v in ob.items() if v})

# ---- new pads vs ALL other copper on shared layers (kept + plan), exact ----
new = [p for p in M['pads'] if p['ref'] in ('U2', 'X4')]
viol = []
for p in new:
    for t in M['tracks']:
        if t['layer'] != 'Top Layer' or (t['net'] == p['net'] and p['net']):
            continue
        g = C.pad_seg(p, (t['x1'], t['y1'], t['x2'], t['y2'])) - t['w'] / 2
        if g < 0.09 - 1e-6:
            viol.append(('trk', p['ref'], p['pad'], t['net'], round(g, 3)))
    for v in M['vias']:
        if 'Top Layer' not in span(v) or (v['net'] == p['net'] and p['net']):
            continue
        g = C.pad_point(p, v['x'], v['y']) - v['size'] / 2
        if g < 0.09 - 1e-6:
            viol.append(('via', p['ref'], p['pad'], v['net'], round(g, 3)))
print('new pad vs foreign Top copper < 0.09:', viol)
# pad to pad (any part), Top or through-hole
def pbox(p):
    return (p['x'] - p['w'] / 2, p['y'] - p['h'] / 2, p['x'] + p['w'] / 2, p['y'] + p['h'] / 2)
pp = []
for a in new:
    for b in M['pads']:
        if b is a or (b['layers'] and 'Top Layer' not in b['layers']):
            continue
        if b['ref'] == a['ref'] and b['pad'] == a['pad']:
            continue
        if C.pad_round(b) or b['shape'] in ('circle', 'round'):
            g = C.pad_point(a, b['x'], b['y']) - min(b['w'], b['h']) / 2
        else:
            g = BC.gap(pbox(a), pbox(b))
        if b['ref'] == a['ref'] and g > 0.16:
            continue
        pp.append((round(g, 3), a['ref'] + '-' + a['pad'], b['ref'] + '-' + b['pad'], b['net']))
pp.sort()
print('nearest pad-pad', [x for x in pp if x[0] < 0.7][:14])
print('edge min new pads', min(min(pbox(p)[0], pbox(p)[1], 60.96 - pbox(p)[2], 25.4 - pbox(p)[3]) for p in new))

# ---- copper under the QFN EP area / package (variant A has no EP land) ----
ep = (30.375 - 2.25, 14.675 - 2.25, 30.375 + 2.25, 14.675 + 2.25)
inn = lambda x, y, b: b[0] <= x <= b[2] and b[1] <= y <= b[3]
uv = [(v['net'], v['x'], v['y'], span(v)[0], span(v)[-1]) for v in M['vias'] if 'Top Layer' in span(v) and inn(v['x'], v['y'], ep)]
ut = collections.Counter(t['net'] for t in M['tracks'] if t['layer'] == 'Top Layer' and (inn(t['x1'], t['y1'], ep) or inn(t['x2'], t['y2'], ep)))
print('Top vias inside EP 4.5 mm square:', len(uv), uv[:30])
print('Top tracks with an end inside EP square, by net:', dict(ut))

# ---- net metrics: USB, VBATT etc, base vs final ----
def netstat(MM, n):
    ts = [t for t in MM['tracks'] if t['net'] == n]
    vs = [v for v in MM['vias'] if v['net'] == n]
    bl = collections.defaultdict(float)
    for t in ts:
        bl[(t['layer'], t['w'])] += L(t)
    return round(sum(L(t) for t in ts), 2), len(vs), {'%s/%.3f' % k: round(v, 1) for k, v in sorted(bl.items())}
for n in ('USB_D_P', 'USB_D_N', 'VBATT', 'VU', 'USB5V0', 'TCK', 'TDI', 'TMS', 'TDO', 'CLK-12M-FT', 'FT-REF', 'FT-VCORE', 'D6'):
    print(n, 'base', netstat(M0, n), '\n    final', netstat(M, n))
# USB coupling: average separation of D_P / D_N Top/inner segments in final
json.dump(M, open('final_%s.json' % tag, 'w'))
