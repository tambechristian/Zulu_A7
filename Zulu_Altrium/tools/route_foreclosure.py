# -*- coding: utf-8 -*-
"""What does a routing plan take away from the nets that are not routed yet?

    python tools/route_foreclosure.py                    the board as saved
    python tools/route_foreclosure.py <plan.json> ...    the board plus plan(s)

For every U1 escape that still needs a via -- a ring-1 signal stub's free end,
or a ring-0 signal ball that nothing has been placed on -- count the legal via
positions it can reach on Top, and exit 1 if any escape that has a slot on the
board alone has none once the plan(s) are added.

A slot is a via centre on a 0.05 mm grid within REACH of the escape point, outside
U1's land field (inside it every free position is an interstice, which the design
forbids), whose 0.35 mm land keeps
    >= 0.44 mm centre-to-centre from every via,
    >= 0.09 mm from every foreign Top, Bottom and through-hole pad,
    >= 0.09 mm from every foreign track on every signal layer -- 0.10 from an
       SDRAM track on L3/L4 and 0.20 from an SDRAM-CLK track on L3/L4,
and which the escape can reach with a 3 mil Top track of ANY shape: Top free space
is rasterised at 0.025 mm around the escape (foreign Top pads, Top tracks and via
lands grown by 0.09 mm + half the track width; the escape's own net carved out)
and flood-filled from the escape point; a slot counts only if its cell is in the
same connected region.

PADS (2026-09-15).  The same question is asked of every Top/Bottom SMD pad of a net
the plans do not own that lies within PAD_NEAR of the plans' copper: flood-fill its
own layer from anywhere inside the pad; it keeps a way out if the region reaches a
legal via slot (whose land also clears every pad, so no via-in-pad) or any other
copper of its own net on that layer.  A pad that had a way out and loses it is
foreclosed.  (A U1-only escape audit once passed a plan that sealed four XADC filter
pads.)

This is a necessary condition for routability, not a sufficient one: an escape
with slots can still be boxed further out. An escape with NONE cannot be routed
without moving copper that is already there.
"""
import io
import json
import math
import os
import sys

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
FI = os.path.join(HERE, 'fanout_inputs.json')
FP = os.path.join(HERE, 'fanout_plan.json')
RI = os.path.join(HERE, 'route_inputs.json')
REACH = 2.5          # via slot within this distance of the escape point
STEP = 0.05          # slot grid
CELL = 0.025         # Top free-space raster
WIN = 3.2            # raster half-window
PAD_NEAR = 1.5       # pads within this of a plan primitive are audited
PAD_WIN = 2.4        # raster half-window for a pad
VIA_R = 0.175
PITCH = 0.44
C = 0.09
TOP_W = 0.0762
POWER = {'GND', 'GNDADC', 'VCC3V3', 'VCC1V0', 'VCC1V8', 'VCCADC'}
SIGNAL_LAYERS = ('Top', 'L3-SIG', 'L4-SIG', 'Bottom')


def seg_pts_dist(x1, y1, x2, y2, px, py):
    """distance from each point (px, py arrays) to one segment"""
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return np.hypot(px - x1, py - y1)
    t = np.clip(((px - x1) * dx + (py - y1) * dy) / L2, 0.0, 1.0)
    return np.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def rect_pts_dist(cx, cy, sx, sy, px, py):
    dx = np.maximum(np.abs(px - cx) - sx / 2, 0.0)
    dy = np.maximum(np.abs(py - cy) - sy / 2, 0.0)
    return np.hypot(dx, dy)


def seg_seg_dist(a, b):
    def pt(px, py, x1, y1, x2, y2):
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        if L2 == 0:
            return math.hypot(px - x1, py - y1)
        t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L2))
        return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))

    def cross(p1, p2, p3, p4):
        d = (p2[0] - p1[0]) * (p4[1] - p3[1]) - (p2[1] - p1[1]) * (p4[0] - p3[0])
        if abs(d) < 1e-12:
            return False
        t = ((p3[0] - p1[0]) * (p4[1] - p3[1]) - (p3[1] - p1[1]) * (p4[0] - p3[0])) / d
        u = ((p3[0] - p1[0]) * (p2[1] - p1[1]) - (p3[1] - p1[1]) * (p2[0] - p1[0])) / d
        return 0 <= t <= 1 and 0 <= u <= 1
    if cross((a[0], a[1]), (a[2], a[3]), (b[0], b[1]), (b[2], b[3])):
        return 0.0
    return min(pt(a[0], a[1], *b), pt(a[2], a[3], *b), pt(b[0], b[1], *a), pt(b[2], b[3], *a))


def seg_rect_dist(seg, cx, cy, sx, sy, n=16):
    x1, y1, x2, y2 = seg
    ts = np.linspace(0, 1, n + 1)
    return float(rect_pts_dist(cx, cy, sx, sy, x1 + (x2 - x1) * ts, y1 + (y2 - y1) * ts).min())


def escapes():
    fi = json.load(io.open(FI, encoding='utf-8'))
    fp = json.load(io.open(FP, encoding='utf-8'))
    sdram = set(json.load(io.open(RI, encoding='utf-8'))['nets'])     # every net the routing plans own
    act = {b['name']: b['action'] for b in fp['balls']}
    lf = fi['grid']['u1_extent']
    out = []
    for b in fi['balls']:
        if not b['net'] or b['net'] in POWER or act.get(b['name']) not in ('gap', 'direct'):
            continue
        if act[b['name']] == 'direct':
            out.append(dict(ball=b['name'], net=b['net'], kind='ball', x=b['x'], y=b['y'], sdram=b['net'] in sdram))
            continue
        # the stub end outside the land field
        best = None
        for t in fp['tracks']:
            if t['net'] != b['net'] or t['layer'] != 'Top':
                continue
            for (x, y) in ((t['x1'], t['y1']), (t['x2'], t['y2'])):
                if not (lf['x0'] <= x <= lf['x1'] and lf['y0'] <= y <= lf['y1']):
                    best = (x, y)
        if best:
            out.append(dict(ball=b['name'], net=b['net'], kind='stub-end', x=best[0], y=best[1], sdram=b['net'] in sdram))
    return out, lf


def world(plans):
    ri = json.load(io.open(RI, encoding='utf-8'))
    sdram = {n for n, v in ri['nets'].items() if v.get('cls', 'SDRAM').startswith('SDRAM')}
    vias = [dict(x=v['x'], y=v['y'], r=v['size'] / 2, net=v['net']) for v in ri['vias']]
    tracks = [dict(t) for t in ri['tracks']]
    for p in plans:
        rem = p.get('remove') or {}
        rv = {(v['net'], round(v['x'], 4), round(v['y'], 4)) for v in rem.get('vias', [])}
        rt = {(t['net'], t['layer']) + tuple(sorted(((round(t['x1'], 4), round(t['y1'], 4)), (round(t['x2'], 4), round(t['y2'], 4))))) for t in rem.get('tracks', [])}
        vias = [v for v in vias if (v['net'], round(v['x'], 4), round(v['y'], 4)) not in rv]
        tracks = [t for t in tracks if (t['net'], t['layer']) + tuple(sorted(((round(t['x1'], 4), round(t['y1'], 4)), (round(t['x2'], 4), round(t['y2'], 4))))) not in rt]
        vias += [dict(x=v['x'], y=v['y'], r=VIA_R, net=v['net']) for v in p.get('vias', [])]
        tracks += [dict(t) for t in p.get('tracks', [])]
    pads_top = [dict(q, layer='Top') for q in ri['top_pads']]
    pads_bot = [dict(q, layer='Bottom') for q in ri['bottom_pads']]
    th = ri['th_pads']

    def trk_clr(t):
        if t['layer'] in ('L3-SIG', 'L4-SIG') and t['net'] in sdram:
            return 0.20 if t['net'] == 'SDRAM-CLK' else 0.10
        return C
    for t in tracks:
        t['clr'] = trk_clr(t)
    return dict(vias=vias, tracks=tracks, top=pads_top, bot=pads_bot, th=th)


def near(objs, x, y, r, key=('x', 'y')):
    out = []
    for o in objs:
        if 'x1' in o:
            if min(o['x1'], o['x2']) - r <= x <= max(o['x1'], o['x2']) + r and min(o['y1'], o['y2']) - r <= y <= max(o['y1'], o['y2']) + r:
                out.append(o)
        elif abs(o['x'] - x) <= r + 1.0 and abs(o['y'] - y) <= r + 1.0:
            out.append(o)
    return out


def slots(e, W, lf, limit=None):
    net = e['net']
    R = REACH + 1.2
    vias = [v for v in near(W['vias'], e['x'], e['y'], R) if True]
    tracks = [t for t in near(W['tracks'], e['x'], e['y'], R) if t['net'] != net]
    top = [p for p in near(W['top'], e['x'], e['y'], R) if p['net'] != net]
    bot = [p for p in near(W['bot'], e['x'], e['y'], R) if p['net'] != net]
    th = [p for p in near(W['th'], e['x'], e['y'], R) if p['net'] != net]

    g = np.arange(-REACH, REACH + 1e-9, STEP)
    gx, gy = np.meshgrid(e['x'] + g, e['y'] + g)
    px, py = gx.ravel(), gy.ravel()
    ok = np.hypot(px - e['x'], py - e['y']) <= REACH
    ok &= ~((px >= lf['x0']) & (px <= lf['x1']) & (py >= lf['y0']) & (py <= lf['y1']))
    for v in vias:
        ok &= np.hypot(px - v['x'], py - v['y']) >= PITCH - 1e-9
    for p in top + bot + th:
        ok &= rect_pts_dist(p['x'], p['y'], p['sx'], p['sy'], px, py) - VIA_R >= C - 1e-9
    for t in tracks:
        ok &= seg_pts_dist(t['x1'], t['y1'], t['x2'], t['y2'], px, py) - t['width'] / 2 - VIA_R >= t['clr'] - 1e-9
    cand = np.flatnonzero(ok)
    if cand.size == 0:
        return 0, None
    # Top free space for a 3 mil track centreline, own net carved out
    gx1 = np.arange(e['x'] - WIN, e['x'] + WIN + 1e-9, CELL)
    gy1 = np.arange(e['y'] - WIN, e['y'] + WIN + 1e-9, CELL)
    RX, RY = np.meshgrid(gx1, gy1)
    free = np.ones(RX.shape, dtype=bool)
    grow = C + TOP_W / 2
    for p in top:
        free &= rect_pts_dist(p['x'], p['y'], p['sx'], p['sy'], RX, RY) >= grow - 1e-9
    for t in tracks:
        if t['layer'] == 'Top':
            free &= seg_pts_dist(t['x1'], t['y1'], t['x2'], t['y2'], RX, RY) - t['width'] / 2 >= grow - 1e-9
    for v in vias:
        if v['net'] != net:
            free &= np.hypot(RX - v['x'], RY - v['y']) - v['r'] >= grow - 1e-9
    ix0 = int(round((e['x'] - gx1[0]) / CELL))
    iy0 = int(round((e['y'] - gy1[0]) / CELL))
    free[max(iy0 - 1, 0):iy0 + 2, max(ix0 - 1, 0):ix0 + 2] = True      # the escape point itself
    lab, _ = ndimage.label(free, structure=np.ones((3, 3), dtype=int))
    region = lab[iy0, ix0]
    order = cand[np.argsort(np.hypot(px[cand] - e['x'], py[cand] - e['y']))]
    n = 0
    first = None
    for k in order:
        vx, vy = float(px[k]), float(py[k])
        cx = int(round((vx - gx1[0]) / CELL))
        cy = int(round((vy - gy1[0]) / CELL))
        if not (0 <= cx < RX.shape[1] and 0 <= cy < RX.shape[0]):
            continue
        if lab[cy, cx] == region and region != 0:
            n += 1
            if first is None:
                first = (round(vx, 3), round(vy, 3))
            if limit and n >= limit:
                break
    return n, first


def _pad_ok_window(pad, W, lf, owned, PAD_WIN):
    """(ok, slots, reason, touches_edge) for one SMD pad, one window size"""
    L = pad['layer']
    net = pad['net']
    R = PAD_WIN + 1.0
    same_layer_pads = W['top'] if L == 'Top' else W['bot']
    pads_L = [p for p in near(same_layer_pads, pad['x'], pad['y'], R)]
    th = [p for p in near(W['th'], pad['x'], pad['y'], R)]
    vias = near(W['vias'], pad['x'], pad['y'], R)
    trk_all = [t for t in near(W['tracks'], pad['x'], pad['y'], R)]
    trk_L = [t for t in trk_all if t['layer'] == L]
    pads_other = [p for p in near(W['bot'] if L == 'Top' else W['top'], pad['x'], pad['y'], R)]

    gx1 = np.arange(pad['x'] - PAD_WIN, pad['x'] + PAD_WIN + 1e-9, CELL)
    gy1 = np.arange(pad['y'] - PAD_WIN, pad['y'] + PAD_WIN + 1e-9, CELL)
    RX, RY = np.meshgrid(gx1, gy1)
    free = np.ones(RX.shape, dtype=bool)
    grow = C + TOP_W / 2
    for p in pads_L + th:
        if p['net'] == net and net is not None:
            continue
        free &= rect_pts_dist(p['x'], p['y'], p['sx'], p['sy'], RX, RY) >= grow - 1e-9
    for t in trk_L:
        if t['net'] == net:
            continue
        free &= seg_pts_dist(t['x1'], t['y1'], t['x2'], t['y2'], RX, RY) - t['width'] / 2 >= grow - 1e-9
    for v in vias:
        if v['net'] == net:
            continue
        free &= np.hypot(RX - v['x'], RY - v['y']) - v['r'] >= grow - 1e-9
    inside = (np.abs(RX - pad['x']) <= pad['sx'] / 2) & (np.abs(RY - pad['y']) <= pad['sy'] / 2)
    free |= inside
    lab, _ = ndimage.label(free, structure=np.ones((3, 3), dtype=int))
    regions = set(np.unique(lab[inside])) - {0}
    if not regions:
        return False, 0, 'no free space at the pad', False
    reg = np.isin(lab, list(regions))
    edge = bool(reg[0, :].any() or reg[-1, :].any() or reg[:, 0].any() or reg[:, -1].any())

    # other copper of its own net on this layer, reached by the region
    if net is not None:
        for p in pads_L:
            if p['net'] == net and not (p['x'] == pad['x'] and p['y'] == pad['y']):
                m = (np.abs(RX - p['x']) <= p['sx'] / 2) & (np.abs(RY - p['y']) <= p['sy'] / 2)
                if (m & reg).any():
                    return True, 25, 'reaches %s-%s' % (p['ref'], p['pad']), edge
        for v in vias:
            if v['net'] == net and ((np.hypot(RX - v['x'], RY - v['y']) <= v['r']) & reg).any():
                return True, 25, 'reaches a %s via' % net, edge
        for t in trk_L:
            if t['net'] == net and ((seg_pts_dist(t['x1'], t['y1'], t['x2'], t['y2'], RX, RY) <= t['width'] / 2) & reg).any():
                return True, 25, 'reaches %s copper' % net, edge

    # a legal via slot inside the region
    g = np.arange(-PAD_WIN, PAD_WIN + 1e-9, STEP)
    gx, gy = np.meshgrid(pad['x'] + g, pad['y'] + g)
    px, py = gx.ravel(), gy.ravel()
    ok = ~((px >= lf['x0']) & (px <= lf['x1']) & (py >= lf['y0']) & (py <= lf['y1']))
    for v in vias:
        ok &= np.hypot(px - v['x'], py - v['y']) >= PITCH - 1e-9
    for p in pads_L + pads_other + th:           # every pad, own net included: no via-in-pad
        ok &= rect_pts_dist(p['x'], p['y'], p['sx'], p['sy'], px, py) - VIA_R >= C - 1e-9
    for t in trk_all:
        if t['net'] == net:
            continue
        ok &= seg_pts_dist(t['x1'], t['y1'], t['x2'], t['y2'], px, py) - t['width'] / 2 - VIA_R >= t['clr'] - 1e-9
    cand = np.flatnonzero(ok)
    n = 0
    for k in cand:
        cx = int(round((px[k] - gx1[0]) / CELL))
        cy = int(round((py[k] - gy1[0]) / CELL))
        if 0 <= cx < RX.shape[1] and 0 <= cy < RX.shape[0] and reg[cy, cx]:
            n += 1
            if n >= 25:
                break
    return n > 0, n, ('%d via slot(s)' % n) if n else 'sealed: no via slot and no own-net copper reachable', edge


def pad_ok(pad, W, lf, owned):
    """(ok, slots, reason).  The window grows while the pad's free region runs into its edge
    without an exit: a fixed 2.4 mm window once called R16-2 sealed when its pocket
    simply continued past the window to 25 via slots."""
    for win in (2.4, 4.0, 6.0, 8.0):
        ok, n, why, edge = _pad_ok_window(pad, W, lf, owned, win)
        if ok or not edge:
            return ok, n, why if win == 2.4 else '%s (window +-%.1f mm)' % (why, win)
    return ok, n, why + ' (still open at +-8 mm: treat as unproven)'


def pad_audit(plans, W0, W1, lf):
    # 2026-09-15: the nets the plans TOUCH are theirs to finish (route_emit --require-complete);
    # every other net's pads -- including power nets a later stage will route -- must keep a
    # way out.  (It used to skip every net in route_inputs.json.)
    owned = set()
    for p in plans:
        owned |= {v['net'] for v in p.get('vias', [])} | {t['net'] for t in p.get('tracks', [])}
    prims = []
    for p in plans:
        prims += [(v['x'], v['y'], v['x'], v['y']) for v in p.get('vias', [])]
        prims += [(t['x1'], t['y1'], t['x2'], t['y2']) for t in p.get('tracks', [])]
    if not prims:
        return [], 0
    P = np.array(prims)
    cand = []
    for pad in W1['top'] + W1['bot']:
        if pad['ref'] == 'U1' or pad['net'] in owned:
            continue
        if pad['net'] is None:
            continue
        d = np.min(np.maximum(0, np.maximum(np.minimum(P[:, 0], P[:, 2]) - pad['x'], pad['x'] - np.maximum(P[:, 0], P[:, 2])))
                   + np.maximum(0, np.maximum(np.minimum(P[:, 1], P[:, 3]) - pad['y'], pad['y'] - np.maximum(P[:, 1], P[:, 3]))))
        if d <= PAD_NEAR + max(pad['sx'], pad['sy']) / 2:
            cand.append(pad)
    lost = []
    for pad in cand:
        ok0, n0, why0 = pad_ok(pad, W0, lf, owned)
        if not ok0:
            continue
        ok1, n1, why1 = pad_ok(pad, W1, lf, owned)
        if not ok1:
            lost.append((pad, why0, why1))
    return lost, len(cand)


def main():
    global RI
    argv = list(sys.argv[1:])
    if '--inputs' in argv:              # e.g. tools/block_place.py --write-inputs: the board with parts moved
        k = argv.index('--inputs')
        RI = argv[k + 1]
        del argv[k:k + 2]
    plans = [json.load(io.open(p, encoding='utf-8')) for p in argv if p.endswith('.json')]
    esc, lf = escapes()
    W0 = world([])
    W1 = world(plans) if plans else None
    lost = []
    print('%d unrouted U1 signal escapes (SDRAM ones marked *)' % len(esc))
    print('%-5s %-14s %-8s %8s %s' % ('ball', 'net', 'kind', 'board', 'with plan' if plans else ''))
    for e in sorted(esc, key=lambda e: (e['sdram'], e['net'])):
        n0, f0 = slots(e, W0, lf, limit=25)
        line = '%-5s %-14s %-8s %8s' % (e['ball'], e['net'] + ('*' if e['sdram'] else ''), e['kind'], ('%d' % n0) + ('+' if n0 >= 25 else ''))
        if W1 is not None and not e['sdram']:
            n1, f1 = slots(e, W1, lf, limit=25)
            line += '   %s%s' % (('%d' % n1) + ('+' if n1 >= 25 else ''), '   <-- FORECLOSED BY THE PLAN' if n0 > 0 and n1 == 0 else '')
            if n0 > 0 and n1 == 0:
                lost.append(e['net'])
        if n0 == 0:
            line += '   <-- already no slot on the board'
        print(line)
    if plans:
        print('\nforeclosed by the plan(s): %s' % (' '.join(lost) if lost else 'none'))
        plost, pn = pad_audit(plans, W0, W1, lf)
        print('\npads of unowned nets within %.1f mm of the plan copper: %d audited' % (PAD_NEAR, pn))
        for pad, w0, w1 in plost:
            print('   %s-%s %-14s %-6s  board: %s   with plan: %s   <-- PAD FORECLOSED' % (pad['ref'], pad['pad'], pad['net'], pad['layer'], w0, w1))
        print('pads foreclosed by the plan(s): %s' % (' '.join('%s-%s' % (p['ref'], p['pad']) for p, _, _ in plost) if plost else 'none'))
        return 1 if (lost or plost) else 0
    return 0


if __name__ == '__main__':
    sys.exit(main())
