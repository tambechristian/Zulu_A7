"""u3_end search engine (D13/D14/D15 series R at the U3 end).

World = board_extract.json + the 13-R plan (dq_series_r_plan.json md5 f2949630), applied with the checker copy's own
apply().  Optional 'unlock' pre-deltas (small re-routes of non-critical copper) are applied on top.
Every geometric test below uses the checker's own exact primitives (check.dist / grow / pad_shape / gap_rule /
width_rule / mask_exp).  The raster (0.02 mm) is only used to FIND routes; every route is re-verified exactly.
"""
import math, json, copy, collections, heapq
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
import base
C = base.C
CU = C.CU
PL = {'Top': 'Top Layer', 'Bottom': 'Bottom Layer'}
for _L in CU:
    PL.setdefault(_L, _L)
DESIGN_MARGIN = 0.0025       # router keeps every new copper/hole >= rule + 2.5 um (Altium rounds to 2.54 um)
GRID = 0.02

class NO:                    # light object for gap_rule (needs .net and .ref)
    def __init__(s, net, ref=None):
        s.net, s.ref = net, ref


def plan_layer(L):
    return PL[L]


def span(a, b):
    i, j = CU.index(a), CU.index(b)
    if i > j:
        i, j = j, i
    return CU[i:j + 1]


class World:
    def __init__(self, plan_path=base.PLAN13):
        self.plan_path = plan_path
        E, pads, tracks, vias, nf = base.applied(plan_path)
        self.pads, self.tracks, self.vias = pads, tracks, vias
        self.objs = C.build_objs(pads, tracks, vias, set())
        self.grid = C.Grid(self.objs, 0.5)
        self.drills = []
        for o in self.objs:
            if o.kind == 'via' and o.layer == o.span[0]:
                self.drills.append((o.xy, o.hole, set(o.span), o.uid))
        for i, p in enumerate(pads):
            if p.get('hole', 0) > 0:
                self.drills.append(((p['x'], p['y']), p['hole'], set(CU), ('p', i)))
        side_of = {c['ref']: c['side'] for c in C.B['components']}
        self.boxes = {}                       # body/courtyard boxes per ref (pads + Mech3/Mech4 bodies)
        for ref, v in C.B['component_outlines'].items():
            if ref == 'X2':
                continue
            bx = [v[k] for k in ('pads', 'Mech3', 'Mech4', 'Mech3(region)', 'Mech4(region)') if k in v]
            if ref == 'U3':
                m = C.B['u3']['body']['max']
                bx.append([m['x0'], m['y0'], m['x1'], m['y1']])
            if ref == 'U1':
                bx = [v['pads'], [41.4, 6.9, 51.4, 16.9]]
            self.boxes[ref] = (side_of.get(ref), bx)
        self.altbox = {}
        for ref, v in C.B['component_outlines'].items():
            if ref == 'X2':
                continue
            bxs = [v[k] for k in v if k in ('pads', 'Mech3', 'Mech4', 'Mech8', 'Mech3(region)', 'Mech4(region)', 'Mech8(region)')]
            if bxs:
                self.altbox[ref] = (side_of.get(ref), [min(b[0] for b in bxs), min(b[1] for b in bxs), max(b[2] for b in bxs), max(b[3] for b in bxs)])
        self.court = {}                       # Mech7 courtyards (soft)
        for ref, v in C.B['component_outlines'].items():
            if 'Mech7' in v and ref != 'X2':
                self.court[ref] = (side_of.get(ref), v['Mech7'])
        self.new_r_boxes = {}                 # the plan's own new R bodies (pads bbox), same side
        P = json.load(open(plan_path))
        for pr in P['parts']:
            xs = [pr['pad1']['x'], pr['pad2']['x']]
            ys = [pr['pad1']['y'], pr['pad2']['y']]
            self.new_r_boxes[pr['ref']] = (pr['side'], [min(xs) - 0.15, min(ys) - 0.15, max(xs) + 0.15, max(ys) + 0.15])
        self.vis_text = [t for t in C.B['texts'] if t['layer'] in ('TopOverlay', 'BottomOverlay') and not t['hidden']]

    # ---- lookup helpers
    def find_tracks(self, net, layer=None):
        return [o for o in self.objs if o.kind == 'track' and o.net == net and (layer is None or o.layer == layer)]

    def find_via(self, net, x, y):
        out = [o for o in self.objs if o.kind == 'via' and o.net == net and abs(o.xy[0] - x) < 2e-3 and abs(o.xy[1] - y) < 2e-3]
        return out

    def pad_obj(self, ref, pad, layer):
        return [o for o in self.objs if o.kind == 'pad' and o.ref == ref and o.pad == pad and o.layer == layer][0]


# ------------------------------------------------------------------ candidate objects
class Cand:
    """delta on top of the world: removed uids, relabelled uids, new shapes (pads/tracks/vias) + plan records"""
    def __init__(self, world, net_bit):
        self.W = world
        self.n = net_bit
        self.removed = set()
        self.relabel = {}
        self.new = []          # list of dicts: kind, layer, net, shape, (w), (hole, span, xy), (ref,pad)
        self.rec = dict(remove=[], remove_vias=[], tracks=[], vias=[], parts=[], renet_pads=[], microvias=[])
        self.notes = []

    def net_of(self, o):
        return self.relabel.get(o.uid, o.net)

    def remove_track(self, o, why=None):
        self.removed.add(o.uid)
        r = o.rec
        d = dict(net=r['net'], layer=plan_layer(r['layer']), w=r['w'], x1=r['x1'], y1=r['y1'], x2=r['x2'], y2=r['y2'])
        if why:
            d['why'] = why
        self.rec['remove'].append(d)

    def remove_via(self, uid, why=None):
        v = [o for o in self.W.objs if o.uid == uid][0].rec
        self.removed.add(uid)
        d = dict(net=v['net'], x=v['x'], y=v['y'], hole=v['hole'], span=[v['span'][0] if v['span'][0] != 'Bottom' else 'Bottom', v['span'][-1]])
        if why:
            d['why'] = why
        self.rec['remove_vias'].append(d)

    def rename_track(self, o, new_net):
        self.remove_track(o, why='rename')
        r = o.rec
        self.add_track(new_net, r['layer'], r['w'], r['x1'], r['y1'], r['x2'], r['y2'], why='rename')

    def rename_via(self, uid, new_net):
        v = [o for o in self.W.objs if o.uid == uid][0].rec
        self.remove_via(uid, why='rename')
        self.add_via(new_net, v['x'], v['y'], v['size'], v['hole'], v['span'][0], v['span'][-1], why='rename')

    def add_track(self, net, layer, w, x1, y1, x2, y2, why=None):
        x1, y1, x2, y2 = [float(round(float(v), 4)) for v in (x1, y1, x2, y2)]
        self.new.append(dict(kind='track', layer=layer, net=net, w=w, shape=('C', x1, y1, x2, y2, w / 2)))
        d = dict(net=net, layer=plan_layer(layer), w=w, x1=x1, y1=y1, x2=x2, y2=y2)
        if why:
            d['why'] = why
        self.rec['tracks'].append(d)

    def add_via(self, net, x, y, size, hole, frm, to, why=None):
        x, y = float(round(float(x), 4)), float(round(float(y), 4))
        sp = span(frm, to)
        for L in sp:
            self.new.append(dict(kind='via', layer=L, net=net, shape=('C', x, y, x, y, size / 2), hole=hole, span=sp, xy=(x, y)))
        d = dict(net=net, x=x, y=y, size=size, hole=hole, from_=plan_layer(sp[0]), to=plan_layer(sp[-1]))
        d['from'] = d.pop('from_')
        if why:
            d['why'] = why
        self.rec['vias'].append(d)
        if why != 'rename' and not (sp[0] == 'Top' and sp[-1] == 'Bottom'):
            self.rec['microvias'].append(dict(net=net, x=x, y=y, size=size, hole=hole, **{'from': plan_layer(sp[0]), 'to': plan_layer(sp[-1])},
                                              type=('microvia %.2f/%.2f' % (size, hole)) if len(sp) == 2 and size >= 0.29 else 'buried %.2f/%.2f' % (size, hole)))

    def add_part(self, ref, side, x, y, rot):
        p1, p2 = r_pads(x, y, rot)
        n = self.n
        x, y = round(x, 4), round(y, 4)
        self.rec['parts'].append(dict(ref=ref, net_bit=n, side=side, footprint='R0201', comment='22', x=x, y=y, rot=rot,
                                      pad1=dict(net='SDRAM-D%d' % n, x=round(p1[0], 4), y=round(p1[1], 4)),
                                      pad2=dict(net='D%d' % n, x=round(p2[0], 4), y=round(p2[1], 4)), designator_hidden=True))
        for k, (px, py), net in (('1', p1, 'SDRAM-D%d' % n), ('2', p2, 'D%d' % n)):
            self.new.append(dict(kind='pad', layer=side, net=net, shape=('R', round(px, 4), round(py, 4), 0.15, 0.15), ref=ref, pad=k,
                                 xy=(round(px, 4), round(py, 4))))

    def renet_u3(self):
        pin = C.DPIN[self.n]
        o = self.W.pad_obj('U3', str(pin), 'Bottom')
        self.relabel[o.uid] = 'SDRAM-D%d' % self.n
        self.rec['renet_pads'].append(dict(ref='U3', pad=str(pin), net='SDRAM-D%d' % self.n))

    # ---- exact verification of every NEW object against everything (world after delta + other new objects)
    def verify(self, extra_new=(), margin=0.0, full=True):
        """returns list of violations (rule, value, limit, a, b) and dict of worst margins"""
        viol, worst = [], {}
        news = list(self.new) + list(extra_new)

        def note(rule, m, a, b):
            if rule not in worst or m < worst[rule][0]:
                worst[rule] = (round(m, 4), a, b)

        for i, a in enumerate(news):
            A = a['shape']
            an = NO(a['net'], a.get('ref'))
            bb = C.bbox(A)
            for q in self.W.grid.near(a['layer'], bb, 0.45):
                if q.uid in self.removed:
                    continue
                qn = self.net_of(q)
                if qn == a['net']:
                    continue
                d = C.dist(A, q.shape)
                g = C.gap_rule(an, NO(qn, q.ref), a['layer'])
                m = d - g
                note('clearance ' + a['layer'], m, desc(a), q.tag)
                if m < margin - 1e-7:
                    viol.append(('clearance', a['layer'], round(d, 4), g, desc(a), q.tag))
            for j, b in enumerate(news):
                if j <= i or b['layer'] != a['layer'] or b['net'] == a['net']:
                    continue
                d = C.dist(A, b['shape'])
                g = C.gap_rule(an, NO(b['net'], b.get('ref')), a['layer'])
                m = d - g
                note('clearance ' + a['layer'], m, desc(a), desc(b))
                if m < margin - 1e-7:
                    viol.append(('clearance', a['layer'], round(d, 4), g, desc(a), desc(b)))
            if a['kind'] == 'track':
                lo, hi, rn = C.width_rule(a['net'], a['layer'])
                if not (lo - 1e-6 <= a['w'] <= hi + 1e-6):
                    viol.append(('width', a['layer'], a['w'], (lo, hi), desc(a), rn))
        # holes
        nvias = {}
        for a in news:
            if a['kind'] == 'via':
                nvias[(a['xy'], tuple(a['span']))] = a
        nd = [(a['xy'], a['hole'], set(a['span']), desc(a)) for a in nvias.values()]
        for i, (xy, h, sp, t) in enumerate(nd):
            for (xy2, h2, sp2, uid) in self.W.drills:
                if uid in self.removed:
                    continue
                if abs(xy[0] - xy2[0]) < 1e-4 and abs(xy[1] - xy2[1]) < 1e-4:
                    continue
                if not (sp & sp2):
                    continue
                d = math.hypot(xy[0] - xy2[0], xy[1] - xy2[1]) - h / 2 - h2 / 2
                if d > 0.6:
                    continue
                note('hole_to_hole', d - 0.24, t, str(uid))
                if d < 0.24 + margin - 1e-7:
                    viol.append(('hole_to_hole', round(d, 4), 0.24, t, str(uid)))
            for j, (xy2, h2, sp2, t2) in enumerate(nd):
                if j <= i or not (sp & sp2):
                    continue
                if abs(xy[0] - xy2[0]) < 1e-4 and abs(xy[1] - xy2[1]) < 1e-4:
                    continue
                d = math.hypot(xy[0] - xy2[0], xy[1] - xy2[1]) - h / 2 - h2 / 2
                note('hole_to_hole', d - 0.24, t, t2)
                if d < 0.24 + margin - 1e-7:
                    viol.append(('hole_to_hole', round(d, 4), 0.24, t, t2))
        # solder mask (pads only)
        for a in news:
            if a['kind'] != 'pad':
                continue
            mo = C.grow(a['shape'], 0.05)
            for q in self.W.grid.near(a['layer'], C.bbox(mo), 0.45):
                if q.kind != 'pad' or q.uid in self.removed:
                    continue
                mq = C.grow(q.shape, C.mask_exp(q))
                d = C.dist(mo, mq)
                note('mask_web ' + a['layer'], d - 0.10, desc(a), q.tag)
                if d < 0.10 - 1e-7:
                    viol.append(('mask_web', a['layer'], round(d, 4), 0.10, desc(a), q.tag))
            for b in news:
                if b is a or b['kind'] != 'pad' or b['layer'] != a['layer'] or b.get('ref') == a.get('ref'):
                    continue
                d = C.dist(mo, C.grow(b['shape'], 0.05))
                note('mask_web ' + a['layer'], d - 0.10, desc(a), desc(b))
                if d < 0.10 - 1e-7:
                    viol.append(('mask_web', a['layer'], round(d, 4), 0.10, desc(a), desc(b)))
        return viol, worst

    def body_checks(self, side, x, y, rot, ref):
        """hard: R body (0.63 x 0.33 max) must not overlap another same-side component body/pads box (incl. the plan's
        new Rs).  soft: Altium ComponentClearance 0.254 on bounding boxes, Mech7 courtyard overlap, visible silk."""
        horiz = rot % 180 == 0
        body = [x - 0.315, y - 0.165, x + 0.315, y + 0.165] if horiz else [x - 0.165, y - 0.315, x + 0.165, y + 0.315]
        pbox = [x - 0.45, y - 0.15, x + 0.45, y + 0.15] if horiz else [x - 0.15, y - 0.45, x + 0.15, y + 0.45]
        hard, soft = [], []

        def rr(a, b):
            return C.d_rect_rect(((a[0] + a[2]) / 2, (a[1] + a[3]) / 2, (a[2] - a[0]) / 2, (a[3] - a[1]) / 2),
                                 ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, (b[2] - b[0]) / 2, (b[3] - b[1]) / 2))

        def overlap(a, b):
            return min(a[2], b[2]) - max(a[0], b[0]) > 1e-6 and min(a[3], b[3]) - max(a[1], b[1]) > 1e-6
        for r2, (s2, bx2) in self.W.boxes.items():
            if s2 != side:
                continue
            for b in bx2:
                if overlap(body, b) or overlap(pbox, b):
                    hard.append('body overlaps %s box %s' % (r2, [round(v, 3) for v in b]))
                    break
        for r2, (s2, b) in self.W.new_r_boxes.items():
            if s2 == side and overlap([body[0] - 1e-6, body[1], body[2], body[3]], b):
                hard.append('body overlaps planned %s' % r2)
        cc = []
        allalt = dict(self.W.altbox)
        for r2, v in self.W.new_r_boxes.items():
            allalt[r2] = v
        for r2, (s2, b) in allalt.items():
            if s2 != side:
                continue
            d = rr(pbox, b)
            if d < 0.6:
                cc.append((round(d, 4), r2))
        cc.sort()
        if cc and cc[0][0] < 0.254 - 1e-6:
            soft.append('ComponentClearance %.3f to %s (<0.254)' % cc[0])
        for r2, (s2, b) in self.W.court.items():
            if s2 == side and overlap(body, b):
                soft.append('inside %s Mech7 courtyard' % r2)
        lay = 'TopOverlay' if side == 'Top' else 'BottomOverlay'
        for t in self.W.vis_text:
            if t['layer'] != lay:
                continue
            tb = C.text_box(t)
            d = C.dist(tb, ('R', x, y, (pbox[2] - pbox[0]) / 2 + 0.05, (pbox[3] - pbox[1]) / 2 + 0.05))
            if d < 0.254:
                soft.append("visible silk '%s' at (%.2f,%.2f) %.3f from pad openings" % (t['text'], t['x'], t['y'], d))
        return hard, soft, cc[:3]


def desc(a):
    if a['kind'] == 'track':
        s = a['shape']
        return 'new track %s %s (%.3f,%.3f)-(%.3f,%.3f) w%.4f' % (a['layer'], a['net'], s[1], s[2], s[3], s[4], a['w'])
    if a['kind'] == 'via':
        return 'new via %s (%.3f,%.3f) %s>%s d%.2f' % (a['net'], a['xy'][0], a['xy'][1], a['span'][0], a['span'][-1], a['shape'][5] * 2)
    return 'new pad %s-%s %s' % (a.get('ref'), a.get('pad'), a['net'])


def r_pads(x, y, rot):
    rot = int(round(rot)) % 360
    d = {0: (-0.3, 0), 180: (0.3, 0), 90: (0, -0.3), 270: (0, 0.3)}[rot]
    return (x + d[0], y + d[1]), (x - d[0], y - d[1])


# ------------------------------------------------------------------ raster router
class Router:
    """window raster of one layer for a track of net N, width W: free cell = every non-own-net object (world after
    the candidate's removals/relabels + extra shapes) is at >= gap + W/2 + DESIGN_MARGIN + guard from the cell centre."""
    def __init__(self, cand, layer, net, w, box, extra=(), guard=0.012):
        self.c, self.L, self.N, self.w = cand, layer, net, w
        X0, Y0, X1, Y1 = box
        self.X0, self.Y0 = X0, Y0
        self.nx, self.ny = int(math.ceil((X1 - X0) / GRID)) + 1, int(math.ceil((Y1 - Y0) / GRID)) + 1
        xs = X0 + np.arange(self.nx) * GRID
        ys = Y0 + np.arange(self.ny) * GRID
        self.xs, self.ys = xs, ys
        blk = np.zeros((self.ny, self.nx), bool)
        an = NO(net)
        shapes = []
        for q in cand.W.grid.near(layer, (X0, Y0, X1, Y1), 0.8):
            if q.layer != layer or q.uid in cand.removed:
                continue
            qn = cand.net_of(q)
            if qn == net:
                continue
            shapes.append((q.shape, C.gap_rule(an, NO(qn, q.ref), layer)))
        for a in list(cand.new) + list(extra):
            if a['layer'] != layer or a['net'] == net:
                continue
            shapes.append((a['shape'], C.gap_rule(an, NO(a['net'], a.get('ref')), layer)))
        self.shapes = shapes
        for S, g in shapes:
            G = g + w / 2 + DESIGN_MARGIN + guard
            bx = C.bbox(C.grow(S, G))
            if bx[2] < X0 or bx[0] > X1 or bx[3] < Y0 or bx[1] > Y1:
                continue
            i0, i1 = max(0, int((bx[0] - X0) / GRID)), min(self.nx, int((bx[2] - X0) / GRID) + 2)
            j0, j1 = max(0, int((bx[1] - Y0) / GRID)), min(self.ny, int((bx[3] - Y0) / GRID) + 2)
            if i0 >= i1 or j0 >= j1:
                continue
            X, Y = np.meshgrid(xs[i0:i1], ys[j0:j1])
            blk[j0:j1, i0:i1] |= _dist_field(S, X, Y) < G
        self.blk = blk
        self.free = ~blk
        self._graph = None

    def cell(self, x, y):
        return int(round((x - self.X0) / GRID)), int(round((y - self.Y0) / GRID))

    def xy(self, i, j):
        return self.X0 + i * GRID, self.Y0 + j * GRID

    def graph(self):
        if self._graph is None:
            ny, nx = self.ny, self.nx
            idx = np.arange(ny * nx).reshape(ny, nx)
            rows, cols, wts = [], [], []
            F = self.free
            for dj, di, wt in ((0, 1, 1.0), (1, 0, 1.0), (1, 1, math.sqrt(2)), (1, -1, math.sqrt(2))):
                if di < 0:
                    a = F[0:ny - dj, -di:nx]
                    b = F[dj:ny, 0:nx + di]
                    ia = idx[0:ny - dj, -di:nx]
                    ib = idx[dj:ny, 0:nx + di]
                else:
                    a = F[0:ny - dj, 0:nx - di]
                    b = F[dj:ny, di:nx]
                    ia = idx[0:ny - dj, 0:nx - di]
                    ib = idx[dj:ny, di:nx]
                m = a & b
                rows.append(ia[m]); cols.append(ib[m]); wts.append(np.full(int(m.sum()), wt))
            r = np.concatenate(rows); c = np.concatenate(cols); w = np.concatenate(wts)
            self._graph = csr_matrix((np.concatenate([w, w]), (np.concatenate([r, c]), np.concatenate([c, r]))), shape=(ny * nx, ny * nx))
        return self._graph

    def route(self, src_cells, dst_cells):
        """shortest raster path from any src cell to any dst cell (lists of (i,j)); returns list of (x,y) or None"""
        src = [j * self.nx + i for i, j in src_cells if 0 <= i < self.nx and 0 <= j < self.ny]
        dst = [j * self.nx + i for i, j in dst_cells if 0 <= i < self.nx and 0 <= j < self.ny]
        if not src or not dst:
            return None
        g = self.graph()
        D, P, S = dijkstra(g, directed=False, indices=src, min_only=True, return_predecessors=True)
        best = min(dst, key=lambda k: D[k])
        if not np.isfinite(D[best]):
            return None
        path = [best]
        while P[path[-1]] >= 0:
            path.append(P[path[-1]])
        path.reverse()
        return [self.xy(k % self.nx, k // self.nx) for k in path]

    def seg_ok(self, x1, y1, x2, y2):
        S = ('C', x1, y1, x2, y2, self.w / 2)
        for T, g in self.shapes:
            if C.dist(S, T) < g + DESIGN_MARGIN - 1e-9:
                return False
        return True


def _dist_field(S, X, Y):
    if S[0] == 'R':
        dx = np.maximum(np.abs(X - S[1]) - S[3], 0); dy = np.maximum(np.abs(Y - S[2]) - S[4], 0)
        return np.hypot(dx, dy)
    x1, y1, x2, y2, r = S[1:6]
    ddx, ddy = x2 - x1, y2 - y1
    L2 = ddx * ddx + ddy * ddy
    t = np.clip(((X - x1) * ddx + (Y - y1) * ddy) / L2, 0, 1) if L2 > 0 else 0
    return np.hypot(X - x1 - t * ddx, Y - y1 - t * ddy) - r


def pull(router, pts):
    """string-pull a raster path with EXACT segment tests; endpoints are kept exactly"""
    out = [pts[0]]
    i = 0
    n = len(pts)
    while i < n - 1:
        j = n - 1
        while j > i + 1 and not router.seg_ok(pts[i][0], pts[i][1], pts[j][0], pts[j][1]):
            j -= 1
        if not router.seg_ok(pts[i][0], pts[i][1], pts[j][0], pts[j][1]):
            return None
        out.append(pts[j])
        i = j
    return out


def poly_len(p):
    return sum(math.hypot(p[k + 1][0] - p[k][0], p[k + 1][1] - p[k][1]) for k in range(len(p) - 1))


def route_exact(router, start, goal, src_extra=(), dst_extra=()):
    """route from exact point start to exact point goal (both own-net copper); raster cells around the ends are
    used as entry/exit, then the exact ends are re-attached and the polyline is pulled exactly"""
    si, sj = router.cell(*start)
    gi, gj = router.cell(*goal)
    src = [(si + a, sj + b) for a in (-1, 0, 1) for b in (-1, 0, 1)] + list(src_extra)
    dst = [(gi + a, gj + b) for a in (-1, 0, 1) for b in (-1, 0, 1)] + list(dst_extra)
    src = [c for c in src if 0 <= c[0] < router.nx and 0 <= c[1] < router.ny and router.free[c[1], c[0]]]
    dst = [c for c in dst if 0 <= c[0] < router.nx and 0 <= c[1] < router.ny and router.free[c[1], c[0]]]
    if not src or not dst:
        return None
    p = router.route(src, dst)
    if p is None:
        return None
    p = [start] + p + [goal]
    q = pull(router, p)
    if q is None:
        return None
    # drop zero-length
    r = [q[0]]
    for pt in q[1:]:
        if math.hypot(pt[0] - r[-1][0], pt[1] - r[-1][1]) > 1e-4:
            r.append(pt)
    return r


# ------------------------------------------------------------------ topologies
FIRST_VIA = {13: (35.625, 16.65), 14: (36.125, 16.65), 15: (38.35, 16.725)}
ROUTE_LAYER = {13: 'L3-SIG', 14: 'L4-SIG', 15: 'L4-SIG'}
REF = {13: 'R132', 14: 'R133', 15: 'R134'}


def chain(W, n):
    """ordered inner-layer route segments of Dn starting at its first via: list of (obj, (xa,ya), (xb,yb))"""
    L = ROUTE_LAYER[n]
    segs = [o for o in W.objs if o.kind == 'track' and o.net == 'D%d' % n and o.layer == L]
    cur = FIRST_VIA[n]
    out = []
    left = list(segs)
    while left:
        hit = None
        for o in left:
            a, b = (o.shape[1], o.shape[2]), (o.shape[3], o.shape[4])
            if math.hypot(a[0] - cur[0], a[1] - cur[1]) < 2e-3:
                hit = (o, a, b)
            elif math.hypot(b[0] - cur[0], b[1] - cur[1]) < 2e-3:
                hit = (o, b, a)
            if hit:
                break
        if not hit:
            break
        out.append(hit)
        left.remove(hit[0])
        cur = hit[2]
    return out


def stub_and_via(W, n):
    st = [o for o in W.objs if o.kind == 'track' and o.net == 'D%d' % n and o.layer == 'Bottom']
    v = W.find_via('D%d' % n, *FIRST_VIA[n])
    return st, v[0].uid


def add_poly(c, net, layer, w, pts):
    for k in range(len(pts) - 1):
        c.add_track(net, layer, w, pts[k][0], pts[k][1], pts[k + 1][0], pts[k + 1][1])


def column_spec(side, L):
    if side == 'Top':
        sp = [('Top', 'L2-GND', 0.30), ('L2-GND', 'L3-SIG', 0.30)]
        if L == 'L4-SIG':
            sp.append(('L3-SIG', 'L4-SIG', 0.27))
    else:
        sp = [('L5-VCC3V3', 'Bottom', 0.30), ('L4-SIG', 'L5-VCC3V3', 0.30)]
        if L == 'L3-SIG':
            sp.append(('L3-SIG', 'L4-SIG', 0.27))
    return sp


def local_box(pts, box, m=1.2):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return (max(box[0], min(xs) - m), max(box[1], min(ys) - m), min(box[2], max(xs) + m), min(box[3], max(ys) + m))


def build_BF(W, n, x, y, rot, box, wf=0.10, wr=0.10, order=0, pre=None):
    """Bottom fold: R on Bottom, stub removed, feed U3 pad -> pad1, return pad2 -> existing first via (Bottom)"""
    c = Cand(W, n)
    if pre:
        pre(c)
    st, vuid = stub_and_via(W, n)
    for o in st:
        c.remove_track(o)
    c.renet_u3()
    c.add_part(REF[n], 'Bottom', x, y, rot)
    p1, p2 = r_pads(x, y, rot)
    u3 = W.pad_obj('U3', str(C.DPIN[n]), 'Bottom').xy
    via = FIRST_VIA[n]
    legs = [('SDRAM-D%d' % n, wf, u3, p1), ('D%d' % n, wr, p2, via)]
    if order:
        legs.reverse()
    for net, w, a, b in legs:
        R = Router(c, 'Bottom', net, w, box)
        p = route_exact(R, a, b)
        if p is None:
            return None, 'no route %s' % net
        add_poly(c, net, 'Bottom', w, p)
    c.topology = 'BF'
    return c, None


def build_XF(W, n, side, x, y, rot, box, wf=None, wi=0.125, pre=None, col_at=None, wcol=None):
    """F-type: stub + first via become SDRAM-Dn; side-layer track via -> pad1; pad2 (or a column reached from pad2 by
    a short side-layer track) drops through a microvia column to the route layer and re-joins the route at K; the
    route from the via to K is removed (no SDRAM-side stub left on the inner layer)."""
    L = ROUTE_LAYER[n]
    c = Cand(W, n)
    if pre:
        pre(c)
    st, vuid = stub_and_via(W, n)
    for o in st:
        c.rename_track(o, 'SDRAM-D%d' % n)
    c.rename_via(vuid, 'SDRAM-D%d' % n)
    c.relabel[vuid] = 'SDRAM-D%d' % n
    for o in st:
        c.removed.add(o.uid)
    c.removed.add(vuid)
    c.renet_u3()
    c.add_part(REF[n], side, x, y, rot)
    p1, p2 = r_pads(x, y, rot)
    via = FIRST_VIA[n]
    wf = wf or (0.0762 if side == 'Top' else 0.10)
    col = col_at or p2
    for a, b, sz in column_spec(side, L):
        c.add_via('D%d' % n, col[0], col[1], sz, 0.15, a, b)
    # inner re-join
    ch = chain(W, n)
    # inner route segments are own-net (not obstacles); the renamed via is
    R3 = Router(c, L, 'D%d' % n, wi, local_box([col], box, 1.6))
    dst = []
    vx, vy = via
    for k, (o, a, b) in enumerate(ch):
        Lg = math.hypot(b[0] - a[0], b[1] - a[1])
        m = max(2, int(Lg / (GRID / 2)))
        for s in range(m + 1):
            t = s / m
            px, py = a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])
            if math.hypot(px - vx, py - vy) < 0.175 + 0.10 + wi / 2 + 0.03:
                continue
            i, j = R3.cell(px, py)
            if 0 <= i < R3.nx and 0 <= j < R3.ny:
                dst.append((i, j, k, t))
    if not dst:
        return None, 'route outside window'
    ci, cj = R3.cell(*col)
    src = [(ci + a, cj + b) for a in (-1, 0, 1) for b in (-1, 0, 1)]
    src = [s for s in src if 0 <= s[0] < R3.nx and 0 <= s[1] < R3.ny and R3.free[s[1], s[0]]]
    dfree = [d for d in dst if R3.free[d[1], d[0]]]
    if not src or not dfree:
        return None, 'column or route cells blocked on %s' % L
    pth = R3.route(src, [(d[0], d[1]) for d in dfree])
    if pth is None:
        return None, 'no inner route column->K on %s' % L
    end = pth[-1]
    # nearest route point to the reached cell -> K (exact, on the polyline)
    best = None
    for k, (o, a, b) in enumerate(ch):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dy * dy
        t = max(0.0, min(1.0, ((end[0] - a[0]) * dx + (end[1] - a[1]) * dy) / L2))
        px, py = a[0] + t * dx, a[1] + t * dy
        d = math.hypot(px - end[0], py - end[1])
        if best is None or d < best[0]:
            best = (d, k, t, (px, py))
    _, ks, ts, K = best
    K = (round(K[0], 4), round(K[1], 4))
    pts = [col] + pth + [K]
    q = pull(R3, pts)
    if q is None:
        return None, 'inner pull failed'
    # remove route segments 0..ks, re-add remainder of segment ks from K
    for k in range(ks + 1):
        c.remove_track(ch[k][0])
        c.removed.add(ch[k][0].uid)
    o, a, b = ch[ks]
    if math.hypot(b[0] - K[0], b[1] - K[1]) > 1e-4:
        c.add_track('D%d' % n, L, o.rec['w'], K[0], K[1], b[0], b[1])
    q2 = [q[0]]
    for pt in q[1:]:
        if math.hypot(pt[0] - q2[-1][0], pt[1] - q2[-1][1]) > 1e-4:
            q2.append(pt)
    add_poly(c, 'D%d' % n, L, wi, q2)
    R = Router(c, side, 'SDRAM-D%d' % n, wf, local_box([via, p1], box))
    p = route_exact(R, via, p1)
    if p is None:
        return None, 'no side route via->pad1'
    add_poly(c, 'SDRAM-D%d' % n, side, wf, p)
    if col_at:
        R2 = Router(c, side, 'D%d' % n, wcol or wf, local_box([p2, col], box, 0.6))
        q = route_exact(R2, p2, col)
        if q is None:
            return None, 'no side route pad2->column'
        add_poly(c, 'D%d' % n, side, wcol or wf, q)
    c.topology = 'XF-%s' % side
    c.K = K
    return c, None


# ------------------------------------------------------------------ unlock: U2-47 GND re-route (non-critical copper)
GND47_RM = [((38.175, 17.125), (38.175, 18.2)), ((38.175, 18.2), (38.35, 18.4))]


def gnd47_tracks(W):
    out = []
    for a, b in GND47_RM:
        hit = [o for o in W.objs if o.kind == 'track' and o.layer == 'Top' and o.net == 'GND' and
               ((abs(o.shape[1] - a[0]) < 2e-3 and abs(o.shape[2] - a[1]) < 2e-3 and abs(o.shape[3] - b[0]) < 2e-3 and abs(o.shape[4] - b[1]) < 2e-3) or
                (abs(o.shape[3] - a[0]) < 2e-3 and abs(o.shape[4] - a[1]) < 2e-3 and abs(o.shape[1] - b[0]) < 2e-3 and abs(o.shape[2] - b[1]) < 2e-3))]
        assert len(hit) == 1, (a, b, hit)
        out.append(hit[0])
    return out


def make_gnd47(site, w=0.18):
    """pre-delta: cut U2-47's Top GND run to the through via (38.35,18.4) after (38.175,17.125) and give U2-47 its own
    Top>L2 GND microvia at `site` (short Top track from (38.175,17.125))."""
    def pre(c):
        for o in gnd47_tracks(c.W):
            c.remove_track(o)
        c.add_via('GND', site[0], site[1], 0.30, 0.15, 'Top', 'L2-GND')
        if abs(site[0] - 38.175) > 1e-4 or abs(site[1] - 17.125) > 1e-4:
            c.add_track('GND', 'Top', w, 38.175, 17.125, site[0], site[1])
        c.notes.append('unlock GND47: U2-47 Top GND run (38.175,17.125)-(38.175,18.2)-(38.35,18.4) removed; Top>L2 GND microvia at (%.3f,%.3f)' % site)
    return pre


# ------------------------------------------------------------------ rebuild a Cand from self-contained records
LIN = {'Top Layer': 'Top', 'Bottom Layer': 'Bottom', 'Top': 'Top', 'Bottom': 'Bottom', 'L2-GND': 'L2-GND', 'L3-SIG': 'L3-SIG',
       'L4-SIG': 'L4-SIG', 'L5-VCC3V3': 'L5-VCC3V3'}


def cand_from_recs(W, recs):
    """union of several candidate deltas (each the 'rec' of a candidate) as one Cand; raises if a removal is unmatched
    or removed twice (=> the candidates are incompatible)"""
    c = Cand(W, None)
    for rec in recs:
        for t in rec['remove']:
            L = LIN[t['layer']]
            hit = [o for o in W.objs if o.kind == 'track' and o.layer == L and o.net == t['net'] and
                   ((abs(o.shape[1] - t['x1']) < 2e-3 and abs(o.shape[2] - t['y1']) < 2e-3 and abs(o.shape[3] - t['x2']) < 2e-3 and abs(o.shape[4] - t['y2']) < 2e-3) or
                    (abs(o.shape[3] - t['x1']) < 2e-3 and abs(o.shape[4] - t['y1']) < 2e-3 and abs(o.shape[1] - t['x2']) < 2e-3 and abs(o.shape[2] - t['y2']) < 2e-3))]
            if len(hit) != 1:
                raise ValueError('removal unmatched %s' % t)
            if hit[0].uid in c.removed:
                raise ValueError('removed twice %s' % t)
            c.removed.add(hit[0].uid)
        for v in rec['remove_vias']:
            sp = span(LIN[v['span'][0]], LIN[v['span'][-1]])
            hit = [o for o in W.objs if o.kind == 'via' and abs(o.xy[0] - v['x']) < 2e-3 and abs(o.xy[1] - v['y']) < 2e-3 and o.span == sp]
            if not hit:
                raise ValueError('via removal unmatched %s' % v)
            if hit[0].uid in c.removed:
                raise ValueError('via removed twice %s' % v)
            for o in hit:
                c.removed.add(o.uid)
        for t in rec['tracks']:
            L = LIN[t['layer']]
            c.new.append(dict(kind='track', layer=L, net=t['net'], w=t['w'], shape=('C', t['x1'], t['y1'], t['x2'], t['y2'], t['w'] / 2)))
        for v in rec['vias']:
            sp = span(LIN[v['from']], LIN[v['to']])
            for L in sp:
                c.new.append(dict(kind='via', layer=L, net=v['net'], shape=('C', v['x'], v['y'], v['x'], v['y'], v['size'] / 2), hole=v['hole'], span=sp, xy=(v['x'], v['y'])))
        for p in rec['parts']:
            for k in ('1', '2'):
                pd = p['pad' + k]
                c.new.append(dict(kind='pad', layer=p['side'], net=pd['net'], shape=('R', pd['x'], pd['y'], 0.15, 0.15), ref=p['ref'], pad=k, xy=(pd['x'], pd['y'])))
        for rp in rec['renet_pads']:
            o = [q for q in W.objs if q.kind == 'pad' and q.ref == rp['ref'] and q.pad == rp['pad']]
            for q in o:
                c.relabel[q.uid] = rp['net']
        for k in rec:
            c.rec[k] = c.rec.get(k, []) + list(rec[k]) if isinstance(rec[k], list) else rec[k]
    return c


def joint_verify(W, recs, margin=0.0):
    try:
        c = cand_from_recs(W, recs)
    except ValueError as e:
        return ['incompatible: %s' % e], {}
    v, w = c.verify(margin=margin)
    hard = []
    for rec in recs:
        for p in rec['parts']:
            others = [r for r in recs if r is not rec]
    # bodies between the new parts themselves
    parts = [p for rec in recs for p in rec['parts']]
    for i, a in enumerate(parts):
        for b in parts[i + 1:]:
            if a['side'] != b['side']:
                continue
            ba = body_box(a); bb = body_box(b)
            if min(ba[2], bb[2]) - max(ba[0], bb[0]) > 1e-6 and min(ba[3], bb[3]) - max(ba[1], bb[1]) > 1e-6:
                v.append(('body', a['ref'], b['ref']))
    return v, w


def body_box(p):
    horiz = p['rot'] % 180 == 0
    x, y = p['x'], p['y']
    return [x - 0.315, y - 0.165, x + 0.315, y + 0.165] if horiz else [x - 0.165, y - 0.315, x + 0.165, y + 0.315]
