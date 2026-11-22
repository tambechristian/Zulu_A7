"""exact clearance helpers in route_check's rules (read-only)"""
import math, sys
sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1/tools')
import route_conn as C
import router as R
STACK = R.STACK

def items_on(M, layer):
    for p in M['pads']:
        ls = p['layers'] or (STACK if p['drill'] > 0 else [])
        if layer in ls:
            yield 'p', p
    for t in M['tracks']:
        if t['layer'] == layer:
            yield 't', t
    for v in M['vias']:
        if layer in v['span']:
            yield 'v', v

def gap_circle(k, o, x, y, r):
    if k == 'p':
        return C.pad_point(o, x, y) - r
    if k == 't':
        return C.seg_dist(o['x1'], o['y1'], o['x2'], o['y2'], x, y) - r - o['w'] / 2
    return math.hypot(o['x'] - x, o['y'] - y) - r - o['size'] / 2

def gap_seg(k, o, s, r):
    if k == 'p':
        return C.pad_seg(o, s) - r
    if k == 't':
        return C.seg_seg(s, (o['x1'], o['y1'], o['x2'], o['y2'])) - r - o['w'] / 2
    return C.seg_dist(s[0], s[1], s[2], s[3], o['x'], o['y']) - r - o['size'] / 2

def via_report(M, net, x, y, size, hole, span, n=4):
    out = []
    for l in span:
        for k, o in items_on(M, l):
            if o.get('net') == net and o.get('net'):
                continue
            g = gap_circle(k, o, x, y, size / 2)
            out.append((round(g, 4), l, k, o.get('net') or o.get('ref'), (o.get('x', o.get('x1')), o.get('y', o.get('y1')))))
    di = set(range(STACK.index(span[0]), STACK.index(span[-1])))
    for v in M['vias']:
        dv = set(range(STACK.index(v['span'][0]), STACK.index(v['span'][-1])))
        if di & dv:
            d = math.hypot(v['x'] - x, v['y'] - y)
            if d < 1e-6:
                continue
            out.append((round(d - v['hole'] / 2 - hole / 2 - 0.24 + 0.09, 4), 'HOLE', 'v', v['net'], (v['x'], v['y'])))
    for p in M['pads']:
        if p['drill'] > 0 and p['net'] != net:
            d = math.hypot(p['x'] - x, p['y'] - y)
            out.append((round(d - p['drill'] / 2 - hole / 2 - 0.24 + 0.09, 4), 'HOLE', 'p', p['ref'], (p['x'], p['y'])))
    out.sort()
    return out[:n]   # values are clearance-equivalents: >= 0.09 passes (HOLE rows shifted so 0.09 = the 0.24 rule)

def track_report(M, t, n=4):
    out = []
    s = (t['x1'], t['y1'], t['x2'], t['y2'])
    for k, o in items_on(M, t['layer']):
        if o.get('net') == t['net'] and o.get('net'):
            continue
        g = gap_seg(k, o, s, t['w'] / 2)
        out.append((round(g, 4), k, o.get('net') or o.get('ref'), (o.get('x', o.get('x1')), o.get('y', o.get('y1')))))
    out.sort()
    return out[:n]
