"""fixvia.py <base_moved> <plan_in> <plan_out>
Every NEW through via (0.35/0.20) whose land overlaps an SMD pad is moved off all SMD pads: the via and the one plan
track tying it to its anchor (or the pad it sits in) are replaced by a through via at the nearest legal spot plus a
straight track from the anchor on the same layer. Legal = clearance to all other-net copper on all six layers,
hole-to-hole 0.24, no overlap with any SMD pad on Top/Bottom, board edge. route_check is the final judge."""
import json, math, sys
T = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools'
sys.path.insert(0, T)
import route_conn as C, router as R
STACK = R.STACK
B = json.load(open(sys.argv[1])); P = json.load(open(sys.argv[2]))
def span(v): return v['span'] if 'span' in v else STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]
def tk(t): return (t['net'], t['layer'], frozenset([(round(t['x1'], 3), round(t['y1'], 3)), (round(t['x2'], 3), round(t['y2'], 3))]))
rk = {tk(t) for t in P.get('remove', [])}
rv = P.get('remove_vias', [])
def gone(v): return any(v['net'] == r['net'] and abs(v['x'] - r['x']) < .002 and abs(v['y'] - r['y']) < .002 and abs(v['hole'] - r['hole']) < .002 for r in rv)
M = dict(B); M['tracks'] = [t for t in B['tracks'] if tk(t) not in rk] + P['tracks']
M['vias'] = [dict(v, span=span(v)) for v in B['vias'] if not gone(v)] + [dict(v, span=span(v)) for v in P['vias']]
smd = [p for p in B['pads'] if not p['drill']]
W, H = B['board']['w'], B['board']['h']
def in_pad(x, y, r): return [p for p in smd if p['layers'][0] in ('Top Layer', 'Bottom Layer') and C.pad_point(p, x, y) < r - 1e-6]
def clr(n1, n2, L): return max(R.clearance(n1, L), R.clearance(n2 or '', L)) + 0.005
def ok_via(x, y, net, skip, layers=STACK, r=0.175, hole=0.2):
    if x - r < 0.3 or y - r < 0.3 or x + r > W - 0.3 or y + r > H - 0.3: return False
    if [p for p in in_pad(x, y, r) if p['layers'][0] in layers]: return False
    for p in B['pads']:
        ls = STACK if p['drill'] else p['layers']
        if not set(ls) & set(layers): continue
        if p['net'] != net or not p['net']:
            if C.pad_point(p, x, y) - r < clr(net, p['net'], [l for l in ls if l in layers][0]): return False
        if p['drill'] and math.hypot(p['x'] - x, p['y'] - y) - p['drill'] / 2 - hole / 2 < 0.24: return False
    for t in M['tracks']:
        if t in skip or t['net'] == net or t['layer'] not in layers: continue
        if C.seg_dist(t['x1'], t['y1'], t['x2'], t['y2'], x, y) - r - t['w'] / 2 < clr(net, t['net'], t['layer']): return False
    for v in M['vias']:
        if v in skip or not set(v['span']) & set(layers): continue
        d = math.hypot(v['x'] - x, v['y'] - y)
        if d - v['hole'] / 2 - hole / 2 < 0.24: return False
        if v['net'] != net and d - r - v['size'] / 2 < max(clr(net, v['net'], L) for L in v['span'] if L in layers): return False
    return True
def ok_track(s, net, L, w, skip):
    for p in B['pads']:
        ls = STACK if p['drill'] else p['layers']
        if L in ls and p['net'] != net and C.pad_seg(p, s) - w / 2 < clr(net, p['net'], L): return False
    for t in M['tracks']:
        if t in skip or t['net'] == net or t['layer'] != L: continue
        if C.seg_seg(s, (t['x1'], t['y1'], t['x2'], t['y2'])) - w / 2 - t['w'] / 2 < clr(net, t['net'], L): return False
    for v in M['vias']:
        if v in skip or v['net'] == net or L not in v['span']: continue
        if C.seg_dist(s[0], s[1], s[2], s[3], v['x'], v['y']) - w / 2 - v['size'] / 2 < clr(net, v['net'], L): return False
    return True
newv, newt, dropv, dropt = [], [], [], []
for v in P['vias']:
    if span(v) != STACK: continue
    hit = in_pad(v['x'], v['y'], v['size'] / 2)
    if not hit: continue
    att = [t for t in P['tracks'] if any(math.hypot(a - v['x'], b - v['y']) < 1e-3 for a, b in ((t['x1'], t['y1']), (t['x2'], t['y2'])))]
    if len(att) > 1:
        print('SKIP (several tracks)', v, att); continue
    if att:
        t = att[0]; L = t['layer']; w = max(t['w'], R.width(v['net'], L))
        ax, ay = (t['x2'], t['y2']) if math.hypot(t['x1'] - v['x'], t['y1'] - v['y']) < 1e-3 else (t['x1'], t['y1'])
    else:
        p = hit[0]; L = p['layers'][0]; w = R.width(v['net'], L); ax, ay = p['x'], p['y']; t = None
    skip = [vv for vv in M['vias'] if abs(vv['x'] - v['x']) < 1e-6 and abs(vv['y'] - v['y']) < 1e-6 and vv['net'] == v['net']] + ([t] if t else [])
    best = None
    for i in range(-48, 49):
        for j in range(-48, 49):
            x, y = round(ax + i * 0.025, 4), round(ay + j * 0.025, 4)
            d = math.hypot(x - ax, y - ay)
            if best and d >= best[0]: continue
            if not ok_via(x, y, v['net'], skip): continue
            if d > 1e-6 and not ok_track((ax, ay, x, y), v['net'], L, w, skip): continue
            best = (d, x, y)
    kind = 'through'
    SL = STACK[1:] if L == 'Bottom Layer' else STACK[:2]
    if not best and v['net'] == 'GND':
        # microvia column from the anchor layer to L2 (no land on the other outer layer)
        for i in range(-48, 49):
            for j in range(-48, 49):
                x, y = round(ax + i * 0.025, 4), round(ay + j * 0.025, 4)
                d = math.hypot(x - ax, y - ay)
                if best and d >= best[0]: continue
                if not ok_via(x, y, v['net'], skip, SL, 0.15, 0.15): continue
                if d > 1e-6 and not ok_track((ax, ay, x, y), v['net'], L, w, skip): continue
                best = (d, x, y)
        kind = 'stack'
    if not best:
        print('NO SPOT', v); continue
    d, x, y = best
    dropv.append(v); dropt += [t] if t else []
    if kind == 'through':
        newv.append(dict(net=v['net'], x=x, y=y, size=0.35, hole=0.2, **{'from': 'Top Layer', 'to': 'Bottom Layer'}))
    else:
        for a, b in zip(SL[::-1], SL[::-1][1:]) if L == 'Bottom Layer' else [('Top Layer', 'L2-GND')]:
            hi, lo = sorted((a, b), key=STACK.index)
            newv.append(dict(net=v['net'], x=x, y=y, size=0.27 if (hi, lo) == ('L3-SIG', 'L4-SIG') else 0.3, hole=0.15, **{'from': hi, 'to': lo}))
        print('  as a microvia column', SL, 'in pad:', [q['ref'] + '-' + q['pad'] for q in in_pad(x, y, 0.15)])
    if d > 1e-6: newt.append(dict(net=v['net'], layer=L, w=w, x1=ax, y1=ay, x2=x, y2=y))
    print('moved %s via (%.3f,%.3f) in %s -> (%.3f,%.3f), %.3f mm track on %s' % (v['net'], v['x'], v['y'], [q['ref'] + '-' + q['pad'] for q in hit], x, y, d, L))
P['vias'] = [v for v in P['vias'] if not any(v is q for q in dropv)] + newv
P['tracks'] = [t for t in P['tracks'] if not any(t is q for q in dropt)] + newt
json.dump(P, open(sys.argv[3], 'w'), indent=1)
