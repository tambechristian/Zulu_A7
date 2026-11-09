"""Exact check of a router plan against the board model (independent of the router's raster).

    python tools/route_check.py tools/route/stage3.json

The model is tools/route/model.json minus the plan's 'remove' tracks, plus the plan. Every NEW track and via is
checked with exact geometry against all copper of other nets on a shared layer: clearance 0.09 mm (0.10 for SDRAM
nets on L3/L4, 0.20 for SDRAM-CLK there), 0.30 mm to the board edge (as a 0.3 mm inset rectangle; rounded corners
as 1.2 mm squares), via holes 0.24 mm apart (spans sharing a layer, the same net included, except a stack at exactly one point; and NPTH/PTH holes), track widths >= the
per-layer minimum. Then connectivity is recounted (route_conn) with the plan merged in.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import route_conn as C  # noqa: E402
import router as R  # noqa: E402

STACK = R.STACK


def span(v):
    if 'span' in v:
        return v['span']
    return STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]


def rule_flags(argv):
    """--clear X and --sdram-plain, as router.py: the plan is judged by the rules it was routed with"""
    out = []
    i = 0
    while i < len(argv):
        if argv[i] == '--clear':
            R.CLEAR = float(argv[i + 1])
            i += 2
            continue
        if argv[i] == '--sdram-plain':
            R.SDRAM_RULES = False
            i += 1
            continue
        out.append(argv[i])
        i += 1
    if R.CLEAR != 0.09 or not R.SDRAM_RULES:
        print('rules: clearance %.4f, SDRAM rules %s' % (R.CLEAR, 'on' if R.SDRAM_RULES else 'OFF (plain)'))
    return out


def main():
    sys.argv[:] = rule_flags(sys.argv)
    plan = json.load(open(sys.argv[1]))
    M = json.load(open(sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'route', 'model.json')))
    rm = plan.get('remove', [])
    def same(t, r):
        return t['net'] == r['net'] and t['layer'] == r['layer'] and \
            {(round(t['x1'], 3), round(t['y1'], 3)), (round(t['x2'], 3), round(t['y2'], 3))} == \
            {(round(r['x1'], 3), round(r['y1'], 3)), (round(r['x2'], 3), round(r['y2'], 3))}
    M['tracks'] = [t for t in M['tracks'] if not any(same(t, r) for r in rm)]
    rmv = plan.get('remove_vias', [])
    if rmv:
        def samev(v, r):
            return v['net'] == r['net'] and abs(v['x'] - r['x']) < 0.002 and abs(v['y'] - r['y']) < 0.002 and                 abs(v['hole'] - r['hole']) < 0.002
        M['vias'] = [v for v in M['vias'] if not any(samev(v, r) for r in rmv)]
    old_t, old_v = len(M['tracks']), len(M['vias'])
    newv = [dict(v, span=span(v)) for v in plan['vias']]
    M['tracks'] = M['tracks'] + plan['tracks']
    M['vias'] = M['vias'] + newv
    bad = []
    W, H = M['board']['w'], M['board']['h']

    def clr(n1, n2, layer):
        return max(R.clearance(n1, layer), R.clearance(n2, layer))

    def edge_ok_pt(x, y, r):
        if x - r < R.EDGE or y - r < R.EDGE or x + r > W - R.EDGE or y + r > H - R.EDGE:
            return False
        for cx, cy in ((0, 0), (W, 0), (0, H), (W, H)):
            if abs(x - cx) < 1.2 + r and abs(y - cy) < 1.2 + r:
                return False
        return True

    # candidate obstacles by layer
    def items_on(layer):
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

    def gap_to(kind, o, geom):
        """distance between our object (geom: ('s', x1,y1,x2,y2, r) or ('c', x, y, r)) and obstacle copper"""
        if geom[0] == 's':
            s = geom[1:5]
            r = geom[5]
            if kind == 'p':
                return C.pad_seg(o, s) - r
            if kind == 't':
                return C.seg_seg(s, (o['x1'], o['y1'], o['x2'], o['y2'])) - r - o['w'] / 2
            return C.seg_dist(s[0], s[1], s[2], s[3], o['x'], o['y']) - r - o['size'] / 2
        x, y, r = geom[1:4]
        if kind == 'p':
            return C.pad_point(o, x, y) - r
        if kind == 't':
            return C.seg_dist(o['x1'], o['y1'], o['x2'], o['y2'], x, y) - r - o['w'] / 2
        return math.hypot(o['x'] - x, o['y'] - y) - r - o['size'] / 2

    cache = {l: list(items_on(l)) for l in STACK}
    for t in plan['tracks']:
        if t['w'] < R.width(t['net'], t['layer']) - 1e-6:
            bad.append('width %s %s %.4f' % (t['net'], t['layer'], t['w']))
        geom = ('s', t['x1'], t['y1'], t['x2'], t['y2'], t['w'] / 2)
        for k, o in cache[t['layer']]:
            if o['net'] and o['net'] == t['net']:
                continue
            g = gap_to(k, o, geom)
            if g < clr(t['net'], o['net'] or '', t['layer']) - 1e-4:
                bad.append('track %s %s (%.3f,%.3f)-(%.3f,%.3f) %.4f from %s %s' % (
                    t['net'], t['layer'], t['x1'], t['y1'], t['x2'], t['y2'], g, k, o.get('net') or o.get('ref')))
        for x, y in ((t['x1'], t['y1']), (t['x2'], t['y2'])):
            if not edge_ok_pt(x, y, t['w'] / 2):
                bad.append('edge track %s at %.3f,%.3f' % (t['net'], x, y))
    for v in newv:
        geom = ('c', v['x'], v['y'], v['size'] / 2)
        for l in v['span']:
            for k, o in cache[l]:
                if o['net'] and o['net'] == v['net']:
                    continue
                if k == 'v' and o is v:
                    continue
                g = gap_to(k, o, geom)
                if g < clr(v['net'], o['net'] or '', l) - 1e-4:
                    bad.append('via %s at %.3f,%.3f on %s %.4f from %s %s' % (v['net'], v['x'], v['y'], l, g, k,
                                                                             o.get('net') or o.get('ref')))
        for o in M['vias']:
            if o is v or not (set(o['span']) & set(v['span'])):
                continue
            if math.hypot(o['x'] - v['x'], o['y'] - v['y']) < 1e-6:
                continue                               # a stack at exactly the same point (Altium exempts it)
            d = math.hypot(o['x'] - v['x'], o['y'] - v['y']) - o['hole'] / 2 - v['hole'] / 2
            if d < R.HOLE_HOLE - 1e-4:
                bad.append('hole-hole via %s at %.3f,%.3f %.4f from via %s' % (v['net'], v['x'], v['y'], d, o['net']))
        for p in M['pads']:
            if p['drill'] > 0 and p['net'] != v['net']:
                d = math.hypot(p['x'] - v['x'], p['y'] - v['y']) - p['drill'] / 2 - v['hole'] / 2
                if d < R.HOLE_HOLE - 1e-4:
                    bad.append('hole-hole via %s at %.3f,%.3f %.4f from %s-%s' % (v['net'], v['x'], v['y'], d,
                                                                                 p['ref'], p['pad']))
        if not edge_ok_pt(v['x'], v['y'], v['size'] / 2):
            bad.append('edge via %s at %.3f,%.3f' % (v['net'], v['x'], v['y']))
    bad = sorted(set(bad))
    oc = C.open_count(C.islands(M))
    print('plan: %d tracks, %d vias, %d removed; board then: %d tracks, %d vias' % (
        len(plan['tracks']), len(plan['vias']), len(rm), len(M['tracks']), len(M['vias'])))
    print('violations: %d' % len(bad))
    for b in bad[:30]:
        print('  ' + b)
    print('open connections after the plan: %d on %d nets' % (sum(oc.values()), len(oc)))
    print('PASS' if not bad else 'FAIL')
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main())
