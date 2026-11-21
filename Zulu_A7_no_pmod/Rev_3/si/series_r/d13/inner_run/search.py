"""Inner-run column search for D13 (L3), D14 (L4), D15 (L4).

For each net the R0201 sits on Top or Bottom over its own inner run.  Each pad holds a stacked column centred in the
pad (the D9/D12 patterns):
    Top    + L3 run : Top>L2 0.30/0.15, L2>L3 0.30/0.15                       (microvias)
    Top    + L4 run : Top>L2 0.30/0.15, L2>L3 0.30/0.15, L3>L4 0.27/0.15      (micro, micro, buried)
    Bottom + L4 run : L5>Bottom 0.30/0.15, L4>L5 0.30/0.15                    (microvias)
    Bottom + L3 run : L5>Bottom, L4>L5 0.30/0.15, L3>L4 0.27/0.15             (micro, micro, buried)
Each column is tied to the run by a straight 0.125 (or 0.10) connector on the run layer to its perpendicular foot on
the run; the run between the two feet is removed; pad 1 (U3 side) must be the one with the smaller arc length.

Search order (pruned by geometry first, spatial index everywhere, time-boxed per net):
  1. column SITES on a 0.025 mm grid in a band around the run: every land of the stack, the side pad, its mask
     opening and the drill(s) are tested exactly against the 13-R plan applied to the board (non-family copper);
  2. R placements = pairs of legal sites 0.60 mm apart (4 rotations);
  3. exact candidate check: connectors, split run pieces and the U3-side relabel against everything (family split
     included), component clearance (Altium 0.254 on the extract's boxes, section-10 bodies), visible silk.
Survivors are written to prefilter_<net>.json; the full check.py proof runs on them in prove.py.
"""
import sys, os, json, math, time, collections
import lib
from lib import C, B

T0 = time.time()
BUDGET = float(os.environ.get('NET_BUDGET_S', '900'))
STEP = float(os.environ.get('GRID', '0.025'))
BAND = float(os.environ.get('BAND', '1.0'))
NETS = sys.argv[1].split(',') if len(sys.argv) > 1 else ['D13', 'D14', 'D15']

objs, pads, tracks, vias, E = lib.apply_plan(lib.BASE_PLAN)
SDRAMX = C.SDRAM | C.SDRAM_NEW
G = C.Grid(objs, 0.5)

# drills of the base state (vias: one per via record; pads with holes)
DRILLS = []
for o in objs:
    if o.kind == 'via' and o.layer == o.span[0]:
        DRILLS.append((o.xy, o.hole, set(o.span), o.net))
for p in pads:
    if p.get('hole', 0) > 0:
        DRILLS.append(((p['x'], p['y']), p['hole'], set(CU := C.CU), p['net']))
DG = collections.defaultdict(list)
for d in DRILLS:
    DG[(int(d[0][0] // 0.5), int(d[0][1] // 0.5))].append(d)

side_of = {c['ref']: c['side'] for c in B['components']}
VIS = [t for t in B['texts'] if t['layer'] in ('TopOverlay', 'BottomOverlay') and not t['hidden']]
VIS_BOX = [(('Top' if t['layer'] == 'TopOverlay' else 'Bottom'), C.text_box(t), t['text']) for t in VIS]

# component boxes: section 14 (Altium-style, extract's pads/Mech3/4/8 union) and section 10 (bodies, U1/U3 special)
ABOX = {}
for ref, v in B['component_outlines'].items():
    if ref == 'X2':
        continue
    bxs = [v[k] for k in v if k in ('pads', 'Mech3', 'Mech4', 'Mech8', 'Mech3(region)', 'Mech4(region)', 'Mech8(region)')]
    if bxs:
        ABOX[ref] = (side_of.get(ref), [min(b[0] for b in bxs), min(b[1] for b in bxs), max(b[2] for b in bxs), max(b[3] for b in bxs)])
BBOX10 = {}
for ref, v in B['component_outlines'].items():
    if ref == 'X2':
        continue
    bx = [v[k] for k in ('pads', 'Mech3', 'Mech4', 'Mech3(region)', 'Mech4(region)') if k in v]
    if ref == 'U3':
        m = B['u3']['body']['max']
        bx.append([m['x0'], m['y0'], m['x1'], m['y1']])
    if ref == 'U1':
        bx = [v['pads'], [41.4, 6.9, 51.4, 16.9]]
    if bx:
        BBOX10[ref] = (side_of.get(ref), bx)
MECH7 = {ref: (side_of.get(ref), v['Mech7']) for ref, v in B['component_outlines'].items() if 'Mech7' in v}
# the 13 plan resistors (pads bbox) take part in component clearance too
for pr in json.load(open(lib.BASE_PLAN))['parts']:
    xs = [pr['pad1']['x'], pr['pad2']['x']]; ys = [pr['pad1']['y'], pr['pad2']['y']]
    bb = [min(xs) - 0.15, min(ys) - 0.15, max(xs) + 0.15, max(ys) + 0.15]
    ABOX[pr['ref']] = (pr['side'], bb)
    BBOX10[pr['ref']] = (pr['side'], [bb])


def rr(a, b):
    return C.d_rect_rect(((a[0] + a[2]) / 2, (a[1] + a[3]) / 2, (a[2] - a[0]) / 2, (a[3] - a[1]) / 2),
                         ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, (b[2] - b[0]) / 2, (b[3] - b[1]) / 2))


RUNL = {'D13': 'L3-SIG', 'D14': 'L4-SIG', 'D15': 'L4-SIG'}
STACKS = {
    ('Top', 'L3-SIG'): [('Top', 'L2-GND', 0.30), ('L2-GND', 'L3-SIG', 0.30)],
    ('Top', 'L4-SIG'): [('Top', 'L2-GND', 0.30), ('L2-GND', 'L3-SIG', 0.30), ('L3-SIG', 'L4-SIG', 0.27)],
    ('Bottom', 'L4-SIG'): [('L5-VCC3V3', 'Bottom', 0.30), ('L4-SIG', 'L5-VCC3V3', 0.30)],
    ('Bottom', 'L3-SIG'): [('L5-VCC3V3', 'Bottom', 0.30), ('L4-SIG', 'L5-VCC3V3', 0.30), ('L3-SIG', 'L4-SIG', 0.27)],
}
HOLE = 0.15
ROT = {0: (0.6, 0.0), 180: (-0.6, 0.0), 90: (0.0, 0.6), 270: (0.0, -0.6)}


def mk(kind, layer, net, shape, span=None, hole=0.0, xy=None, ref=None, pad=None, w=None):
    return C.O(kind, layer, net, shape, {}, '%s %s %s' % (kind, layer, net), ('n', id(shape)), new=True, span=span, hole=hole,
               xy=xy, ref=ref, pad=pad, w=w)


def layer_lands(stack):
    """{layer: land radius} -- the largest land of the stack on each layer"""
    out = {}
    for a, b, s in stack:
        for L in (a, b):
            out[L] = max(out.get(L, 0), s / 2)
    return out


def near_objs(L, bb, pad=0.3):
    return C.Grid.near(G, L, bb, pad)


def family(net):
    return {net, 'SDRAM-' + net}


def worst_gap(newo, L, fam, skip=frozenset()):
    """smallest (dist - rule) of newo against non-family base objects on L (skip: ids of removed objects)"""
    best = (9.0, None)
    for q in near_objs(L, C.bbox(newo.shape)):
        if q.net in fam or id(q) in skip:
            continue
        d = C.dist(newo.shape, q.shape)
        g = C.gap_rule(newo, q, L)
        if d - g < best[0]:
            best = (d - g, q.tag)
    return best


def h2h(xy, span):
    worst = (9.0, None)
    gx, gy = int(xy[0] // 0.5), int(xy[1] // 0.5)
    for i in (gx - 1, gx, gx + 1):
        for j in (gy - 1, gy, gy + 1):
            for d in DG.get((i, j), ()):
                if abs(d[0][0] - xy[0]) < 1e-4 and abs(d[0][1] - xy[1]) < 1e-4:
                    return (-1.0, 'coincident drill %s' % d[3])
                if not (d[2] & span):
                    continue
                v = math.hypot(d[0][0] - xy[0], d[0][1] - xy[1]) - d[1] / 2 - HOLE / 2 - 0.24
                if v < worst[0]:
                    worst = (v, 'drill %s (%.3f,%.3f)' % (d[3], d[0][0], d[0][1]))
    return worst


def side_pads(side):
    return [o for o in objs if o.kind == 'pad' and o.layer == side]


PADG = {s: C.Grid(side_pads(s), 0.5) for s in ('Top', 'Bottom')}


def site_eval(net, side, runL, x, y):
    """exact column-site test (no family objects); returns (ok, worst margin, reason) and the per-rule margins"""
    fam = family(net)
    stack = STACKS[(side, runL)]
    m = {}
    # lands
    for L, r in layer_lands(stack).items():
        o = mk('via', L, 'SDRAM-' + net, ('C', x, y, x, y, r), span=[L])
        m['cl_' + L] = worst_gap(o, L, fam)
    # side pad copper
    po = mk('pad', side, 'SDRAM-' + net, ('R', x, y, 0.15, 0.15), ref='RNEW')
    m['cl_pad'] = worst_gap(po, side, fam)
    # mask sliver vs every pad of the side (non-family)
    mo = C.grow(po.shape, 0.05)
    wm = (9.0, None)
    for q in PADG[side].near(side, C.bbox(mo), 0.3):
        if q.net in fam:
            continue
        d = C.dist(mo, C.grow(q.shape, C.mask_exp(q)))
        v = d - 0.10 if d > 0 else -1.0
        if v < wm[0]:
            wm = (v, q.tag)
    m['mask'] = wm
    # drills
    hw = (9.0, None)
    for a, b, s in stack:
        i0, i1 = C.CU.index(a), C.CU.index(b)
        span = set(C.CU[min(i0, i1):max(i0, i1) + 1])
        v = h2h((x, y), span)
        if v[0] < hw[0]:
            hw = v
    m['h2h'] = hw
    # visible silk vs pad opening (>= 0.254 wanted)
    sw = (9.0, None)
    for sd, tb, txt in VIS_BOX:
        if sd != side:
            continue
        v = C.dist(tb, mo) - 0.254
        if v < sw[0]:
            sw = (v, 'silk %s' % txt)
    m['silk'] = sw
    worst = min(m.items(), key=lambda kv: kv[1][0])
    return worst[1][0] >= -1e-6, m


# ------------------------------------------------------------------ run geometry
def run_poly(net):
    path = B['d_escapes'][net]['path']
    L = RUNL[net]
    segs = [(e['x1'], e['y1'], e['x2'], e['y2']) for e in path if e['kind'] == 'track' and e['layer'] == L]
    # confirm every segment exists in the base state with the same net
    base = [o for o in objs if o.kind == 'track' and o.layer == L and o.net == net]
    used = []
    for s in segs:
        hit = [o for o in base if (C.same((o.shape[1], o.shape[2]), s[:2]) and C.same((o.shape[3], o.shape[4]), s[2:])) or
               (C.same((o.shape[1], o.shape[2]), s[2:]) and C.same((o.shape[3], o.shape[4]), s[:2]))]
        assert len(hit) == 1, (net, s)
        used.append(hit[0])
    return L, segs, used


def proj(segs, x, y):
    """nearest point on the polyline: (dist, s, seg index, t, px, py)"""
    best = None
    s0 = 0.0
    for k, (x1, y1, x2, y2) in enumerate(segs):
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / L2))
        px, py = x1 + t * dx, y1 + t * dy
        d = math.hypot(x - px, y - py)
        if best is None or d < best[0] - 1e-12:
            best = (d, s0 + t * math.sqrt(L2), k, t, px, py)
        s0 += math.sqrt(L2)
    return best


def stub_objs(net):
    """U3-side copper that is renamed SDRAM-n: pad stub (Bottom) + first through via"""
    path = B['d_escapes'][net]['path']
    st = [e for e in path if e['kind'] == 'track' and e['layer'] == 'Bottom'][0]
    fv = B['d_escapes'][net]['first_via']
    return st, fv


def build_candidate(net, side, rot, p1, p2, segs, used, runL, conn_w=0.125):
    """returns dict: geometry of the candidate (new/renamed/removed records) or None if the order is wrong"""
    a = proj(segs, *p1)
    b = proj(segs, *p2)
    if not (a[1] < b[1] - 1e-6):
        return None
    k1, k2 = a[2], b[2]
    rm = []           # base track objects removed
    add = []          # (layer, net, x1,y1,x2,y2,w, why)
    for k, s in enumerate(segs):
        o = used[k]
        if k < k1:
            rm.append(o); add.append((runL, 'SDRAM-' + net, s[0], s[1], s[2], s[3], o.w, 'rename'))
        elif k == k1 == k2:
            rm.append(o)
            if math.hypot(a[4] - s[0], a[5] - s[1]) > 1e-6:
                add.append((runL, 'SDRAM-' + net, s[0], s[1], a[4], a[5], o.w, 'piece'))
            if math.hypot(s[2] - b[4], s[3] - b[5]) > 1e-6:
                add.append((runL, net, b[4], b[5], s[2], s[3], o.w, 'piece'))
        elif k == k1:
            rm.append(o)
            if math.hypot(a[4] - s[0], a[5] - s[1]) > 1e-6:
                add.append((runL, 'SDRAM-' + net, s[0], s[1], a[4], a[5], o.w, 'piece'))
        elif k1 < k < k2:
            rm.append(o)
        elif k == k2:
            rm.append(o)
            if math.hypot(s[2] - b[4], s[3] - b[5]) > 1e-6:
                add.append((runL, net, b[4], b[5], s[2], s[3], o.w, 'piece'))
    if a[0] > 1e-6:
        add.append((runL, 'SDRAM-' + net, p1[0], p1[1], a[4], a[5], conn_w, 'connector'))
    if b[0] > 1e-6:
        add.append((runL, net, p2[0], p2[1], b[4], b[5], conn_w, 'connector'))
    cols = []
    for (x, y), nn in ((p1, 'SDRAM-' + net), (p2, net)):
        for f, t, s in STACKS[(side, runL)]:
            cols.append(dict(net=nn, x=round(x, 4), y=round(y, 4), size=s, frm=f, to=t))
    return dict(net=net, side=side, rot=rot, p1=p1, p2=p2, s1=a[1], s2=b[1], conn1=a[0], conn2=b[0], rm=rm, add=add, cols=cols)


def candidate_exact(cand, runL):
    """exact clearance of the candidate's new geometry + family split against the base state"""
    net = cand['net']
    fam = family(net)
    skip = set(id(o) for o in cand['rm'])
    news = []
    for (L, nn, x1, y1, x2, y2, w, why) in cand['add']:
        if why == 'rename':
            continue
        news.append(mk('track', L, nn, ('C', x1, y1, x2, y2, w / 2), w=w))
    for c in cand['cols']:
        i0, i1 = C.CU.index(c['frm']), C.CU.index(c['to'])
        span = C.CU[min(i0, i1):max(i0, i1) + 1]
        for L in span:
            news.append(mk('via', L, c['net'], ('C', c['x'], c['y'], c['x'], c['y'], c['size'] / 2), span=span, hole=HOLE, xy=(c['x'], c['y'])))
    for (x, y), nn, pn in ((cand['p1'], 'SDRAM-' + net, '1'), (cand['p2'], net, '2')):
        news.append(mk('pad', cand['side'], nn, ('R', x, y, 0.15, 0.15), xy=(x, y), ref='RNEW', pad=pn))
    worst = (9.0, None)
    for o in news:
        v = worst_gap(o, o.layer, fam, skip)
        if v[0] < worst[0]:
            worst = (v[0], '%s vs %s' % (o.tag, v[1]))
    # family split: label every family object (base, not removed) by side of the cut
    famobjs = [o for o in objs if o.net in fam and id(o) not in skip]
    # base family objects: U3 side = the renamed set (stub, first via, run segments before k1, U3 pad)
    st, fv = stub_objs(net)
    ren = set()
    for o in famobjs:
        if o.kind == 'pad' and o.ref == 'U3':
            ren.add(id(o))
        if o.kind == 'via' and C.same(o.xy, (fv['x'], fv['y'])):
            ren.add(id(o))
        if o.kind == 'track' and o.layer == 'Bottom' and ({(round(o.shape[1], 3), round(o.shape[2], 3)), (round(o.shape[3], 3), round(o.shape[4], 3))} ==
                {(round(st['x1'], 3), round(st['y1'], 3)), (round(st['x2'], 3), round(st['y2'], 3))}):
            ren.add(id(o))
    allf = []
    for o in famobjs:
        allf.append((o, 'SDRAM-' + net if id(o) in ren else net))
    for (L, nn, x1, y1, x2, y2, w, why) in cand['add']:
        if why == 'rename':
            allf.append((mk('track', L, nn, ('C', x1, y1, x2, y2, w / 2), w=w), nn))
    for o in news:
        allf.append((o, o.net))
    fw = (9.0, None)
    for i, (o, n1) in enumerate(allf):
        for q, n2 in allf[i + 1:]:
            if n1 == n2 or o.layer != q.layer:
                continue
            d = C.dist(o.shape, q.shape)
            g = 0.10 if o.layer in ('L3-SIG', 'L4-SIG') else 0.09
            if d - g < fw[0]:
                fw = (d - g, '%s vs %s' % (o.tag, q.tag))
    # renamed U3-side copper now SDRAM class: on L3/L4 the rule is unchanged (Dn already SDRAM_DATA)
    return worst, fw, news


def comp_clear(cand):
    side = cand['side']
    xs = [cand['p1'][0], cand['p2'][0]]; ys = [cand['p1'][1], cand['p2'][1]]
    bb = [min(xs) - 0.15, min(ys) - 0.15, max(xs) + 0.15, max(ys) + 0.15]
    a14 = min(((rr(bb, b), r) for r, (s, b) in ABOX.items() if s == side), default=(9, None))
    a10 = min(((min(rr(bb, b) for b in bx), r) for r, (s, bx) in BBOX10.items() if s == side), default=(9, None))
    # courtyard (Mech7) overlap, advisory
    cy = [r for r, (s, b) in MECH7.items() if s == side and rr(bb, b) == 0]
    return a14, a10, cy, bb


def main():
    res = {}
    for net in NETS:
        t0 = time.time()
        runL, segs, used = run_poly(net)
        allx = [v for s in segs for v in (s[0], s[2])]; ally = [v for s in segs for v in (s[1], s[3])]
        x0, x1 = min(allx) - BAND, max(allx) + BAND
        y0, y1 = min(ally) - BAND, max(ally) + BAND
        sites = {}
        nsite = 0
        timed_out = False
        why_bad = collections.Counter()
        for side in ('Top', 'Bottom'):
            nx = int(round((x1 - x0) / STEP)) + 1
            ny = int(round((y1 - y0) / STEP)) + 1
            for i in range(nx):
                if time.time() - t0 > BUDGET:
                    timed_out = True
                    break
                x = round(x0 + i * STEP, 4)
                for j in range(ny):
                    y = round(y0 + j * STEP, 4)
                    if proj(segs, x, y)[0] > BAND:
                        continue
                    nsite += 1
                    ok, m = site_eval(net, side, runL, x, y)
                    if ok:
                        sites[(side, i, j)] = (x, y, m)
                    else:
                        why_bad[min(m.items(), key=lambda kv: kv[1][0])[0]] += 1
        print('%s %s: %d sites tested, %d legal (Top %d / Bottom %d) [%.0f s]%s' % (
            net, runL, nsite, len(sites), sum(1 for k in sites if k[0] == 'Top'), sum(1 for k in sites if k[0] == 'Bottom'),
            time.time() - t0, ' TIMED OUT' if timed_out else ''))
        print('   site failures by first rule:', dict(why_bad))
        d = int(round(0.6 / STEP))
        cands = []
        npair = 0
        for (side, i, j), (x, y, m) in sites.items():
            for rot, (dx, dy) in ROT.items():
                k2 = (side, i + int(round(dx / STEP)), j + int(round(dy / STEP)))
                if k2 not in sites:
                    continue
                npair += 1
                x2, y2 = sites[k2][0], sites[k2][1]
                cand = build_candidate(net, side, rot, (x, y), (x2, y2), segs, used, runL)
                if cand is None:
                    continue
                if cand['conn1'] > BAND or cand['conn2'] > BAND:
                    continue
                wc, fw, news = candidate_exact(cand, runL)
                a14, a10, cy, bb = comp_clear(cand)
                ok = wc[0] >= -1e-6 and fw[0] >= -1e-6
                if not ok:
                    continue
                cands.append(dict(net=net, side=side, rot=rot, cx=round((x + x2) / 2, 4), cy=round((y + y2) / 2, 4),
                                  pad1=[x, y], pad2=[x2, y2], s1=round(cand['s1'], 4), s2=round(cand['s2'], 4),
                                  conn1=round(cand['conn1'], 4), conn2=round(cand['conn2'], 4),
                                  site_margins={'pad1': {k: [round(v[0], 4), v[1]] for k, v in m.items()},
                                                'pad2': {k: [round(v[0], 4), v[1]] for k, v in sites[k2][2].items()}},
                                  cand_clear=[round(wc[0], 4), wc[1]], family_clear=[round(fw[0], 4), fw[1]],
                                  compclear_altium=[round(a14[0], 4), a14[1]], compclear_body=[round(a10[0], 4), a10[1]],
                                  courtyard_mech7_overlap=cy, rbox=[round(v, 4) for v in bb],
                                  add=[list(a) for a in cand['add']], cols=cand['cols'],
                                  rm=[dict(layer=o.layer, net=o.net, x1=o.shape[1], y1=o.shape[2], x2=o.shape[3], y2=o.shape[4], w=o.w) for o in cand['rm']]))
        print('   %d site pairs, %d candidates pass exact clearance [%.0f s]' % (npair, len(cands), time.time() - t0))
        res[net] = dict(run_layer=runL, sites_tested=nsite, sites_legal=len(sites), site_pairs=npair, timed_out=timed_out,
                        site_fail_rule=dict(why_bad), candidates=cands, seconds=round(time.time() - t0, 1),
                        legal_sites=[[k[0], v[0], v[1]] for k, v in sites.items()])
        json.dump(res[net], open(os.path.join(lib.HERE, os.environ.get('PREFILTER_PREFIX', 'prefilter') + '_%s.json' % net), 'w'), indent=0)


if __name__ == '__main__':
    main()
