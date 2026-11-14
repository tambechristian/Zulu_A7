"""Bottom-side series-R plan for the 16 SDRAM DQ nets (approach 'bottom': R on Bottom, next to U3's pin).

PLANNING ONLY. Reads board_extract.json (written by extract.py from the saved PcbDoc, md5 in its 'source'),
never the PcbDoc itself, and writes only design_bottom.json / design_bottom.png in this folder.

Topology per DQ n (the R splits the old net Dn in two):
    U3 pad (now net SDRAM-Dn) -> 'neck' track on Bottom, outward (away from U3's body)
    -> R pad A (SDRAM-Dn) | R | R pad B (Dn)
    -> 'return' track on Bottom, back between U3's pads (through a pad-row gap) -> the EXISTING first through via
    (which stays where it is, so nothing on L2..L5 or Top changes) -> existing Dn route to U1.
The old Bottom stub pad->via is removed.

The plan is found by a small search: candidate R positions on a 0.025 mm grid are filtered by the component-
clearance, copper-clearance and mask-sliver rules, then the neck and return are routed by a 45-degree A* on a
0.025 mm raster whose blocked cells are computed from EXACT distances to every foreign-net Bottom object.
Everything placed is then re-checked with exact geometry (geom.py) against the whole Bottom layer.

Rework items (non-D copper / parts that have to move) are listed in REWORK and applied before the search; each is
re-checked with the same exact checker as the new D copper.

    python design_bottom.py --variant CH18     # the reported plan: search + verify + design_bottom.json/.png
    python design_bottom.py --variant CH18,VCC9 --order 0,1,4,3,5,2,6,7 --tag w2   # what-ifs -> $DB_SCRATCH
    python design_bottom.py --variant CH18 --compclr 0.10 --tag relaxed            # ComponentClearance what-if

RESULT (2026-11-13): 4 of 16 (D0, D1, D3, D5) with one Bottom-only reshape of the CHAN18 jumper; 3 of 16 with D copper
only; 6 of 16 if ComponentClearance were relaxed to 0.10 mm; the north row (D8-D15) places none in any variant.
"""
import json, math, os, sys, heapq, time, itertools
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import geom as G

EXTRACT = os.path.join(HERE, 'board_extract.json')
OUT_JSON = os.path.join(HERE, 'design_bottom.json')
OUT_PNG = os.path.join(HERE, 'design_bottom.png')

# ---------------- rules (values from board_extract.json 'rules_summary', re-read below) ----------------
CLR = 0.09            # 'Clearance' All/All, 3.5 mil -- binds on Bottom
COMP_CLR = 0.254      # 'ComponentClearance' 10 mil
MASK_EXP = 0.05       # 'SolderMaskExpansion' default; U1 0.0, X3 0.04
MASK_SLIVER = 0.10    # 'MinimumSolderMaskSliver' 3.937 mil
W_BOT = (0.10, 0.125, 0.15)   # Width_SDRAM on Bottom (min, pref, max)
GRID = 0.025
EPS = 0.004           # raster safety margin (path between two legal cell centres)
# R0201 footprint (zulu_a7.PcbLib R0201 / board copies R12..R15): pads 0.30 x 0.30 at +-0.30, Mech3 body 0.402 x 0.396
R_PAD = 0.30
R_PITCH = 0.60
R_MECH3 = (0.2009, 0.1979)    # half sizes along / across the long axis (R15 Mech3 = [43.8489,3.752,44.2507,4.1478])

DQ_PIN = {0: 2, 1: 4, 2: 5, 3: 7, 4: 8, 5: 10, 6: 11, 7: 13, 8: 42, 9: 44, 10: 45, 11: 47, 12: 48, 13: 50, 14: 51, 15: 53}
FIRST_DESIG = 119     # R119..R134 (schematic_plan.md: highest existing R is R118)

EX = json.load(open(EXTRACT))


def rd(x, n=4):
    return round(float(x), n)


# ---------------- Bottom copper model ----------------
def pad_obj(p):
    w, h = p['w'], p['h']
    if p['layer'] == 'Multi' and p.get('size_bot'):
        sx, sy = p['size_bot']
        if abs((p.get('rot') or 0) % 180 - 90) < 1:
            sx, sy = sy, sx
        w, h = sx, sy
    if p['shape'] == 'round' and abs(w - h) < 1e-6:
        o = dict(kind='circ', g=(p['x'], p['y'], w / 2))
    else:  # rect / obround / rounded rect -> its bounding rect (conservative)
        o = dict(kind='rect', g=(p['x'] - w / 2, p['y'] - h / 2, p['x'] + w / 2, p['y'] + h / 2))
    o.update(net=p['net'], src='pad %s-%s' % (p['ref'], p['pad']), ref=p['ref'], pad=p['pad'], is_pad=True,
             mask=0.0 if p['ref'] == 'U1' else (0.04 if p['ref'] == 'X3' else MASK_EXP))
    return o


def load_bottom():
    objs = []
    for p in EX['pads']:
        if p['layer'] in ('Bottom', 'Multi'):
            objs.append(pad_obj(p))
    for i, t in enumerate(EX['tracks']):
        if t['layer'] == 'Bottom':
            objs.append(dict(kind='seg', g=(t['x1'], t['y1'], t['x2'], t['y2'], t['w'] / 2), net=t['net'],
                             src='track#%d %s' % (i, t['net']), tid=i))
    for i, v in enumerate(EX['vias']):
        if 'Bottom' in v['span']:
            objs.append(dict(kind='circ', g=(v['x'], v['y'], v['size'] / 2), net=v['net'],
                             src='via#%d %s %s' % (i, v['net'], v['kind']), vid=i, via=v))
    return objs


def comp_proxies():
    """Body proxy per Bottom component = bbox of its pads + Mech3/Mech4 drawings/regions (what ComponentClearance can
    see: the board has no 3D bodies). Mech7/Mech8 courtyards are NOT used: C7's Mech7 is 0.14 mm from C41's Mech3 and
    the board passes DRC, so Altium does not check them. U3 also gets the datasheet max body (inside its pad box)."""
    out = {}
    for c in EX['components']:
        if c['side'] != 'Bottom':
            continue
        o = EX['component_outlines'][c['ref']]
        boxes = [v for k, v in o.items() if k.split('(')[0] in ('pads', 'Mech3', 'Mech4')]
        if c['ref'] == 'U3':
            b = EX['u3']['body']['max']
            boxes.append([b['x0'], b['y0'], b['x1'], b['y1']])
        if not boxes:
            continue
        out[c['ref']] = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
    return out


def rect_gap(a, b):
    return math.hypot(max(0.0, a[0] - b[2], b[0] - a[2]), max(0.0, a[1] - b[3], b[1] - a[3]))


# ---------------- R geometry ----------------
def r_geom(cx, cy, rot):
    """rot 0: pad A west, B east; 90: A south, B north; 180: A east; 270: A north."""
    ang = math.radians(rot)
    ux, uy = round(math.cos(ang), 9), round(math.sin(ang), 9)
    ax, ay = cx - ux * R_PITCH / 2, cy - uy * R_PITCH / 2
    bx, by = cx + ux * R_PITCH / 2, cy + uy * R_PITCH / 2
    h = R_PAD / 2
    pa = (ax - h, ay - h, ax + h, ay + h)
    pb = (bx - h, by - h, bx + h, by + h)
    if rot % 180 == 0:
        prox = (cx - R_PITCH / 2 - h, cy - R_MECH3[1], cx + R_PITCH / 2 + h, cy + R_MECH3[1])
    else:
        prox = (cx - R_MECH3[1], cy - R_PITCH / 2 - h, cx + R_MECH3[1], cy + R_PITCH / 2 + h)
    return (ax, ay), (bx, by), pa, pb, prox


# ---------------- router ----------------
DIRS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]


class Board:
    def __init__(self, objs, proxies):
        self.objs = list(objs)
        self.proxies = dict(proxies)

    def foreign(self, net, box):
        x0, y0, x1, y1 = box
        for o in self.objs:
            b = G.bbox(o)
            if b[2] < x0 or b[0] > x1 or b[3] < y0 or b[1] > y1:
                continue
            if o['net'] is not None and o['net'] == net:
                continue
            yield o

    REGION = (25.5, 1.5, 41.5, 22.0)

    def _raster(self, net, w, objs, box, blk=None):
        x0, y0 = box[0], box[1]
        if blk is None:
            nx = int(round((box[2] - box[0]) / GRID)) + 1
            ny = int(round((box[3] - box[1]) / GRID)) + 1
            blk = np.zeros((ny, nx), bool)
        ny, nx = blk.shape
        need = CLR + w / 2 + EPS
        for o in objs:
            if o['net'] is not None and o['net'] == net:
                continue
            b = G.bbox(o)
            i0 = max(0, int((b[0] - need - x0) / GRID) - 1); i1 = min(nx, int((b[2] + need - x0) / GRID) + 2)
            j0 = max(0, int((b[1] - need - y0) / GRID) - 1); j1 = min(ny, int((b[3] + need - y0) / GRID) + 2)
            if i0 >= i1 or j0 >= j1:
                continue
            X = x0 + GRID * np.arange(i0, i1)[None, :]
            Y = y0 + GRID * np.arange(j0, j1)[:, None]
            X, Y = np.broadcast_arrays(X, Y)
            blk[j0:j1, i0:i1] |= G.vdist(X, Y, o) < need
        return blk

    def blocked(self, net, w, box):
        """raster over the fixed REGION: static objects cached per (net, w), plus every object flagged 'dyn'."""
        key = (net, w)
        if not hasattr(self, '_cache'):
            self._cache = {}
        if key not in self._cache:
            self._cache[key] = self._raster(net, w, [o for o in self.objs if not o.get('dyn')], self.REGION)
        blk = self._cache[key].copy()
        self._raster(net, w, [o for o in self.objs if o.get('dyn')], self.REGION, blk)
        R = self.REGION
        i0 = max(0, int((box[0] - R[0]) / GRID)); i1 = min(blk.shape[1], int((box[2] - R[0]) / GRID) + 1)
        j0 = max(0, int((box[1] - R[1]) / GRID)); j1 = min(blk.shape[0], int((box[3] - R[1]) / GRID) + 1)
        return blk[j0:j1, i0:i1], R[0] + i0 * GRID, R[1] + j0 * GRID

    def route(self, net, w, start, goal, box, max_len=12.0, turn_pen=0.6, forbid=None):
        blk, x0, y0 = self.blocked(net, w, box)
        if forbid is not None:
            blk |= forbid(x0, y0, blk.shape)
        ny, nx = blk.shape
        si, sj = int(round((start[0] - x0) / GRID)), int(round((start[1] - y0) / GRID))
        gi, gj = int(round((goal[0] - x0) / GRID)), int(round((goal[1] - y0) / GRID))
        for (i, j) in ((si, sj), (gi, gj)):
            if not (0 <= i < nx and 0 <= j < ny):
                return None
        # endpoints sit inside own-net copper (pad / via); let the search leave them even if the raster grazes
        blk = blk.copy()
        blk[sj, si] = False
        blk[gj, gi] = False
        INF = 1e18
        best = {}
        h0 = math.hypot(gi - si, gj - sj)
        pq = [(h0, 0.0, si, sj, -1, None)]
        came = {}
        while pq:
            f, g, i, j, d, par = heapq.heappop(pq)
            key = (i, j, d)
            if key in came:
                continue
            came[key] = par
            if (i, j) == (gi, gj):
                path = []
                k = key
                while k is not None:
                    path.append((k[0], k[1]))
                    k = came[k]
                path.reverse()
                pts = [(x0 + GRID * a, y0 + GRID * b) for a, b in path]
                pts[0] = start
                pts[-1] = goal
                return simplify(pts)
            if g * GRID > max_len:
                continue
            for nd, (di, dj) in enumerate(DIRS):
                ii, jj = i + di, j + dj
                if not (0 <= ii < nx and 0 <= jj < ny) or blk[jj, ii]:
                    continue
                if di and dj and (blk[j, ii] and blk[jj, i]):
                    continue
                step = 1.4142135 if di and dj else 1.0
                ng = g + step + (turn_pen if (d >= 0 and nd != d) else 0.0)
                nk = (ii, jj, nd)
                if nk in came or best.get(nk, INF) <= ng:
                    continue
                best[nk] = ng
                heapq.heappush(pq, (ng + math.hypot(gi - ii, gj - jj), ng, ii, jj, nd, key))
        return None


def simplify(pts):
    out = [pts[0]]
    for k in range(1, len(pts) - 1):
        ax, ay = out[-1]
        bx, by = pts[k]
        cx, cy = pts[k + 1]
        cross = (bx - ax) * (cy - by) - (by - ay) * (cx - bx)
        if abs(cross) > 1e-9:
            out.append(pts[k])
    out.append(pts[-1])
    return [(rd(x), rd(y)) for x, y in out]


def plen(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


# ---------------- REWORK (non-D changes needed to make room) ----------------
# Filled in after the tier-0 run showed what blocks; each entry: remove these Bottom objects (matched by exact
# coordinates) and add these, with the reason.  See design_bottom.json 'rework'.
REWORK = []


def match_track(objs, net, x1, y1, x2, y2, tol=2e-3):
    for o in objs:
        if o['kind'] == 'seg' and o['net'] == net:
            g = o['g']
            if (abs(g[0] - x1) < tol and abs(g[1] - y1) < tol and abs(g[2] - x2) < tol and abs(g[3] - y2) < tol) or \
               (abs(g[0] - x2) < tol and abs(g[1] - y2) < tol and abs(g[2] - x1) < tol and abs(g[3] - y1) < tol):
                return o
    raise KeyError('track %s (%g,%g)-(%g,%g) not found' % (net, x1, y1, x2, y2))


def match_via(objs, net, x, y, tol=2e-3):
    for o in objs:
        if 'vid' in o and o['net'] == net and abs(o['g'][0] - x) < tol and abs(o['g'][1] - y) < tol:
            return o
    raise KeyError('via %s (%g,%g) not found' % (net, x, y))


# ---------------- main search ----------------
def dq_info():
    out = {}
    for n in range(16):
        e = EX['d_escapes']['D%d' % n]
        p = e['u3_pad']
        south = p['y'] < 11.85
        out[n] = dict(net='D%d' % n, pin=p['pad'], px=p['x'], py=p['y'], pw=p['w'], ph=p['h'], south=south,
                      edge=(p['y'] - p['h'] / 2) if south else (p['y'] + p['h'] / 2),
                      stub=e['bottom_stub'][0], via=(e['first_via']['x'], e['first_via']['y']),
                      stub_len=e['bottom_stub_length'])
    return out


def candidates(B, info, n, placed_boxes):
    q = info[n]
    s = -1 if q['south'] else 1
    net_a, net_b = 'SDRAM-D%d' % n, 'D%d' % n
    out = []
    xs = np.arange(round((q['px'] - 2.0) / GRID), round((q['px'] + 2.0) / GRID) + 1) * GRID
    ys = q['edge'] + s * (np.arange(4, 130) * GRID)       # 0.10 .. 3.2 mm outward of the pad edge
    for rot in (0, 90, 180, 270):
        for cy in ys:
            cy = round(cy / GRID) * GRID
            for cx in xs:
                A, Bp, pa, pb, prox = r_geom(cx, cy, rot)
                # component clearance
                if any(rect_gap(prox, b) < COMP_CLR - 1e-6 for r, b in B.proxies.items()):
                    continue
                if any(rect_gap(prox, b) < COMP_CLR - 1e-6 for b in placed_boxes):
                    continue
                ok = True
                for pad, net in ((pa, net_a), (pb, net_b)):
                    po = dict(kind='rect', g=pad)
                    for o in B.foreign(net, (pad[0] - 0.3, pad[1] - 0.3, pad[2] + 0.3, pad[3] + 0.3)):
                        d = G.dist(po, o)
                        if d < CLR - 1e-6:
                            ok = False; break
                        if o.get('is_pad') and d - MASK_EXP - o['mask'] < MASK_SLIVER - 1e-6 and d - MASK_EXP - o['mask'] > 1e-9:
                            ok = False; break
                    if not ok:
                        break
                if not ok:
                    continue
                # cost: neck (pin edge -> pad A) dominates; return (pad B -> via) second
                neck = abs(A[0] - q['px']) + abs(A[1] - q['edge'])
                ret = abs(Bp[0] - q['via'][0]) + abs(Bp[1] - q['via'][1])
                out.append((3 * neck + ret, cx, cy, rot, A, Bp, pa, pb, prox, neck))
    out.sort(key=lambda t: t[0])
    return out


def reach(B, net, w, seed, box):
    """cells reachable (8-connected) from seed on net's raster, ignoring candidate R pads; used only to prune."""
    from scipy import ndimage
    blk, x0, y0 = B.blocked(net, w, box)
    i, j = int(round((seed[0] - x0) / GRID)), int(round((seed[1] - y0) / GRID))
    free = ~blk
    if not (0 <= j < free.shape[0] and 0 <= i < free.shape[1]):
        return None
    free[j, i] = True
    lab, _ = ndimage.label(free, structure=np.ones((3, 3), bool))
    return (lab == lab[j, i]), x0, y0


def in_reach(R, pt):
    m, x0, y0 = R
    i, j = int(round((pt[0] - x0) / GRID)), int(round((pt[1] - y0) / GRID))
    return 0 <= j < m.shape[0] and 0 <= i < m.shape[1] and m[j, i]


def try_net(B, info, n, placed_boxes, max_cands=150, widths=(0.125, 0.10)):
    q = info[n]
    s = -1 if q['south'] else 1
    net_a, net_b = 'SDRAM-D%d' % n, 'D%d' % n
    cands = candidates(B, info, n, placed_boxes)
    tgt = (round(q['px'] / GRID) * GRID, round((q['edge'] - s * 0.15) / GRID) * GRID)
    v = q['via']
    win = (q['px'] - 3.0, min(q['edge'] - 3.4, v[1] - 1.0), q['px'] + 3.0, max(q['edge'] + 3.4, v[1] + 1.0))
    reach_cache = {}
    tried = 0
    for c in cands:
        if tried >= max_cands:
            break
        _, cx, cy, rot, A, Bp, pa, pb, prox, neck_est = c
        ok_w = []
        for w in widths:
            if w not in reach_cache:
                reach_cache[w] = (reach(B, net_a, w, tgt, win), reach(B, net_b, w, v, win))
            ra_, rb_ = reach_cache[w]
            if ra_ and rb_ and in_reach(ra_, A) and in_reach(rb_, Bp):
                ok_w.append(w)
        if not ok_w:
            continue
        tried += 1
        ra = dict(kind='rect', g=pa, net=net_a, src='R pad A', is_pad=True, mask=MASK_EXP, new=True, dyn=True)
        rb = dict(kind='rect', g=pb, net=net_b, src='R pad B', is_pad=True, mask=MASK_EXP, new=True, dyn=True)
        B.objs += [ra, rb]
        res = None
        for w in ok_w:
            box = (min(A[0], tgt[0]) - 1.2, min(A[1], tgt[1]) - 1.2, max(A[0], tgt[0]) + 1.2, max(A[1], tgt[1]) + 1.2)
            neck = B.route(net_a, w, A, tgt, box, max_len=4.0)
            if neck is None:
                continue
            neck_objs = [dict(kind='seg', g=(a[0], a[1], b[0], b[1], w / 2), net=net_a, src='neck', new=True, dyn=True)
                         for a, b in zip(neck, neck[1:])]
            B.objs += neck_objs
            box = (min(Bp[0], v[0]) - 1.5, min(Bp[1], v[1]) - 1.5, max(Bp[0], v[0]) + 1.5, max(Bp[1], v[1]) + 1.5)
            ret = B.route(net_b, w, Bp, v, box, max_len=10.0)
            if ret is None:
                del B.objs[-len(neck_objs):]
                continue
            ret_objs = [dict(kind='seg', g=(a[0], a[1], b[0], b[1], w / 2), net=net_b, src='return', new=True, dyn=True)
                        for a, b in zip(ret, ret[1:])]
            B.objs += ret_objs
            res = dict(n=n, cx=rd(cx), cy=rd(cy), rot=rot, A=A, Bp=Bp, pa=pa, pb=pb, prox=prox, w=w, neck=neck, ret=ret,
                       objs=[ra, rb] + neck_objs + ret_objs, tried=tried)
            break
        if res:
            return res, len(cands)
        B.objs.remove(ra); B.objs.remove(rb)
    return None, len(cands)



# ======================================================================================================
# inner layers (only touched by rework items)
INNER = ('L3-SIG', 'L4-SIG', 'L5-VCC3V3')
SDRAM_NETS = set(sum([v for k, v in EX['net_classes'].items() if k.startswith('SDRAM')], []))
SDRAM_NETS |= set('SDRAM-D%d' % n for n in range(16))


def load_inner():
    out = {L: [] for L in INNER}
    for i, t in enumerate(EX['tracks']):
        if t['layer'] in INNER:
            out[t['layer']].append(dict(kind='seg', g=(t['x1'], t['y1'], t['x2'], t['y2'], t['w'] / 2), net=t['net'],
                                        src='track#%d %s %s' % (i, t['net'], t['layer'])))
    for i, v in enumerate(EX['vias']):
        for L in INNER:
            if L in v['span']:
                out[L].append(dict(kind='circ', g=(v['x'], v['y'], v['size'] / 2), net=v['net'], vid=i,
                                   src='via#%d %s %s>%s' % (i, v['net'], v['span'][0], v['span'][-1])))
    for p in EX['pads']:
        if p['layer'] == 'Multi':
            for L in INNER:
                o = pad_obj(p)
                o['src'] += ' ' + L
                out[L].append(o)
    return out


def seg(net, x1, y1, x2, y2, w, src=None):
    return dict(kind='seg', g=(x1, y1, x2, y2, w / 2), net=net, src=src or '%s track (%.4g,%.4g)-(%.4g,%.4g) w%.4g' % (net, x1, y1, x2, y2, w))


def mvia(net, x, y, size=0.30, src=None):
    return dict(kind='circ', g=(x, y, size / 2), net=net, src=src or '%s microvia (%.4g,%.4g) %.2f' % (net, x, y, size),
                via_new=True)


# ---- rework catalogue (applied only in the variants that name them) ----
REWORKS = {
    'CH18': dict(
        name='CH18', why=("CHAN18 Bottom jumper runs diagonally (37.85,4.10)->(37.55,5.55) through the only room south of "
                          "U3-2 (D0); re-shape it to drop vertically at x 37.55 so D0's R fits. Same endpoints, same layer, "
                          "+0.06 mm length."),
        remove=[('track', 'CHAN18', 37.55, 5.55, 37.85, 4.1)],
        add=[seg('CHAN18', 37.85, 4.1, 37.85, 4.45, 0.0762), seg('CHAN18', 37.85, 4.45, 37.55, 4.75, 0.0762),
             seg('CHAN18', 37.55, 4.75, 37.55, 5.55, 0.0762)]),
    'VCC9': dict(
        name='VCC9', why=("NO GAIN (with it D3 and D4 still exclude each other: 4 placed either way, runs w1/w2). "
                          "U3-9 (VDDQ) reaches C38 by an outboard VCC3V3 L-route at y 5.10 that walls off the gaps beside "
                          "D3/D4. Replace it by a Bottom>L5 microvia at U3-9 (inboard, under the body) and a Bottom>L5 "
                          "microvia at C38-2: pin and cap then meet through the L5 VCC3V3 plane (2.9 mm apart) instead of "
                          "3.3 mm of 0.2 mm track."),
        remove=[('track', 'VCC3V3', 32.35, 6.1701, 32.5, 5.1), ('track', 'VCC3V3', 32.5, 5.1, 33.5492, 5.1),
                ('track', 'VCC3V3', 33.5492, 3.9499, 33.5492, 5.1)],
        add=[seg('VCC3V3', 32.35, 6.45, 32.35, 7.05, 0.2), mvia('VCC3V3', 32.35, 7.05),
             seg('VCC3V3', 33.5492, 3.9499, 33.55, 4.40, 0.2), mvia('VCC3V3', 33.55, 4.40)],
        inner_add={'L5-VCC3V3': [mvia('VCC3V3', 32.35, 7.05), mvia('VCC3V3', 33.55, 4.40)]}),
    'TMS': dict(
        name='TMS', why=("REJECTED (verify(): its new stack lands on RAS#/CHAN24 on L3 and SDRAM-CS#/CAS# on L4; a site "
                         "scan found legal TMS stack sites only at x 33.0..33.2, y 4.33..4.5, i.e. where it already is). "
                         "The TMS Bottom jumper (stack at 33.025,4.475 -> gap 31.95 -> stack at 32.15,8.125) crosses the "
                         "strip south of U3-8/9 at y 4.48..4.85; move its south microvia stack to (31.975,4.95) so the "
                         "jumper is one vertical piece and extend its L3 feed by 0.5 mm less."),
        remove=[('track', 'TMS', 32.65, 4.85, 33.025, 4.475), ('track', 'TMS', 32.375, 4.85, 32.65, 4.85),
                ('track', 'TMS', 31.975, 5.25, 32.375, 4.85), ('via', 'TMS', 33.025, 4.475)],
        add=[seg('TMS', 31.975, 4.95, 31.975, 5.25, 0.0762), mvia('TMS', 31.975, 4.95)],
        inner_remove=[('L3-SIG', 'track', 'TMS', 32.675, 4.2, 33.025, 4.475),
                      ('L3-SIG', 'track', 'TMS', 28.75, 4.2, 32.675, 4.2),
                      ('L3-SIG', 'via', 'TMS', 33.025, 4.475), ('L4-SIG', 'via', 'TMS', 33.025, 4.475),
                      ('L5-VCC3V3', 'via', 'TMS', 33.025, 4.475)],
        inner_add={'L3-SIG': [seg('TMS', 28.75, 4.2, 31.725, 4.2, 0.0762), seg('TMS', 31.725, 4.2, 31.975, 4.45, 0.0762),
                              seg('TMS', 31.975, 4.45, 31.975, 4.95, 0.0762), mvia('TMS', 31.975, 4.95, 0.27)],
                   'L4-SIG': [mvia('TMS', 31.975, 4.95, 0.30)],
                   'L5-VCC3V3': [mvia('TMS', 31.975, 4.95, 0.30)]}),
}


def match_inner(objs, kind, net, *xy, tol=2e-3):
    for o in objs:
        if o['net'] != net:
            continue
        g = o['g']
        if kind == 'track' and o['kind'] == 'seg':
            x1, y1, x2, y2 = xy
            if (abs(g[0] - x1) < tol and abs(g[1] - y1) < tol and abs(g[2] - x2) < tol and abs(g[3] - y2) < tol) or \
               (abs(g[0] - x2) < tol and abs(g[1] - y2) < tol and abs(g[2] - x1) < tol and abs(g[3] - y1) < tol):
                return o
        if kind == 'via' and o['kind'] == 'circ' and 'vid' in o and abs(g[0] - xy[0]) < tol and abs(g[1] - xy[1]) < tol:
            return o
    raise KeyError((kind, net, xy))


def apply_rework(B, item, removed, inner, inner_removed):
    rem = []
    for r in item.get('remove', []):
        if r[0] == 'track':
            o = match_track(B.objs, *r[1:])
            B.objs.remove(o); removed.append(o); rem.append(o['src'])
        else:   # a via: remove every record at that point (stacked microvias are separate records)
            k = 0
            while True:
                try:
                    o = match_via(B.objs, *r[1:])
                except KeyError:
                    break
                B.objs.remove(o); removed.append(o); rem.append(o['src']); k += 1
            assert k, r
    for a in item.get('add', []):
        a = dict(a); a['new'] = True; a['src'] = 'rework %s: %s' % (item['name'], a['src'])
        B.objs.append(a)
    for (L, kind, net, *xy) in item.get('inner_remove', []):
        k = 0
        while True:
            try:
                o = match_inner(inner[L], kind, net, *xy)
            except KeyError:
                break
            inner[L].remove(o); inner_removed.append((L, o)); rem.append(o['src'] + (' on ' + L if 'vid' in o else '')); k += 1
        assert k, (L, kind, net, xy)
    for L, lst in item.get('inner_add', {}).items():
        for a in lst:
            a = dict(a); a['new'] = True; a['src'] = 'rework %s: %s on %s' % (item['name'], a['src'], L)
            inner[L].append(a)
    return dict(name=item['name'], why=item['why'], removed=rem,
                added=['Bottom: ' + a['src'] for a in item.get('add', [])] +
                      ['%s: %s' % (L, a['src']) for L, l in item.get('inner_add', {}).items() for a in l])


NEW_REFS = set()


def run(order=None, rework=(), verbose=True):
    NEW_REFS.clear()
    objs = load_bottom()
    inner = load_inner()
    proxies = comp_proxies()
    info = dq_info()
    removed, inner_removed = [], []
    for n in range(16):
        st = info[n]['stub']
        o = match_track(objs, 'D%d' % n, st['x1'], st['y1'], st['x2'], st['y2'])
        objs.remove(o); removed.append(o)
    for o in objs:
        if o.get('ref') == 'U3' and o['net'] in ['D%d' % n for n in range(16)]:
            o['net'] = 'SDRAM-' + o['net']
    B = Board(objs, proxies)
    rw_log = [apply_rework(B, REWORKS[k], removed, inner, inner_removed) for k in rework]
    placed, failed = {}, {}
    boxes = []
    order = list(order or range(16))
    for n in order:
        t0 = time.time()
        res, nc = try_net(B, info, n, boxes)
        if res is None:
            failed[n] = dict(legal_positions=nc)
            if verbose:
                print('D%-2d FAILED (%d legal R positions, none routable)' % (n, nc), flush=True)
            continue
        ref = 'R%d' % (FIRST_DESIG + n)
        NEW_REFS.add(ref)
        res['ref'] = ref
        B.proxies[ref] = res['prox']
        boxes.append(res['prox'])
        placed[n] = res
        if verbose:
            print('D%-2d R at (%.3f, %.3f) rot %3d  neck %.3f  return %.3f  w %.3f  [cand %d/%d, %.1fs]' % (
                n, res['cx'], res['cy'], res['rot'], plen(res['neck']), plen(res['ret']), res['w'], res['tried'], nc,
                time.time() - t0), flush=True)
    return dict(B=B, inner=inner, info=info, placed=placed, failed=failed, removed=removed,
                inner_removed=inner_removed, rework=rw_log, order=order, variant=list(rework))


def verify(S):
    """Exact re-check of every NEW object: Bottom copper clearance, mask sliver, component clearance, and the
    inner-layer pieces of the rework items. Returns violations and the worst margin per rule."""
    B, inner = S['B'], S['inner']
    viol, worst = [], {}

    def note(rule, val, lim, a, b):
        if rule not in worst or val - lim < worst[rule]['margin']:
            worst[rule] = dict(value=rd(val), limit=lim, margin=rd(val - lim), a=a, b=b)
        if val < lim - 1e-6:
            viol.append(dict(rule=rule, value=rd(val), limit=lim, a=a, b=b))
    new = [o for o in B.objs if o.get('new')]
    seen = set()
    for a in new:
        ba = G.bbox(a)
        for b in B.objs:
            if b is a:
                continue
            if b.get('new'):
                key = tuple(sorted((id(a), id(b))))
                if key in seen:
                    continue
                seen.add(key)
            bb = G.bbox(b)
            if bb[2] < ba[0] - 0.6 or bb[0] > ba[2] + 0.6 or bb[3] < ba[1] - 0.6 or bb[1] > ba[3] + 0.6:
                continue
            d = G.dist(a, b)
            if not (a['net'] is not None and a['net'] == b['net']):
                note('Bottom copper clearance', d, CLR, a['src'], b['src'])
            if a.get('is_pad') and b.get('is_pad'):
                gap = d - a['mask'] - b['mask']
                if gap > 1e-9:
                    note('solder-mask sliver (Bottom)', gap, MASK_SLIVER, a['src'], b['src'])
    for r in sorted(NEW_REFS):
        for k, bx in B.proxies.items():
            if k == r or (k in NEW_REFS and k < r):
                continue
            note('component clearance (Bottom bodies)', rect_gap(B.proxies[r], bx), COMP_CLR, r, k)
    for L, objs in inner.items():
        for a in [o for o in objs if o.get('new')]:
            for b in objs:
                if b is a or (a['net'] is not None and a['net'] == b['net']):
                    continue
                if L == 'L5-VCC3V3' and b['net'] == 'VCC3V3':
                    continue
                lim = 0.10 if (L in ('L3-SIG', 'L4-SIG') and (a['net'] in SDRAM_NETS or b['net'] in SDRAM_NETS)) else CLR
                if L == 'L5-VCC3V3':
                    # the VCC3V3 pour must clear foreign vias: 0.175 to through vias (Clearance_Plane_ThruVia),
                    # 0.165 to microvias (PlaneClearance, micro); a foreign NEW microvia is held to the same numbers
                    thru = 'through' in b['src'] or 'through' in a['src']
                    lim = 0.175 if thru else 0.165
                d = G.dist(a, b)
                if d < 1.0:
                    note('%s clearance' % L, d, lim, a['src'], b['src'])
    return viol, worst


# ======================================================================================================
# outputs
TD_PS_PER_MM = {0.125: 6.3025, 0.10: 6.2957}   # Bottom microstrip on the fab stack: si/spice/fieldsolve.zulu_line()


def pad1_offset(rot):
    """Pad 1 offset of the board's R0201 on Bottom: measured R117 rot 0 -> (-0.3,0); R114 rot 180 -> (+0.3,0);
    R118 rot 270 -> (0,+0.3). rot 90 -> (0,-0.3) is inferred by symmetry (no Bottom 0201 at 90 on the board)."""
    return {0: (-0.3, 0.0), 90: (0.0, -0.3), 180: (0.3, 0.0), 270: (0.0, 0.3)}[rot]


def gap_audit(S):
    """For every pad-row gap: the non-D objects inside the 0.125 mm return corridor (after the stub removal + rework)."""
    B = S['B']
    u3 = sorted([o for o in B.objs if o.get('ref') == 'U3'], key=lambda o: o['g'][0])
    out = []
    for row, yc in (('south', 6.1701), ('north', 17.53)):
        pads = [o for o in u3 if abs((o['g'][1] + o['g'][3]) / 2 - yc) < 0.01 and 28.0 < o['g'][0] < 39.0]
        for a, b in zip(pads, pads[1:]):
            xg = (a['g'][2] + b['g'][0]) / 2
            y_out = (a['g'][1] - 0.45) if row == 'south' else (a['g'][3] + 0.45)
            y_in = (a['g'][3] + 0.25) if row == 'south' else (a['g'][1] - 0.25)
            cor = dict(kind='seg', g=(xg, y_out, xg, y_in, 0.0625), net='probe')
            blk = sorted(set(('new %s of %s' % (o['src'], o['net'])) if o.get('dyn') else o['src'] for o in B.objs
                             if o is not a and o is not b and G.dist(cor, o) < CLR - 1e-9
                             and (o.get('dyn') or not (o['net'] or '').startswith(('D', 'SDRAM-D')))))
            out.append(dict(row=row, x=rd(xg), between='U3-%s(%s) / U3-%s(%s)' % (a['pad'], a['net'], b['pad'], b['net']),
                            blocked_by=blk))
    return out


def failed_detail(S):
    """Why each unplaced net failed: its two neighbouring pad-row gaps and what sits in them, how many R positions
    pass the static rules, and how far the nearest of those is from the pin."""
    ga = gap_audit(S)
    out = {}
    boxes = [S['B'].proxies[r] for r in NEW_REFS]
    for n, v in S['failed'].items():
        q = S['info'][n]
        row = 'south' if q['south'] else 'north'
        adj = [g for g in ga if g['row'] == row and abs(g['x'] - q['px']) < 0.45]
        c = candidates(S['B'], S['info'], n, boxes)
        near = min((t[9] for t in c), default=None)
        out['D%d' % n] = dict(legal_R_positions=len(c), nearest_legal_pad1_from_pad_edge_mm=None if near is None else rd(near, 3),
                              adjacent_gaps=[dict(x=g['x'], between=g['between'], blocked_by=g['blocked_by'] or 'free') for g in adj])
    return out


def report(S, viol, worst, path_json):
    info, placed = S['info'], S['placed']
    pl, cu = [], {}
    for n in range(16):
        q = info[n]
        if n not in placed:
            continue
        r = placed[n]
        w = r['w']
        neck_len = plen(r['neck'])
        ret_len = plen(r['ret'])
        inside = 0.15   # the neck ends 0.15 mm inside U3's pad, measured from its outer edge
        from_edge = neck_len - inside
        from_centre = neck_len + (q['ph'] / 2 - inside)
        td = TD_PS_PER_MM[w]
        ox, oy = pad1_offset(r['rot'])
        pl.append(dict(ref=r['ref'], nets='pad1 SDRAM-D%d (U3 side) / pad2 D%d (line side)' % (n, n), part='Yageo RC0201FR-0722RL',
                       footprint='R0201 (zulu_a7.PcbLib)', side='Bottom', x=r['cx'], y=r['cy'], rot=r['rot'],
                       pad1_xy=[rd(r['cx'] + ox), rd(r['cy'] + oy)],
                       dist_from_u3_pin_mm=rd(from_centre, 3), dist_from_u3_pad_edge_mm=rd(from_edge, 3),
                       neck_ps_from_pad_centre=round(from_centre * td, 1), neck_ps_from_pad_edge=round(from_edge * td, 1),
                       neck_width=w, return_width=w, neck_len=rd(neck_len, 3), return_len=rd(ret_len, 3),
                       old_stub_len=rd(q['stub_len'], 3), first_via=list(q['via']),
                       neck_pts=[list(p) for p in r['neck']], return_pts=[list(p) for p in r['ret']]))
        cu['D%d' % n] = dict(
            removed=['Bottom track D%d (%.4f,%.4f)-(%.4f,%.4f) w0.125 (old stub U3-%s -> first via)' % (
                n, q['stub']['x1'], q['stub']['y1'], q['stub']['x2'], q['stub']['y2'], q['pin'])],
            net_change='U3-%s pad: D%d -> SDRAM-D%d (via the schematic; add SDRAM-D%d to class SDRAM_DATA)' % (q['pin'], n, n, n),
            added_SDRAM_side=['Bottom w%.3f SDRAM-D%d %s' % (w, n, ' -> '.join('(%.3f,%.3f)' % p for p in r['neck']))],
            added_line_side=['Bottom w%.3f D%d %s' % (w, n, ' -> '.join('(%.3f,%.3f)' % p for p in r['ret']))],
            unchanged='first through via (%.3f,%.3f) and all of D%d beyond it (L3/L4/Top) stay as they are' % (q['via'][0], q['via'][1], n))
    out = dict(
        source=dict(extract=EXTRACT, pcbdoc_md5=EX['source']['pcbdoc_md5'], script=os.path.abspath(__file__)),
        approach='bottom: R0201 on Bottom outboard of U3 pad row; neck pad->R, return R->gap between U3 pads->existing first via',
        variant=S['variant'], order=S['order'],
        rules_used=dict(copper_clearance=CLR, component_clearance=COMP_CLR, mask_expansion=MASK_EXP, mask_sliver=MASK_SLIVER,
                        width_bottom=W_BOT, inner_SDRAM_clearance=0.10, plane_clearance_micro=0.165, plane_thruvia=0.175,
                        component_proxy='bbox(pads + Mech3/Mech4) per Bottom part; U3 also datasheet max body; new R0201 = pads 0.9 x Mech3 0.396'),
        placed=sorted('D%d' % n for n in placed), failed=failed_detail(S),
        placements=pl, copper=cu, rework=S['rework'],
        verify=dict(violations=viol, worst=worst),
        gap_audit=gap_audit(S))
    json.dump(out, open(path_json, 'w'), indent=1)
    return out


def plot(S, path_png, title):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle, Polygon
    B = S['B']
    fig, axs = plt.subplots(2, 1, figsize=(15, 13), dpi=160)
    boxes = [(27.6, 3.3, 39.9, 9.4), (27.6, 15.7, 39.9, 21.2)]

    def col(o):
        net = o['net'] or ''
        if o.get('dyn'):
            return 'tab:red' if net.startswith('SDRAM-D') else 'tab:orange'
        if o.get('new'):
            return 'tab:green'
        if net.startswith('SDRAM-D') or (net.startswith('D') and net[1:].isdigit()):
            return 'gold'
        return 'tab:blue'
    for ax, (x0, y0, x1, y1), name in zip(axs, boxes, ('south row D0-D7 (Bottom, seen from above)', 'north row D8-D15')):
        for r, b in B.proxies.items():
            if b[2] < x0 or b[0] > x1 or b[3] < y0 or b[1] > y1:
                continue
            new = r in NEW_REFS
            ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fill=False, ls='-' if new else '--',
                                   lw=1.0 if new else 0.5, ec='m' if new else 'k', zorder=5))
            ax.text(min(max((b[0] + b[2]) / 2, x0 + 0.3), x1 - 0.3), min(b[3], y1 - 0.1), r, fontsize=6, ha='center',
                    va='bottom', color='m' if new else 'k', zorder=6, clip_on=True)
        for o in S['removed']:
            if o['kind'] == 'seg':
                g = o['g']
                ax.plot([g[0], g[2]], [g[1], g[3]], ls=':', color='k', lw=1.0, zorder=7)
        for o in B.objs:
            b = G.bbox(o)
            if b[2] < x0 or b[0] > x1 or b[3] < y0 or b[1] > y1:
                continue
            c = col(o)
            g = o['g']
            if o['kind'] == 'rect':
                ax.add_patch(Rectangle((g[0], g[1]), g[2] - g[0], g[3] - g[1], fc=c, ec='k', lw=0.3, alpha=0.85, zorder=2))
            elif o['kind'] == 'circ':
                ax.add_patch(Circle((g[0], g[1]), g[2], fc=c, ec='k', lw=0.3, alpha=0.85, zorder=3))
            else:
                dx, dy = g[2] - g[0], g[3] - g[1]
                L = math.hypot(dx, dy) or 1e-9
                nx, ny = -dy / L * g[4], dx / L * g[4]
                ax.add_patch(Polygon([(g[0] + nx, g[1] + ny), (g[2] + nx, g[3] + ny), (g[2] - nx, g[3] - ny), (g[0] - nx, g[1] - ny)],
                                     fc=c, ec='none', alpha=0.8, zorder=4 if o.get('dyn') else 2))
                for (cx, cy) in ((g[0], g[1]), (g[2], g[3])):
                    ax.add_patch(Circle((cx, cy), g[4], fc=c, ec='none', alpha=0.8, zorder=4 if o.get('dyn') else 2))
        for n, r in S['placed'].items():
            if y0 <= r['cy'] <= y1:
                ax.annotate('%s D%d' % (r['ref'], n), (r['cx'], r['cy']), xytext=(0, -14 if r['cy'] < 10 else 14),
                            textcoords='offset points', fontsize=7, ha='center', color='m', zorder=8,
                            arrowprops=dict(arrowstyle='-', color='m', lw=0.5))
        for n in S['failed']:
            q = S['info'][n]
            if y0 <= q['py'] <= y1:
                ax.text(q['px'], q['py'], 'D%d\nnot\nplaced' % n, fontsize=6, ha='center', va='center', color='darkred',
                        zorder=9, fontweight='bold')
        ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal')
        ax.set_title(name, fontsize=9)
        ax.grid(True, lw=0.2)
        ax.tick_params(labelsize=7)
    fig.suptitle(title, fontsize=10)
    from matplotlib.lines import Line2D
    fig.legend(handles=[Line2D([], [], color='tab:red', lw=4, label='new SDRAM-Dn copper (U3 pad side)'),
                        Line2D([], [], color='tab:orange', lw=4, label='new Dn copper (R -> existing first via)'),
                        Line2D([], [], color='gold', lw=4, label='existing D copper / U3 DQ pads'),
                        Line2D([], [], color='tab:green', lw=4, label='rework copper (non-D)'),
                        Line2D([], [], color='k', ls=':', label='removed copper'),
                        Line2D([], [], color='m', lw=1, label='new R0201 body proxy (pads + Mech3)'),
                        Line2D([], [], color='k', ls='--', lw=0.5, label='existing part proxies')],
               loc='lower center', ncol=4, fontsize=7)
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
    fig.savefig(path_png)


if __name__ == '__main__':
    a = sys.argv[1:]
    variant = [v for v in (a[a.index('--variant') + 1].split(',') if '--variant' in a else []) if v]
    order = [int(x) for x in a[a.index('--order') + 1].split(',')] if '--order' in a else list(range(16))
    tag = a[a.index('--tag') + 1] if '--tag' in a else None
    if '--compclr' in a:      # what-if only: ComponentClearance is NOT in this board's batch DRC (docs/drc_jtag_column.drc)
        COMP_CLR = float(a[a.index('--compclr') + 1])
    S = run(order=order, rework=variant)
    viol, worst = verify(S)
    pj = OUT_JSON if tag is None else os.path.join(os.environ.get('DB_SCRATCH', HERE), 'design_bottom_%s.json' % tag)
    out = report(S, viol, worst, pj)
    print('variant %s order %s: placed %d/16 %s, violations %d' % (variant, order, len(S['placed']),
                                                                   out['placed'], len(viol)))
    for k, v in worst.items():
        print('  worst %-40s %.4f (limit %.3f, margin %+.4f)  %s | %s' % (k, v['value'], v['limit'], v['margin'], v['a'], v['b']))
    for v in viol:
        print('  VIOLATION', v)
    if tag is None:
        plot(S, OUT_PNG, 'Zulu_a7_no_pmod Rev 2 -- series R0201 on Bottom at U3 (design_bottom.py; variant %s): %d of 16 placed'
             % ('+'.join(variant) or 'D-copper only', len(S['placed'])))
