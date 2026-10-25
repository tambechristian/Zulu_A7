"""Routing stage 1 (2026-10-23): transplant the production board's finished U1 escape copper onto the Feather.

U1 sat at rot 0 on both boards; since 2026-10-24 it is rot 180 on the Feather (its SDRAM balls then face U3),
and the under-U1 decoupling turned with it. Production copper is turned by U1's rotation about U1's centre, so production's DRC-clean fan-out around U1 -- ball vias, Top/inner escapes, Bottom decap ties, plane
microvias -- is valid Feather geometry once it is shifted by the U1-centre offset and re-netted per ball.

    "C:/Program Files/KiCad/10.0/bin/python.exe" tools/transplant_u1.py --dump   production copper -> prod_u1_copper.json
    python tools/transplant_u1.py [--r 5.5]                                     plan -> tools/route/stage1_u1.json

PLAN RULES
  - window: |x|,|y| <= R mm from U1's centre on every layer; a track crossing the edge is clipped to it (its outer
    end becomes a stub for the next stage), a via outside it is dropped
  - net: production copper of net N is kept only if N is on a U1 ball; it takes the Feather net of that ball
    (193 balls keep their net, the 18 swapped header balls take the new CHAN net, the 19 balls the Feather no
    longer connects lose their copper)
  - check: every kept primitive against every Feather pad of another net on a layer it occupies, at the 0.09 mm
    clearance rule (pad copper as its box); a conflicting primitive is dropped and reported
Coordinates in the plan are board-relative mm (origin at the board's lower-left corner, y up), as FeatherPlace uses.
"""
import json
import math
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUTD = os.path.join(HERE, 'route')
PROD = os.path.join(ROOT, '..', 'Zulu_Altium_VS_Code', 'Imported zulu_a7.PrjPcb', 'zulu_a7.PcbDoc')
COPPER = os.path.join(OUTD, 'prod_u1_copper.json')
CLEAR = 0.09
# KiCad layer names -> the Feather stack (Altium MID3 = L2-GND, MID1 = L3-SIG, MID2 = L4-SIG, MID4 = L5-VCC3V3)
STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']


def dump():
    import pcbnew
    import wx
    app = wx.App(False)  # noqa: F841
    wx.Log.SetActiveTarget(wx.LogStderr())
    b = pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.ALTIUM_DESIGNER).LoadBoard(PROD, None)
    mm = pcbnew.ToMM
    u1 = b.FindFootprintByReference('U1')
    balls = {p.GetNumber(): (mm(p.GetPosition().x), -mm(p.GetPosition().y), p.GetNetname()) for p in u1.Pads()}
    cx = sum(v[0] for v in balls.values()) / len(balls)
    cy = sum(v[1] for v in balls.values()) / len(balls)
    out = {'u1c': [cx, cy], 'balls': balls, 'tracks': [], 'vias': []}
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA':
            p = t.GetPosition()
            out['vias'].append({'x': mm(p.x), 'y': -mm(p.y), 'net': t.GetNetname(),
                                'from': b.GetLayerName(t.TopLayer()), 'to': b.GetLayerName(t.BottomLayer()),
                                'size': mm(t.GetWidth(pcbnew.F_Cu)), 'drill': mm(t.GetDrillValue())})
        elif t.GetClass() == 'PCB_TRACK':
            s, e = t.GetStart(), t.GetEnd()
            out['tracks'].append({'x1': mm(s.x), 'y1': -mm(s.y), 'x2': mm(e.x), 'y2': -mm(e.y), 'w': mm(t.GetWidth()),
                                  'layer': b.GetLayerName(t.GetLayer()), 'net': t.GetNetname()})
        else:
            sys.exit('unexpected copper object ' + t.GetClass())
    os.makedirs(OUTD, exist_ok=True)
    json.dump(out, open(COPPER, 'w'))
    print('production: %d balls, %d tracks, %d vias' % (len(balls), len(out['tracks']), len(out['vias'])))


def clip(x1, y1, x2, y2, lo_x, lo_y, hi_x, hi_y):
    """Liang-Barsky: the part of the segment inside the box, or None."""
    dx, dy = x2 - x1, y2 - y1
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x1 - lo_x), (dx, hi_x - x1), (-dy, y1 - lo_y), (dy, hi_y - y1)):
        if p == 0:
            if q < 0:
                return None
            continue
        r = q / p
        if p < 0:
            t0 = max(t0, r)
        else:
            t1 = min(t1, r)
        if t0 > t1:
            return None
    return x1 + t0 * dx, y1 + t0 * dy, x1 + t1 * dx, y1 + t1 * dy


def seg_rect(x1, y1, x2, y2, r):
    """Distance from a segment to an axis-aligned rectangle (0 if they touch)."""
    lx, ly, hx, hy = r
    if clip(x1, y1, x2, y2, lx, ly, hx, hy):
        return 0.0
    def pr(px, py):
        return math.hypot(max(lx - px, 0, px - hx), max(ly - py, 0, py - hy))
    def ps(px, py):
        vx, vy = x2 - x1, y2 - y1
        L = vx * vx + vy * vy
        t = 0 if L == 0 else max(0, min(1, ((px - x1) * vx + (py - y1) * vy) / L))
        return math.hypot(px - x1 - t * vx, py - y1 - t * vy)
    return min(pr(x1, y1), pr(x2, y2), ps(lx, ly), ps(lx, hy), ps(hx, ly), ps(hx, hy))


def plan(R):
    sys.path.insert(0, HERE)
    import verify_placement as V
    P = json.load(open(COPPER))
    D = V.D
    def rel(x, y):                                   # verify_placement.D is already board-relative
        return x, y
    u = D['U1']
    # absolute ball positions with U1's rotation applied (verify_placement.abs_pads), keyed by ball name
    fball = {q[1]: ((q[3] + q[5]) / 2, (q[4] + q[6]) / 2, q[2]) for q in V.abs_pads('U1')}
    fcx = sum(v[0] for v in fball.values()) / len(fball)
    fcy = sum(v[1] for v in fball.values()) / len(fball)
    sx, sy = fcx - P['u1c'][0], fcy - P['u1c'][1]
    # U1 may be turned on the Feather (rot 180 since 2026-10-24); production's U1 is rot 0. Copper turns with it
    th = math.radians(D['U1']['rot'] % 360)
    ca, sa = round(math.cos(th), 9), round(math.sin(th), 9)
    pcx, pcy = P['u1c']

    def xf(x, y):
        dx, dy = x - pcx, y - pcy
        return fcx + dx * ca - dy * sa, fcy + dx * sa + dy * ca
    pmap = {}
    for ball, (x, y, n) in P['balls'].items():
        if n:
            f = fball[ball][2] or None
            if pmap.setdefault(n, f) != f:
                sys.exit('production net %s maps to two Feather nets' % n)
    cx, cy = rel(fcx, fcy)
    lo_x, lo_y, hi_x, hi_y = cx - R, cy - R, cx + R, cy + R
    # Feather pads as obstacles, per side
    pads = []
    for ref in D:
        if ref.startswith('_'):
            continue
        for q in V.abs_pads(ref):
            (a, b2), (c, d) = rel(q[3], q[4]), rel(q[5], q[6])
            pads.append((ref, q[1], q[2], (a, b2, c, d), q[7]))
    ROUND = ('U1', 'U3')                             # BGA lands are circles (a square model loses the interstitial sites)
    def gap(ref, r, kind, g):
        """distance from a via point (kind 'p', g = (x, y)) or track (kind 's', g = x1,y1,x2,y2) to pad copper"""
        if ref in ROUND:
            px, py, rad = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2, (r[2] - r[0]) / 2
            if kind == 'p':
                return math.hypot(g[0] - px, g[1] - py) - rad
            x1, y1, x2, y2 = g
            vx, vy = x2 - x1, y2 - y1
            L = vx * vx + vy * vy
            t = 0 if L == 0 else max(0, min(1, ((px - x1) * vx + (py - y1) * vy) / L))
            return math.hypot(px - x1 - t * vx, py - y1 - t * vy) - rad
        if kind == 'p':
            return math.hypot(max(r[0] - g[0], 0, g[0] - r[2]), max(r[1] - g[1], 0, g[1] - r[3]))
        return seg_rect(g[0], g[1], g[2], g[3], r)
    def side_of(layer):
        return 'top' if layer == 'Top Layer' else 'bottom' if layer == 'Bottom Layer' else None
    stats = Counter()
    vias, tracks, drops = [], [], []
    for v in P['vias']:
        net = pmap.get(v['net'], 'DROP') if v['net'] in pmap else None
        if not net:
            stats['via: net not on a Feather U1 ball'] += 1
            continue
        x, y = rel(*xf(v['x'], v['y']))
        if not (lo_x <= x <= hi_x and lo_y <= y <= hi_y):
            stats['via: outside window'] += 1
            continue
        span = STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]
        sides = {s for s in (side_of(span[0]), side_of(span[-1])) if s}
        hit = None
        for ref, pn, pnet, r, psides in pads:
            if pnet != net and sides & psides:
                if gap(ref, r, 'p', (x, y)) < v['size'] / 2 + CLEAR - 1e-6:
                    hit = '%s-%s' % (ref, pn)
                    break
        if hit:
            drops.append('via %s at %.3f,%.3f %s-%s hits %s' % (net, x, y, span[0], span[-1], hit))
            continue
        vias.append({'net': net, 'x': round(x, 4), 'y': round(y, 4), 'size': v['size'], 'hole': v['drill'],
                     'from': span[0], 'to': span[-1]})
        stats['via passed the pad check'] += 1
    for t in P['tracks']:
        if t['net'] not in pmap:
            stats['track: net not on a U1 ball'] += 1
            continue
        net = pmap[t['net']]
        if not net:
            stats['track: ball no longer connected'] += 1
            continue
        a = rel(*xf(t['x1'], t['y1']))
        b2 = rel(*xf(t['x2'], t['y2']))
        c = clip(a[0], a[1], b2[0], b2[1], lo_x, lo_y, hi_x, hi_y)
        if not c or math.hypot(c[2] - c[0], c[3] - c[1]) < 1e-4 and (a != b2):
            stats['track: outside window'] += 1
            continue
        if c != (a[0], a[1], b2[0], b2[1]):
            stats['track clipped at the window'] += 1
        s = side_of(t['layer'])
        hit = None
        if s:
            for ref, pn, pnet, r, psides in pads:
                if pnet != net and s in psides and gap(ref, r, 's', c) < t['w'] / 2 + CLEAR - 1e-6:
                    hit = '%s-%s' % (ref, pn)
                    break
        if hit:
            drops.append('track %s %s %.3f,%.3f-%.3f,%.3f hits %s' % (net, t['layer'], c[0], c[1], c[2], c[3], hit))
            continue
        tracks.append({'net': net, 'layer': t['layer'], 'w': t['w'],
                       'x1': round(c[0], 4), 'y1': round(c[1], 4), 'x2': round(c[2], 4), 'y2': round(c[3], 4)})
        stats['track passed the pad check'] += 1
    # prune: keep only copper joined (through its own net's copper) to a Feather pad of that net. Two pieces join
    # when a track end or via centre lies within 0.01 mm of the other piece's end/centre, or on its track; a piece
    # joins a pad when its end/centre lies on the pad's copper on a layer both occupy.
    def on_seg(px, py, t):
        vx, vy = t['x2'] - t['x1'], t['y2'] - t['y1']
        L = vx * vx + vy * vy
        u = 0 if L == 0 else max(0, min(1, ((px - t['x1']) * vx + (py - t['y1']) * vy) / L))
        return math.hypot(px - t['x1'] - u * vx, py - t['y1'] - u * vy) < 0.01
    def layers_of(o):
        if 'layer' in o:
            return {o['layer']}
        return set(STACK[STACK.index(o['from']):STACK.index(o['to']) + 1])
    def pts(o):
        return [(o['x1'], o['y1']), (o['x2'], o['y2'])] if 'layer' in o else [(o['x'], o['y'])]
    items = vias + tracks
    bynet = defaultdict(list)
    for i, o in enumerate(items):
        bynet[o['net']].append(i)
    live = set()
    for net, idx in bynet.items():
        seeds = []
        for i in idx:
            o = items[i]
            ls = layers_of(o)
            for ref, pn, pnet, r, psides in pads:
                if pnet != net:
                    continue
                pl = ({'Top Layer'} if 'top' in psides else set()) | ({'Bottom Layer'} if 'bottom' in psides else set())
                if 'top' in psides and 'bottom' in psides:
                    pl = set(STACK)
                if ls & pl and any(gap(ref, r, 'p', q) <= 0.005 for q in pts(o)):
                    seeds.append(i)
                    break
        seen = set(seeds)
        stack = list(seeds)
        while stack:
            i = stack.pop()
            a = items[i]
            for j in idx:
                if j in seen:
                    continue
                b = items[j]
                if not (layers_of(a) & layers_of(b)):
                    continue
                hit = any(math.hypot(p[0] - q[0], p[1] - q[1]) < 0.01 for p in pts(a) for q in pts(b))
                if not hit and 'layer' in b:
                    hit = any(on_seg(p[0], p[1], b) for p in pts(a))
                if not hit and 'layer' in a:
                    hit = any(on_seg(q[0], q[1], a) for q in pts(b))
                if hit:
                    seen.add(j)
                    stack.append(j)
        live |= seen
    floating = len(items) - len(live)
    vias = [o for i, o in enumerate(items) if i in live and 'layer' not in o]
    tracks = [o for i, o in enumerate(items) if i in live and 'layer' in o]
    stats['floating copper pruned'] = floating
    nets = Counter(v['net'] for v in vias) + Counter(t['net'] for t in tracks)
    fnets = {n for _, _, n in fball.values() if n}
    stats['via kept'] = len(vias)
    stats['track kept'] = len(tracks)
    out = {'R': R, 'shift': [round(sx, 4), round(sy, 4)], 'u1_centre': [round(cx, 4), round(cy, 4)],
           'stats': dict(stats), 'drops': drops, 'vias': vias, 'tracks': tracks}
    os.makedirs(OUTD, exist_ok=True)
    json.dump(out, open(os.path.join(OUTD, 'stage1_u1.json'), 'w'), indent=0)
    print('window +-%.2f mm about U1 (%.2f, %.2f); U1 rot %g; shift %.3f, %.3f' % (R, cx, cy, D['U1']['rot'], sx, sy))
    for k, v in sorted(stats.items()):
        print('  %-40s %d' % (k, v))
    print('  dropped for Feather pad conflicts         %d' % len(drops))
    for d in drops[:40]:
        print('    ' + d)
    print('U1 nets with copper: %d of %d' % (len(nets), len(fnets)))
    print('  without: ' + ' '.join(sorted(fnets - set(nets))))


if __name__ == '__main__':
    if '--dump' in sys.argv:
        dump()
    else:
        plan(float(sys.argv[sys.argv.index('--r') + 1]) if '--r' in sys.argv else 5.5)
