"""candidate builder + fast exact pre-check (engine.py geometry).  A candidate that passes here still has to pass
check.py (fullcheck.py) before it is called legal."""
import math, collections, json
import numpy as np
import engine as E
C = E.C
B = E.B
CU = E.CU

U1_BODY = (41.4, 6.9, 51.4, 16.9)
VIS_TEXT = {s: [t for t in B['texts'] if t['layer'] == s and not t['hidden']] for s in ('TopOverlay', 'BottomOverlay')}
SIDE_OF = {c['ref']: c['side'] for c in B['components']}
ABOX = {}
for ref, v in B['component_outlines'].items():
    if ref == 'X2':
        continue
    bxs = [v[k] for k in v if k in ('pads', 'Mech3', 'Mech4', 'Mech8', 'Mech3(region)', 'Mech4(region)', 'Mech8(region)')]
    if bxs:
        ABOX[ref] = (SIDE_OF.get(ref), [min(b_[0] for b_ in bxs), min(b_[1] for b_ in bxs), max(b_[2] for b_ in bxs), max(b_[3] for b_ in bxs)])
for pr in E.ulib.P13['parts']:
    xs = [pr['pad1']['x'], pr['pad2']['x']]; ys = [pr['pad1']['y'], pr['pad2']['y']]
    ABOX[pr['ref']] = (pr['side'], [min(xs) - 0.15, min(ys) - 0.15, max(xs) + 0.15, max(ys) + 0.15])


def rr(a, b):
    dx = max(0.0, max(a[0], b[0]) - min(a[2], b[2]))
    dy = max(0.0, max(a[1], b[1]) - min(a[3], b[3]))
    return math.hypot(dx, dy)


def fam_split(n, fam):
    """kept family records with their side ('S' = SDRAM-Dn, 'D' = Dn) and removed records, per family"""
    N = E.NETS[n]
    ts, vs, ps = E.fam_records(n)
    poly = N['poly']
    zone_from = N['last_from']
    zone_to = len(poly) - 1
    if fam == 'F5':
        zone_from, zone_to = 0, N['first_to']
    inner = N['inner']

    def in_zone(t):
        if t['layer'] != inner:
            return False
        for k in range(zone_from, zone_to):
            a, b = poly[k], poly[k + 1]
            if (E.same(a, (t['x1'], t['y1'])) and E.same(b, (t['x2'], t['y2']))) or (E.same(b, (t['x1'], t['y1'])) and E.same(a, (t['x2'], t['y2']))):
                return True
        return False
    rm_t, rm_v, keep = [], [], []
    v2 = [v for v in vs if E.same((v['x'], v['y']), N['v2'])][0]
    for t in ts:
        top = t['layer'] == 'Top'
        if fam == 'F1':
            (rm_t if top else keep).append(t) if top else keep.append((t, 'S'))
        elif fam == 'F2a':
            if top or in_zone(t):
                rm_t.append(t)
            else:
                keep.append((t, 'S'))
        elif fam == 'F5':
            if in_zone(t):
                rm_t.append(t)
            elif t['layer'] == 'Bottom':
                keep.append((t, 'S'))
            else:
                keep.append((t, 'D'))
        elif fam in ('F2b', 'F4', 'F3T', 'F3B'):
            if in_zone(t):
                rm_t.append(t)
            elif top:
                keep.append((t, 'D'))
            else:
                keep.append((t, 'S'))
    for v in vs:
        isv2 = v is v2
        if fam == 'F1':
            keep.append((v, 'S'))
        elif fam == 'F2a':
            if isv2:
                rm_v.append(v)
            else:
                keep.append((v, 'S'))
        else:
            keep.append((v, 'D' if isv2 else 'S'))
    for p in ps:
        keep.append((p, 'D' if p['ref'] == 'U1' else 'S'))
    # F1: the Top chain went into keep by mistake above if any; normalise
    if fam == 'F1':
        rm_t = [t for t in ts if t['layer'] == 'Top']
        keep = [(r, s) for r, s in keep if not (r in rm_t)]
    s_zone = E.poly_len(poly[:zone_from + 1])
    return dict(rm_t=rm_t, rm_v=rm_v, keep=keep, v2=v2, s_zone=s_zone, L=E.poly_len(poly))


def rec_objs(rec, net):
    if 'x1' in rec:
        t = dict(rec, net=net)
        return [E.track_obj(t)]
    if 'span' in rec:
        v = dict(rec, net=net)
        return E.via_objs(v)
    p = dict(rec, net=net)
    layers = CU if p['layer'] == 'Multi' else [p['layer']]
    return [C.O('pad', L, net, C.pad_shape(p, L), p, 'pad %s-%s' % (p['ref'], p['pad']), ('kp', p['ref'], p['pad']), new=False,
                span=layers, xy=(p['x'], p['y']), ref=p['ref'], pad=p['pad']) for L in layers]


class Ctx:
    """per (net, family, window) cached static rasters"""
    def __init__(s, n, fam, win):
        s.n, s.fam = n, fam
        s.W = E.Win(*win)
        s.ign = lambda q, n=n: E.is_fam(q.net, n)
        s.cache = {}

    def blocked(s, layer, net, r):
        k = (layer, net in E.SDRAM_ALL, round(r, 4))
        if k not in s.cache:
            s.cache[k] = E.static_block(s.W, layer, net, r, (), exclude=s.ign)
        return s.cache[k]


def route2(ctx, layer, net, w, start, goal, extra):
    """route with cached static raster + stamped extras"""
    W = ctx.W
    base = ctx.blocked(layer, net, w / 2 + 0.004)
    M = base.copy()
    for q in extra:
        if q.layer != layer or q.net == net:
            continue
        E.stamp_block(W, M, q.shape, E.gap_nets(net, q.net, layer, None, q.ref) + w / 2 + 0.004)
    si, sj = W.ij(*start)
    if not (0 <= si < W.nx and 0 <= sj < W.ny):
        return None
    M[sj, si] = False
    X, Y = np.meshgrid(W.xs, W.ys)
    G = np.zeros_like(M)
    if goal['kind'] == 'point':
        G = np.hypot(X - goal['xy'][0], Y - goal['xy'][1]) <= goal['r']
    elif goal['kind'] == 'shapes':
        for S in goal['shapes']:
            sh = S if S[0] == 'R' else ('C',) + tuple(S[1:5]) + (max(S[5] - w / 2, 0.0),)
            G |= E.shape_dist_grid(W, sh) <= 1e-9
    else:
        pts = goal['pts']
        sacc = 0.0
        for k in range(len(pts) - 1):
            (x1, y1), (x2, y2) = pts[k], pts[k + 1]
            L = math.hypot(x2 - x1, y2 - y1)
            t = np.clip(((X - x1) * (x2 - x1) + (Y - y1) * (y2 - y1)) / (L * L), 0, 1)
            d = np.hypot(X - x1 - t * (x2 - x1), Y - y1 - t * (y2 - y1))
            sv = sacc + t * L
            G |= (d <= E.RR * 0.75) & (sv >= goal['s_lo']) & (sv <= goal['s_hi'])
            sacc += L
    M &= ~G
    if not G.any():
        return None
    path = E.astar(M, (si, sj), G, max_nodes=250000)
    if path is None:
        return None
    pts = [start] + [W.xy(i, j) for i, j in path[1:]]
    attach = None
    if goal['kind'] == 'point':
        pts.append(goal['xy'])
    elif goal['kind'] == 'poly':
        attach = E.project_poly(goal['pts'], *pts[-1])
        pts.append(attach[1])
    out = [pts[0]]
    i = 0
    while i < len(pts) - 1:
        j = len(pts) - 1
        while j > i + 1 and not E.seg_clear(layer, net, w, pts[i], pts[j], extra, ctx.ign):
            j -= 1
        out.append(pts[j])
        i = j
    o2 = [out[0]]
    for p in out[1:]:
        if math.hypot(p[0] - o2[-1][0], p[1] - o2[-1][1]) > 1e-6:
            o2.append((round(p[0], 4), round(p[1], 4)))
    o2[0] = (round(o2[0][0], 4), round(o2[0][1], 4))
    if len(o2) < 2:
        o2.append(o2[0])
    return o2, attach


def tracks_from(pts, layer, net, w, why):
    return [dict(layer=layer, net=net, w=w, x1=pts[k][0], y1=pts[k][1], x2=pts[k + 1][0], y2=pts[k + 1][1], why=why)
            for k in range(len(pts) - 1) if math.hypot(pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1]) > 1e-6]


def build(ctx, side, x, y, rot, w_inner=E.W_INNER):
    """returns (cand, None) or (None, reason)"""
    n, fam = ctx.n, ctx.fam
    N = E.NETS[n]
    SN, DN = 'SDRAM-D%d' % n, 'D%d' % n
    ref = E.REF[n]
    p1, p2 = E.pad_xy(x, y, rot)
    sp = fam_split(n, fam)
    w_out = E.W_OUTER if side == 'Top' else E.W_BOT
    # kept family objects with their final nets
    kept_objs = []
    for rec, s in sp['keep']:
        kept_objs += rec_objs(rec, SN if s == 'S' else DN)
    pad1 = E.pad_obj(side, SN, p1, ref, '1')
    pad2 = E.pad_obj(side, DN, p2, ref, '2')
    new_v, new_t = [], []
    new_objs = [pad1, pad2]
    inner = N['inner']
    poly = N['poly']
    zpts = poly[N['last_from']:]

    def extra_for(net):
        return [o for o in kept_objs + new_objs if o.net != net]
    try:
        if fam == 'F1':
            r1 = route2(ctx, side, SN, w_out, p1, dict(kind='point', xy=N['v2'], r=0.175 - w_out / 2 - 0.01), extra_for(SN))
            if r1 is None:
                return None, 'pad1->V2 Top route'
            t1 = tracks_from(r1[0], side, SN, w_out, 'new')
            new_t += t1; new_objs += [E.track_obj(t) for t in t1]
            r2 = route2(ctx, side, DN, w_out, p2, dict(kind='point', xy=N['ballxy'], r=0.1125 - 0.01), extra_for(DN))
            if r2 is None:
                return None, 'pad2->ball Top route'
            t2 = tracks_from(r2[0], side, DN, w_out, 'new')
            new_t += t2; new_objs += [E.track_obj(t) for t in t2]
        elif fam in ('F2a', 'F2b', 'F4'):
            col = E.column(side, inner, p1, SN)
            new_v += col
            for v in col:
                new_objs += E.via_objs(v)
            # inner: column -> poly zone (SDRAM piece kept from zone start to attach)
            r1 = route2(ctx, inner, SN, w_inner, p1, dict(kind='poly', pts=zpts, s_lo=0.0, s_hi=E.poly_len(zpts) - 0.45), extra_for(SN))
            if r1 is None:
                return None, 'column1->inner run route'
            s1 = r1[1][0]
            pa, _ = E.poly_cut(zpts, s1)
            piece = tracks_from(pa, inner, SN, 0.125, 'keep-piece') if len(pa) > 1 else []
            ti = tracks_from(r1[0], inner, SN, w_inner, 'new')
            new_t += piece + ti
            new_objs += [E.track_obj(t) for t in piece + ti]
            if fam == 'F2a':
                goal = dict(kind='point', xy=N['ballxy'], r=0.1125 - 0.01)
            elif fam == 'F2b':
                goal = dict(kind='shapes', shapes=[o.shape for o in kept_objs if o.net == DN and o.layer == 'Top'])
            else:
                goal = dict(kind='point', xy=N['v2'], r=0.175 - w_out / 2 - 0.01)
            r2 = route2(ctx, side, DN, w_out, p2, goal, extra_for(DN))
            if r2 is None:
                return None, 'pad2 outer route'
            t2 = tracks_from(r2[0], side, DN, w_out, 'new')
            new_t += t2; new_objs += [E.track_obj(t) for t in t2]
        elif fam == 'F5':
            zp = poly[:N['first_to'] + 1]
            r1 = route2(ctx, side, SN, w_out, p1, dict(kind='point', xy=N['v1'], r=0.175 - w_out / 2 - 0.01), extra_for(SN))
            if r1 is None:
                return None, 'pad1->first via Top route'
            t1 = tracks_from(r1[0], side, SN, w_out, 'new')
            new_t += t1; new_objs += [E.track_obj(t) for t in t1]
            c2 = E.column(side, inner, p2, DN)
            new_v += c2
            for v in c2:
                new_objs += E.via_objs(v)
            r2 = route2(ctx, inner, DN, w_inner, p2, dict(kind='poly', pts=zp, s_lo=0.45, s_hi=E.poly_len(zp)), extra_for(DN))
            if r2 is None:
                return None, 'column2->inner run (U1 side)'
            s2 = r2[1][0]
            _, pb = E.poly_cut(zp, s2)
            piece_b = tracks_from(pb, inner, DN, 0.125, 'keep-piece') if len(pb) > 1 else []
            t2 = tracks_from(r2[0], inner, DN, w_inner, 'new')
            new_t += piece_b + t2
            new_objs += [E.track_obj(t) for t in piece_b + t2]
        elif fam in ('F3T', 'F3B'):
            c1 = E.column(side, inner, p1, SN)
            c2 = E.column(side, inner, p2, DN)
            new_v += c1 + c2
            for v in c1 + c2:
                new_objs += E.via_objs(v)
            Lz = E.poly_len(zpts)
            sc = E.project_poly(zpts, x, y)[0]
            r1 = route2(ctx, inner, SN, w_inner, p1, dict(kind='poly', pts=zpts, s_lo=0.0, s_hi=max(0.0, sc - 0.05)), extra_for(SN))
            if r1 is None:
                return None, 'column1->inner run (U3 side)'
            s1 = r1[1][0]
            pa, _ = E.poly_cut(zpts, s1)
            piece_a = tracks_from(pa, inner, SN, 0.125, 'keep-piece') if len(pa) > 1 else []
            ti = tracks_from(r1[0], inner, SN, w_inner, 'new')
            new_t += piece_a + ti
            new_objs += [E.track_obj(t) for t in piece_a + ti]
            r2 = route2(ctx, inner, DN, w_inner, p2, dict(kind='poly', pts=zpts, s_lo=s1 + 0.35, s_hi=Lz), extra_for(DN))
            if r2 is None:
                return None, 'column2->inner run (U1 side)'
            s2 = r2[1][0]
            _, pb = E.poly_cut(zpts, s2)
            piece_b = tracks_from(pb, inner, DN, 0.125, 'keep-piece') if len(pb) > 1 else []
            t2 = tracks_from(r2[0], inner, DN, w_inner, 'new')
            new_t += piece_b + t2
            new_objs += [E.track_obj(t) for t in piece_b + t2]
    except Exception as ex:  # noqa
        return None, 'exception %r' % ex
    cand = dict(net=n, fam=fam, side=side, x=round(x, 4), y=round(y, 4), rot=rot, ref=ref, p1=p1, p2=p2,
                rm_t=sp['rm_t'], rm_v=sp['rm_v'], keep=sp['keep'], add_t=new_t, add_v=new_v, w_inner=w_inner)
    return cand, None


# --------------------------------------------------------------------------- exact fast check
def cand_objs(c):
    n = c['net']
    SN, DN = 'SDRAM-D%d' % n, 'D%d' % n
    kept = []
    for rec, s in c['keep']:
        kept += rec_objs(rec, SN if s == 'S' else DN)
    new = [E.pad_obj(c['side'], SN, c['p1'], c['ref'], '1'), E.pad_obj(c['side'], DN, c['p2'], c['ref'], '2')]
    for t in c['add_t']:
        new.append(E.track_obj(t))
    for v in c['add_v']:
        new += E.via_objs(v)
    return kept, new


def fast_check(c, others=()):
    """exact checks of the candidate's new + renamed objects against the static board, the family and `others`
    (objects of other candidates, for joint plans).  Returns dict(ok, hard=[...], soft=[...], margins)."""
    n = c['net']
    ign = lambda q: E.is_fam(q.net, n)
    kept, new = cand_objs(c)
    SN = 'SDRAM-D%d' % n
    hard, soft = [], []
    worst = {}
    fam_all = kept + new
    check_set = [o for o in kept if o.net == SN] + new   # renamed + new
    for o in check_set:
        bb = C.bbox(o.shape)
        cands = [q for q in E.SG.near(o.layer, bb, 0.4) if not ign(q)] + [q for q in fam_all + list(others) if q.layer == o.layer and q is not o]
        for q in cands:
            if q.net == o.net:
                continue
            g = E.gap_nets(o.net, q.net, o.layer, o.ref, q.ref)
            d = C.dist(o.shape, q.shape)
            m = d - g
            k = 'clr ' + o.layer
            if k not in worst or m < worst[k][0]:
                worst[k] = (round(m, 4), o.tag, q.tag)
            if m < -1e-6:
                hard.append('clearance %s %.4f<%.3f %s vs %s' % (o.layer, d, g, o.tag, q.tag))
    # hole to hole
    newd = [((v['x'], v['y']), v['hole'], set(v['span']), v['net']) for v in c['add_v']]
    famd = [((r['x'], r['y']), r['hole'], set(r['span']), r['net']) for r, s in c['keep'] if 'span' in r and 'x1' not in r]
    od = []
    for o in others:
        if o.kind == 'via' and o.layer == o.span[0]:
            od.append((o.xy, o.hole, set(o.span), o.net))
    for a in newd:
        pool = [d for d in E.drills_near(a[0][0], a[0][1], 1.0) if not E.is_fam(d[3], n)] + famd + od + [b for b in newd if b is not a]
        for b in pool:
            if E.same(a[0], b[0], 1e-4):
                continue
            if not (a[2] & b[2]):
                continue
            d = math.hypot(a[0][0] - b[0][0], a[0][1] - b[0][1]) - a[1] / 2 - b[1] / 2
            k = 'h2h'
            if k not in worst or d - 0.24 < worst[k][0]:
                worst[k] = (round(d - 0.24, 4), str(a[0]), str(b[0]))
            if d < 0.24 - 1e-6:
                hard.append('hole-to-hole %.4f %s vs %s' % (d, a[0], b[0]))
    # mask sliver / merge: new pads vs other pads on the side
    side = c['side']
    for o in new[:2]:
        mo = C.grow(o.shape, 0.05)
        for q in list(E.SG.near(side, C.bbox(mo), 0.5)) + [p for p in others if p.kind == 'pad'] + new[:2]:
            if q is o or q.kind != 'pad' or q.layer != side:
                continue
            if q.ref == o.ref:
                continue
            mq = C.grow(q.shape, C.mask_exp(q))
            d = C.dist(mo, mq)
            k = 'mask'
            if k not in worst or d - 0.10 < worst[k][0]:
                worst[k] = (round(d - 0.10, 4), o.tag, q.tag)
            if d < 0.10 - 1e-6:
                hard.append('mask web %.4f %s vs %s' % (d, o.tag, q.tag))
        # vias whose land reaches into the opening
        for q in list(E.SG.near(side, C.bbox(mo), 0.5)) + [v for v in fam_all if v.kind == 'via' and v.layer == side] + [v for v in others if v.kind == 'via' and v.layer == side]:
            if q.kind != 'via' or q.layer != side or (ign(q) and q not in fam_all):
                continue
            if C.dist(mo, q.shape) > 0:
                continue
            inside = all(C.in_rect(q.xy[0] + dx, q.xy[1] + dy, o.shape[1:], 1e-6) for dx, dy in
                         ((q.hole / 2, 0), (-q.hole / 2, 0), (0, q.hole / 2), (0, -q.hole / 2)))
            if q.net != o.net:
                hard.append('other-net via land in opening %s %s' % (o.tag, q.tag))
            elif len(q.span) == 6:
                hard.append('through via land in pad opening %s %s' % (o.tag, q.tag))
            elif not inside:
                hard.append('microvia not fully in pad %s %s' % (o.tag, q.tag))
    # U1 body (Top) and component clearance
    horiz = c['rot'] in (0, 180)
    body = [c['x'] - 0.315, c['y'] - 0.165, c['x'] + 0.315, c['y'] + 0.165] if horiz else [c['x'] - 0.165, c['y'] - 0.315, c['x'] + 0.165, c['y'] + 0.315]
    pbox = [min(c['p1'][0], c['p2'][0]) - 0.15, min(c['p1'][1], c['p2'][1]) - 0.15, max(c['p1'][0], c['p2'][0]) + 0.15, max(c['p1'][1], c['p2'][1]) + 0.15]
    if side == 'Top':
        gb = rr(body, U1_BODY)
        if gb <= 0:
            hard.append('R body under U1 body')
        worst['u1_body_gap'] = (round(gb, 4),)
    best = (9, None)
    for r2, (s2, b2) in ABOX.items():
        if s2 != side:
            continue
        d = rr(pbox, b2)
        if d < best[0]:
            best = (round(d, 4), r2)
    for o in others:
        if o.kind == 'pad' and o.layer == side and o.ref and o.ref != c['ref']:
            b2 = C.bbox(o.shape)
            d = rr(pbox, list(b2))
            if d < best[0]:
                best = (round(d, 4), o.ref)
    worst['comp_clear'] = best
    if best[0] < 0.254 - 1e-6:
        soft.append('ComponentClearance %.3f < 0.254 to %s' % best)
    # silk text vs pad openings and body
    sil = []
    for t in VIS_TEXT['TopOverlay' if side == 'Top' else 'BottomOverlay']:
        tb = C.text_box(t)
        for o in new[:2]:
            d = C.dist(tb, C.grow(o.shape, 0.05))
            if d < 0.254:
                sil.append((t['text'], round(d, 3)))
        bd = rr([tb[1] - tb[3], tb[2] - tb[4], tb[1] + tb[3], tb[2] + tb[4]], body)
        if bd <= 0:
            sil.append((t['text'], 'over body'))
    if sil:
        soft.append('silk %s' % sorted(set(map(str, sil))))
    worst['silk'] = sil
    # connectivity: exactly two islands, pads on the right side, no dangling ends
    uf = C.phys_islands(fam_all, net_aware=False)
    isl = collections.defaultdict(list)
    for k, o in enumerate(fam_all):
        isl[uf.f(k)].append(o)
    if len(isl) != 2:
        hard.append('family islands %d' % len(isl))
    for r, os_ in isl.items():
        nets = {o.net for o in os_}
        if len(nets) != 1:
            hard.append('island mixes nets %s' % nets)
    for o in new:
        if o.kind != 'track':
            continue
        for ex, ey in ((o.shape[1], o.shape[2]), (o.shape[3], o.shape[4])):
            P_ = ('C', ex, ey, ex, ey, 0.0)
            if not any(q is not o and q.net == o.net and q.layer == o.layer and C.dist(P_, q.shape) <= 1e-4 for q in fam_all):
                hard.append('dangling end %s (%.3f,%.3f)' % (o.tag, ex, ey))
    return dict(ok=not hard, hard=hard, soft=soft, worst=worst)


# --------------------------------------------------------------------------- plan delta in dq_series_r_plan format
def plan_delta(c):
    n = c['net']
    SN, DN = 'SDRAM-D%d' % n, 'D%d' % n
    d = dict(remove=[], remove_vias=[], tracks=[], vias=[], parts=[], renet_pads=[], microvias=[])
    for t in c['rm_t']:
        d['remove'].append(dict(net=t['net'], layer=E.EMIT[t['layer']], w=t['w'], x1=t['x1'], y1=t['y1'], x2=t['x2'], y2=t['y2']))
    for v in c['rm_v']:
        d['remove_vias'].append(dict(net=v['net'], x=v['x'], y=v['y'], hole=v['hole'], span=[v['span'][0], v['span'][-1]]))
    for rec, s in c['keep']:
        if s != 'S':
            continue
        if 'x1' in rec:
            d['remove'].append(dict(net=rec['net'], layer=E.EMIT[rec['layer']], w=rec['w'], x1=rec['x1'], y1=rec['y1'], x2=rec['x2'], y2=rec['y2'], why='rename'))
            d['tracks'].append(dict(net=SN, layer=E.EMIT[rec['layer']], w=rec['w'], x1=rec['x1'], y1=rec['y1'], x2=rec['x2'], y2=rec['y2'], why='rename'))
        elif 'span' in rec:
            d['remove_vias'].append(dict(net=rec['net'], x=rec['x'], y=rec['y'], hole=rec['hole'], span=[rec['span'][0], rec['span'][-1]], why='rename'))
            d['vias'].append(dict(net=SN, x=rec['x'], y=rec['y'], size=rec['size'], hole=rec['hole'], **{'from': E.EMIT[rec['span'][0]], 'to': E.EMIT[rec['span'][-1]]}, why='rename'))
        elif rec.get('ref') == 'U3':
            d['renet_pads'].append(dict(ref='U3', pad=rec['pad'], net=SN))
    for t in c['add_t']:
        d['tracks'].append(dict(net=t['net'], layer=E.EMIT[t['layer']], w=t['w'], x1=t['x1'], y1=t['y1'], x2=t['x2'], y2=t['y2']))
    for v in c['add_v']:
        vv = dict(net=v['net'], x=v['x'], y=v['y'], size=v['size'], hole=v['hole'], **{'from': E.EMIT[v['span'][0]], 'to': E.EMIT[v['span'][-1]]})
        d['vias'].append(vv)
        d['microvias'].append(dict(vv, type=('microvia 0.30/0.15' if v['size'] >= 0.29 else 'buried 0.27/0.15')))
    d['parts'].append(dict(ref=c['ref'], net_bit=n, side=c['side'], footprint='R0201', comment='22', x=c['x'], y=c['y'], rot=c['rot'],
                           pad1=dict(net=SN, x=round(c['p1'][0], 4), y=round(c['p1'][1], 4)),
                           pad2=dict(net=DN, x=round(c['p2'][0], 4), y=round(c['p2'][1], 4)), designator_hidden=True))
    return d


def merge_plan(base, deltas, note=''):
    P = json.loads(json.dumps(base))
    for d in deltas:
        for k in ('remove', 'remove_vias', 'tracks', 'vias', 'parts', 'renet_pads', 'microvias'):
            P[k] += d[k]
        for pr in d['parts']:
            sn = 'SDRAM-D%d' % pr['net_bit']
            if sn not in P['net_class_add']['SDRAM_DATA']:
                P['net_class_add']['SDRAM_DATA'].append(sn)
    rt = sum(1 for t in P['tracks'] if t.get('why') == 'rename'); rv = sum(1 for v in P['vias'] if v.get('why') == 'rename')
    P['renamed_existing'] = dict(tracks=rt, vias=rv)
    P['source'] = dict(P['source'], plan='13-resistor plan (dq_series_r_plan.json md5 f2949630) + ' + note,
                       generated_by='si/series_r/d13/u1_end')
    return P


# --------------------------------------------------------------------------- pairwise compatibility of two deltas
LIN = {'Top Layer': 'Top', 'Bottom Layer': 'Bottom', 'L2-GND': 'L2-GND', 'L3-SIG': 'L3-SIG', 'L4-SIG': 'L4-SIG',
       'L5-VCC3V3': 'L5-VCC3V3'}


def delta_objs(d):
    """O objects of everything a delta adds (incl. renamed copies) -- what can collide with another delta"""
    out = []
    for t in d['tracks']:
        out.append(E.track_obj(dict(t, layer=LIN[t['layer']])))
    for v in d['vias']:
        s0, s1 = CU.index(LIN[v['from']]), CU.index(LIN[v['to']])
        vv = dict(v, span=CU[min(s0, s1):max(s0, s1) + 1])
        out += E.via_objs(vv)
    for pr in d['parts']:
        out.append(E.pad_obj(pr['side'], pr['pad1']['net'], (pr['pad1']['x'], pr['pad1']['y']), pr['ref'], '1'))
        out.append(E.pad_obj(pr['side'], pr['pad2']['net'], (pr['pad2']['x'], pr['pad2']['y']), pr['ref'], '2'))
    return out


def removed_keys(d):
    return {(t['layer'], t['net'], round(t['x1'], 4), round(t['y1'], 4), round(t['x2'], 4), round(t['y2'], 4)) for t in d['remove']}


def pair_ok(da, db):
    """exact geometric compatibility of two deltas for DIFFERENT nets: clearance (rule by layer/net), hole-to-hole on
    shared spans, mask web between new pads, ComponentClearance between the two new parts, removal overlap.
    Objects that one delta removes and the other keeps are handled by check.py on the merged plan."""
    if removed_keys(da) & removed_keys(db):
        return False, 'both remove the same track'
    A, Bo = delta_objs(da), delta_objs(db)
    worst = 9.0
    for a in A:
        for b in Bo:
            if a.layer != b.layer or a.net == b.net:
                continue
            g = E.gap_nets(a.net, b.net, a.layer, a.ref, b.ref)
            d = C.dist(a.shape, b.shape)
            worst = min(worst, d - g)
            if d < g - 1e-6:
                return False, 'clearance %s %.4f %s / %s' % (a.layer, d, a.tag, b.tag)
            if a.kind == 'pad' and b.kind == 'pad':
                m = C.dist(C.grow(a.shape, 0.05), C.grow(b.shape, 0.05))
                if m < 0.10 - 1e-6:
                    return False, 'mask web %.4f' % m
    for a in A:
        if a.kind != 'via' or a.layer != a.span[0]:
            continue
        for b in Bo:
            if b.kind != 'via' or b.layer != b.span[0] or not (set(a.span) & set(b.span)):
                continue
            d = math.hypot(a.xy[0] - b.xy[0], a.xy[1] - b.xy[1]) - a.hole / 2 - b.hole / 2
            if d < 0.24 - 1e-6:
                return False, 'h2h %.4f' % d
    pa = [o for o in A if o.kind == 'pad']; pb = [o for o in Bo if o.kind == 'pad']
    if pa and pb and pa[0].layer == pb[0].layer:
        ba = [min(C.bbox(o.shape)[0] for o in pa), min(C.bbox(o.shape)[1] for o in pa), max(C.bbox(o.shape)[2] for o in pa), max(C.bbox(o.shape)[3] for o in pa)]
        bb = [min(C.bbox(o.shape)[0] for o in pb), min(C.bbox(o.shape)[1] for o in pb), max(C.bbox(o.shape)[2] for o in pb), max(C.bbox(o.shape)[3] for o in pb)]
        if rr(ba, bb) < 0.254 - 1e-6:
            return False, 'ComponentClearance %.3f' % rr(ba, bb)
    return True, round(worst, 4)
