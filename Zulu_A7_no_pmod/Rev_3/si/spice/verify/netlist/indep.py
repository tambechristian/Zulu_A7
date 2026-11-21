"""Independent board->SPICE netlist (LC ladders, own topology code) driven by the same IBIS buffers as bus_sim.
python indep.py NET scenario corner [opts]   opts: viaC=x viaL=x z=x novia ladder=mm tra dt=s cbylen vccr=V"""
import sys, json, math, collections
import numpy as np
sys.path.insert(0, '../..')
import bus_sim as B, ibis2spice as I, ngs

M = json.load(open(B.MODEL))
# own stack: top surface z of each copper and its thickness
CU = [('Top Layer', 0.035), ('L2-GND', 0.0152), ('L3-SIG', 0.0152), ('L4-SIG', 0.0152), ('L5-VCC3V3', 0.0152), ('Bottom Layer', 0.035)]
DIEL = [0.09939, 0.1, 1.1208, 0.1, 0.09939]
ZTOP, z = {}, 0.0
for k, (n, t) in enumerate(CU):
    ZTOP[n] = z
    z += t + (DIEL[k] if k < 5 else 0)
ZBOT = {n: ZTOP[n] + t for n, t in CU}
ORDER = [c[0] for c in CU]


def build(net, opt):
    T = [dict(t) for t in M['tracks'] if t['net'] == net]
    V = [v for v in M['vias'] if v['net'] == net]
    P = [p for p in M['pads'] if p['net'] == net]

    def contacts(layer, skip):
        out = []
        for i, t in enumerate(T):
            if i != skip and t['layer'] == layer:
                out += [(t['x1'], t['y1']), (t['x2'], t['y2'])]
        for v in V:
            if layer in v['span']:
                out.append((v['x'], v['y']))
        for p in P:
            if layer in p['layers']:
                out.append((p['x'], p['y']))
        return out
    segs = []
    for i, t in enumerate(T):
        L = math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1'])
        us = {0.0, 1.0}
        for (x, y) in contacts(t['layer'], i):
            d, u = B._seg_dist(x, y, t['x1'], t['y1'], t['x2'], t['y2'])
            if d <= t['w'] / 2 + 1e-6 and 1e-9 < u < 1 - 1e-9:
                us.add(u)
        us = sorted(us)
        for a, b in zip(us[:-1], us[1:]):
            segs.append({'layer': t['layer'], 'w': t['w'], 'x1': t['x1'] + a * (t['x2'] - t['x1']), 'y1': t['y1'] + a * (t['y2'] - t['y1']),
                         'x2': t['x1'] + b * (t['x2'] - t['x1']), 'y2': t['y1'] + b * (t['y2'] - t['y1']), 'L': (b - a) * L})
    pts = []
    for i, s in enumerate(segs):
        pts.append((('s', i, 0), s['layer'], s['x1'], s['y1'], ('c', s['w'] / 2)))
        pts.append((('s', i, 1), s['layer'], s['x2'], s['y2'], ('c', s['w'] / 2)))
    for j, v in enumerate(V):
        for L in v['span']:
            pts.append((('v', j, L), L, v['x'], v['y'], ('c', v['size'] / 2)))
    for k, p in enumerate(P):
        for L in p['layers']:
            pts.append((('p', k, L), L, p['x'], p['y'], ('r', p['w'] / 2, p['h'] / 2)))
    uf = B.UF()

    def inside(px, py, q):
        _, _, qx, qy, sh = q
        if sh[0] == 'c':
            return math.hypot(px - qx, py - qy) <= sh[1] + 1e-6
        return abs(px - qx) <= sh[1] + 1e-6 and abs(py - qy) <= sh[2] + 1e-6
    for a in range(len(pts)):
        uf.find(pts[a][0])
        for b in range(len(pts)):
            if a != b and pts[a][1] == pts[b][1] and inside(pts[a][2], pts[a][3], pts[b]):
                uf.union(pts[a][0], pts[b][0])
    names = {}

    def nd(k):
        r = uf.find(k)
        return names.setdefault(r, 'm%d' % len(names))
    el = []
    zs = opt.get('z', 1.0)
    cnt = [0]

    def ladder(a, b, L, lp):
        Lt = lp['L_nH_per_mm'] * L * 1e-9 * zs
        Ct = lp['C_pF_per_mm'] * L * 1e-12 / zs
        if opt.get('tra'):
            cnt[0] += 1
            el.append('T%d %s 0 %s 0 Z0=%.5g TD=%.6g' % (cnt[0], a, b, lp['Z0'] * zs, L * lp['td_ps_per_mm'] * 1e-12))
            return
        n = max(1, int(math.ceil(L / opt.get('ladder', 0.05))))
        prev = a
        for k in range(n):
            cnt[0] += 1
            nxt = b if k == n - 1 else 'x%d' % cnt[0]
            el.append('C%da %s 0 %.6g' % (cnt[0], prev, Ct / n / 2))
            el.append('L%d %s %s %.6g' % (cnt[0], prev, nxt, Lt / n))
            el.append('C%db %s 0 %.6g' % (cnt[0], nxt, Ct / n / 2))
            prev = nxt
    lenby = collections.defaultdict(float)
    for i, s in enumerate(segs):
        a, b = nd(('s', i, 0)), nd(('s', i, 1))
        lp = B.line(s['layer'], s['w'])
        lenby[s['layer']] += s['L']
        if a == b:
            cnt[0] += 1
            el.append('Cq%d %s 0 %.6g' % (cnt[0], a, lp['C_pF_per_mm'] * s['L'] * 1e-12))
        else:
            ladder(a, b, s['L'], lp)
    viarep = []
    for j, v in enumerate(V):
        span = [L for L in ORDER if L in v['span']]
        h = ZBOT[span[-1]] - ZTOP[span[0]]
        d = v['hole']
        Ltot = 0.2 * h * (math.log(4 * h / d) + 1) * 1e-9 * opt.get('viaL', 1.0)
        D1, D2 = v['size'], v['size'] + 2 * B.ANTIPAD_CLEAR
        Ctot = 1.41 * B.ER_AVG * (h / 25.4) * D1 / (D2 - D1) * 1e-12 * opt.get('viaC', 1.0)
        if opt.get('fdC'):
            Ctot = {('Top Layer', 'Bottom Layer'): 0.28e-12, ('L3-SIG', 'L4-SIG'): 0.197e-12}.get((span[0], span[-1]), Ctot)
        viarep.append((span[0], span[-1], round(h, 4), round(Ltot * 1e9, 3), round(Ctot * 1e12, 3)))
        if opt.get('novia'):
            Ltot, Ctot = 1e-15, 0.0
        ns = [nd(('v', j, L)) for L in span]
        zc = [(ZTOP[L] + ZBOT[L]) / 2 for L in span]
        for k in range(len(span)):
            cnt[0] += 1
            el.append('Cv%d %s 0 %.6g' % (cnt[0], ns[k], Ctot / len(span)))
        for k in range(len(span) - 1):
            cnt[0] += 1
            if ns[k] != ns[k + 1]:
                el.append('Lw%d %s %s %.6g' % (cnt[0], ns[k], ns[k + 1], max(Ltot * (zc[k + 1] - zc[k]) / (zc[-1] - zc[0]), 1e-15)))
    u1 = [k for k, p in enumerate(P) if p['ref'] == 'U1'][0]
    u3 = [k for k, p in enumerate(P) if p['ref'] == 'U3'][0]
    n1, n3 = nd(('p', u1, P[u1]['layers'][0])), nd(('p', u3, P[u3]['layers'][0]))
    return el, n1, n3, dict(lenby), viarep, segs


def run(net, scen, corner, opt):
    if 'rail' in opt:
        _r = I._rails
        I._rails = lambda m, c: (opt['rail'], 0.0, opt['rail'], 0.0)
    el, n1, n3, lenby, viarep, segs = build(net, opt)
    U1, U3 = I.Ibis(B.U1_IBS), I.Ibis(B.U3_IBS)
    p1 = [p['pad'] for p in M['pads'] if p['net'] == net and p['ref'] == 'U1'][0]
    p3 = [p['pad'] for p in M['pads'] if p['net'] == net and p['ref'] == 'U3'][0]
    if scen == 'write':
        di, dp, dn, ri, rp, rn = U1, p1, n1, U3, p3, n3
    else:
        di, dp, dn, ri, rp, rn = U3, p3, n3, U1, p1, n1
    dm, rm = di.model(di.pins[dp][1]), ri.model(ri.pins[rp][1])
    lines = ['* indep %s' % net]
    t, ku, kd = I.weights_pwl(dm, corner, B.EDGES, B.T_END)
    lines += B.pwl_source('ku', 'ku', t, ku) + B.pwl_source('kd', 'kd', t, kd)
    lines += I.buffer_netlist('D', dm, corner, 'ddie', dn, I.pkg_for(di, dp, corner), 'ku', 'kd')[0]
    b, (vcc, _) = I.buffer_netlist('R', rm, corner, 'rdie', rn, I.pkg_for(ri, rp, corner))
    lines += b + el
    dt = opt.get('dt', 5e-12)
    lines += ['.options reltol=1e-4 abstol=1e-12 vntol=1e-6 method=gear', '.ic V(ddie)=0 V(rdie)=0',
              '.tran %g %g 0 %g' % (dt, B.T_END, dt), '.end']
    r = ngs.run(lines)
    if 'rdie' not in r:
        raise RuntimeError(ngs.log()[-2000:])
    m = B.measure(r['time'], r['rdie'], vcc)
    return m, lenby, viarep, r, vcc


if __name__ == '__main__':
    net, scen, corner = sys.argv[1:4]
    opt = {}
    for a in sys.argv[4:]:
        if '=' in a:
            k, v = a.split('=')
            opt[k] = float(v)
        else:
            opt[a] = True
    m, lenby, viarep, r, vcc = run(net, scen, corner, opt)
    print(json.dumps({'net': net, 'scen': scen, 'corner': corner, 'opt': opt, 'ovs': round(m['overshoot'], 4), 'uns': round(m['undershoot'], 4),
                      'ring': round(m['ringback_into_band'], 4), 't1090': round(m['t10_90_ns'] or -1, 4), 'vcc': vcc,
                      'len_by_layer': {k: round(v, 3) for k, v in lenby.items()}, 'vias': viarep}))
