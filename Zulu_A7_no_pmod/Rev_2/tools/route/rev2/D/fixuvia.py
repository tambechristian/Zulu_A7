"""(helpers copied from fixvia.py)
fixvia.py <base_moved> <plan_in> <plan_out>
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

def pad_hits(v):
    sp = span(v); r = v['size'] / 2
    return [p for p in smd if p['layers'][0] in sp and C.pad_point(p, v['x'], v['y']) < r - 1e-6]
cols = {}
for v in P['vias']:
    if span(v) == STACK: continue
    cols.setdefault((v['net'], round(v['x'], 4), round(v['y'], 4)), []).append(v)
newt, kept, moved = [], [], []
for (net, x0, y0), vs in cols.items():
    hits = [p for v in vs for p in pad_hits(v)]
    if not hits: continue
    layers = sorted({L for v in vs for L in span(v)}, key=STACK.index)
    # connections at the point, by layer (plan + board tracks, pads)
    att = {}
    for t in M['tracks']:
        if t['net'] == net and any(math.hypot(a - x0, b - y0) < 1e-3 for a, b in ((t['x1'], t['y1']), (t['x2'], t['y2']))):
            att.setdefault(t['layer'], []).append(t)
    padL = {p['layers'][0] for p in B['pads'] if not p['drill'] and p['net'] == net and C.pad_point(p, x0, y0) < 1e-6}
    conn = sorted((set(att) | padL) & set(layers), key=STACK.index)
    sameloc = [v for v in M['vias'] if abs(v['x'] - x0) < 1e-6 and abs(v['y'] - y0) < 1e-6 and v['net'] == net]
    if any(span(v) == STACK for v in sameloc) or len(sameloc) != len(vs):
        kept.append(((net, x0, y0), 'board via at the same point')); continue
    widths = {L: max([t['w'] for t in att.get(L, [])] + [R.width(net, L)]) for L in conn}
    best = None
    for i in range(-40, 41):
        for j in range(-40, 41):
            x, y = round(x0 + i * 0.025, 4), round(y0 + j * 0.025, 4)
            d = math.hypot(x - x0, y - y0)
            if d < 1e-6 or (best and d >= best[0]): continue
            if not ok_via(x, y, net, sameloc, layers, 0.15, 0.15): continue
            if any(not ok_track((x0, y0, x, y), net, L, widths[L], sameloc) for L in conn): continue
            best = (d, x, y)
    if not best:
        kept.append(((net, x0, y0), [p['ref'] + '-' + p['pad'] for p in hits])); continue
    d, x, y = best
    for v in vs: v['x'], v['y'] = x, y
    for L in conn: newt.append(dict(net=net, layer=L, w=widths[L], x1=x0, y1=y0, x2=x, y2=y))
    moved.append(((net, x0, y0), (x, y), round(d, 3), conn, [p['ref'] + '-' + p['pad'] for p in hits]))
P['tracks'] += newt
for m in moved: print('moved', m)
for k in kept: print('kept', k)
json.dump(P, open(sys.argv[3], 'w'), indent=1)
