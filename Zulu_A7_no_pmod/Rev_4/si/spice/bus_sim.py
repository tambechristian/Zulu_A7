"""SDRAM bus SI cross-check for Zulu_a7_no_pmod Rev 2: board copper -> ngspice, IBIS buffers at both ends, 3.3 V.

    python bus_sim.py [--corner typ|max] [--nets A0,D0,...] [--check]

Per net (from tools/route/model.json, the board extract):
  * every track becomes a lossless T-line (Z0/delay from fieldsolve on the board's stack for its layer and width);
    tracks shorter than SHORT_MM become a lumped C (their line capacitance) on a merged node;
  * every via becomes a ladder through its span (barrel L split by length, Johnson's pad/antipad capacitance spread
    over the span; antipad = pad + 2 x 0.175 mm, the board's via-to-pour clearance), so via stubs are modelled;
  * T-junctions and endpoints inside pads/vias are merged on the same layer;
  * the reference is ideal ground (L2/L5 treated as perfect planes: plane-gap crossings are NOT modelled).
Scenarios: WRITE (U1 drives, U3 receives) for all 39 nets; READ (U3 DQ drives, U1 receives) for D0-D15.
Stimulus: edges at 1.0, 8.5, 16.0, 23.5 ns (133 MHz data toggling), 32 ns window. Measured at the receiver die.
"""
import json, math, os, sys, collections
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ngs
import ibis2spice as I
import fieldsolve as F

ROOT = os.path.dirname(os.path.dirname(HERE))          # Rev_2
MODEL = os.path.join(ROOT, 'tools', 'route', 'model.json')
U1_IBS = os.path.join(ROOT, 'si', 'vivado', 'zulu_a7_no_pmod_u1.ibs')
U3_IBS = os.path.join(ROOT, 'si', 'ibis', 'as4c32m16sb', 'Alliance-Memory_AS4C32M16SB-7TCN_Ibis.ibs')
ORDER = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
STACK = 'fab'                 # 'fab' = PCBWay construction (default), 'pcbdoc' = stack stored in the PcbDoc
TD_LUMP = 10e-12              # T-lines shorter than this become an L / C pi section (no femtosecond steps)
VIA_C_PER_MM = 0.173e-12      # field-solved: through via 0.35/0.20 = 0.28 pF over 1.615 mm (reviewer FD solve)
MICROVIA_C = 0.05e-12         # single-dielectric laser via, both pads
VRAIL = {'typ': 3.3, 'max': 3.465, 'min': 3.135}   # one VCC3V3 rail for both parts (regulator +-5 %)
VIL, VIH = 0.8, 2.0           # LVTTL / LVCMOS33 input thresholds (both datasheets)
EDGES = [(1.0e-9, 'rise'), (8.5e-9, 'fall'), (16.0e-9, 'rise'), (23.5e-9, 'fall')]
T_END = 32e-9
NETS = ['A%d' % i for i in range(13)] + ['BS0', 'BS1'] + ['D%d' % i for i in range(16)] + \
       ['CAS#', 'RAS#', 'WE#', 'CKE', 'SDRAM-CS#', 'LDQM', 'UDQM', 'SDRAM-CLK']

_lines_cache = {}


def line(layer, w):
    k = (STACK, layer, round(w, 5))
    if k not in _lines_cache:
        _lines_cache[k] = F.zulu_line(layer, w, STACK)
    return _lines_cache[k]


class UF:
    def __init__(self):
        self.p = {}

    def find(self, a):
        self.p.setdefault(a, a)
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


def _seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    u = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L2))
    return math.hypot(px - (x1 + u * dx), py - (y1 + u * dy)), u


def net_elements(M, net):
    """Graph of one net: list of SPICE element lines, the U1 and U3 pad node names, and a report."""
    tracks = [dict(t) for t in M['tracks'] if t['net'] == net]
    vias = [v for v in M['vias'] if v['net'] == net]
    pads = [p for p in M['pads'] if p['net'] == net]
    # split tracks at T-junctions (an endpoint of one track on the interior of another, same layer)
    changed = True
    while changed:
        changed = False
        for a in tracks:
            for (px, py) in ((a['x1'], a['y1']), (a['x2'], a['y2'])):
                for b in tracks:
                    if b is a or b['layer'] != a['layer']:
                        continue
                    d, u = _seg_dist(px, py, b['x1'], b['y1'], b['x2'], b['y2'])
                    Lb = math.hypot(b['x2'] - b['x1'], b['y2'] - b['y1'])
                    if d <= b['w'] / 2 + 1e-6 and 1e-3 < u * Lb < Lb - 1e-3:
                        mx, my = b['x1'] + u * (b['x2'] - b['x1']), b['y1'] + u * (b['y2'] - b['y1'])
                        nb = dict(b)
                        nb['x1'], nb['y1'] = mx, my
                        b['x2'], b['y2'] = mx, my
                        tracks.append(nb)
                        changed = True
                        break
                if changed:
                    break
            if changed:
                break
    uf = UF()
    pts = []   # (key, layer, x, y)
    for i, t in enumerate(tracks):
        for e, (x, y) in enumerate(((t['x1'], t['y1']), (t['x2'], t['y2']))):
            pts.append((('t', i, e), t['layer'], x, y, t['w'] / 2))
    for j, v in enumerate(vias):
        for L in v['span']:
            pts.append((('v', j, L), L, v['x'], v['y'], v['size'] / 2))
    for k, p in enumerate(pads):
        for L in p['layers']:
            pts.append((('p', k, L), L, p['x'], p['y'], None))
    # merge same-layer points that touch
    for a in range(len(pts)):
        ka, la, xa, ya, ra = pts[a]
        for b in range(a + 1, len(pts)):
            kb, lb, xb, yb, rb = pts[b]
            if la != lb:
                continue
            touch = False
            if ka[0] == 'p' or kb[0] == 'p':
                pk, ok = (ka, kb) if ka[0] == 'p' else (kb, ka)
                p = pads[pk[1]]
                ox, oy = (xb, yb) if pk is ka else (xa, ya)
                if p['shape'] == 'circle':
                    touch = math.hypot(ox - p['x'], oy - p['y']) <= p['w'] / 2 + 1e-6
                else:
                    touch = abs(ox - p['x']) <= p['w'] / 2 + 1e-6 and abs(oy - p['y']) <= p['h'] / 2 + 1e-6
            else:
                touch = math.hypot(xa - xb, ya - yb) <= max(ra, rb) + 1e-6
            if touch:
                uf.union(ka, kb)
    names = {}

    def node(key):
        r = uf.find(key)
        if r not in names:
            names[r] = 'n%d' % len(names)
        return names[r]

    el = []
    lumpC = collections.defaultdict(float)
    rep = {'tlines': 0, 'lumped': 0, 'len_mm': 0.0, 'delay_ps': 0.0}
    for i, t in enumerate(tracks):
        a, b = node(('t', i, 0)), node(('t', i, 1))
        L = math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1'])
        lp = line(t['layer'], t['w'])
        rep['len_mm'] += L
        td = L * lp['td_ps_per_mm'] * 1e-12
        rep['delay_ps'] += td * 1e12
        if a == b:
            lumpC[a] += lp['C_pF_per_mm'] * L * 1e-12
            rep['lumped'] += 1
        elif td < TD_LUMP:
            # pi section: series L = Z0 * td, C = td / Z0 split over the two ends
            el.append('L_s%d %s %s %.5g' % (i, a, b, max(lp['Z0'] * td, 1e-15)))
            lumpC[a] += td / lp['Z0'] / 2
            lumpC[b] += td / lp['Z0'] / 2
            rep['lumped'] += 1
        else:
            el.append('T%d %s 0 %s 0 Z0=%.4g TD=%.5g' % (i, a, b, lp['Z0'], td))
            rep['tlines'] += 1
    for j, v in enumerate(vias):
        span = [L for L in ORDER if L in v['span']]
        Z, CU = F.stack_z(STACK)
        h = Z[span[-1]] + CU[span[-1]] - Z[span[0]]
        d = max(v.get('hole', 0.2), 0.05)
        Ltot = 0.2 * h * (math.log(4 * h / d) + 1) * 1e-9
        Ctot = MICROVIA_C if h < 0.3 else VIA_C_PER_MM * h * (v['size'] / 0.35)
        nodes = [node(('v', j, L)) for L in span]
        for L, n in zip(span, nodes):
            lumpC[n] += Ctot / len(span)
        for k in range(len(span) - 1):
            frac = (Z[span[k + 1]] - Z[span[k]]) / max(Z[span[-1]] - Z[span[0]], 1e-6)
            if nodes[k] != nodes[k + 1]:
                el.append('Lv%d_%d %s %s %.4g' % (j, k, nodes[k], nodes[k + 1], Ltot * frac))
    for n, c in lumpC.items():
        if c > 0:
            el.append('Cl_%s %s 0 %.4g' % (n, n, c))
    u1 = [p for p in pads if p['ref'] == 'U1']
    u3 = [p for p in pads if p['ref'] == 'U3']
    assert len(u1) == 1 and len(u3) == 1, (net, [(p['ref'], p['pad']) for p in pads])
    n_u1 = node(('p', pads.index(u1[0]), u1[0]['layers'][0]))
    n_u3 = node(('p', pads.index(u3[0]), u3[0]['layers'][0]))
    # connectivity check: union-find over element terminals
    g = UF()
    for e in el:
        tok = e.split()
        if tok[0][0] in 'TRL':
            a, b = (tok[1], tok[3]) if tok[0][0] == 'T' else (tok[1], tok[2])
            g.union(a, b)
    rep['connected'] = g.find(n_u1) == g.find(n_u3)
    rep['u1_pin'], rep['u3_pin'] = u1[0]['pad'], u3[0]['pad']
    rep['vias'] = len(vias)
    return el, n_u1, n_u3, rep


def pwl_source(name, node, t, v):
    pts = ' '.join('%.6g %.6g' % (a, b) for a, b in zip(t, v))
    line_ = 'V%s %s 0 PWL(%s)' % (name, node, pts)
    out = []
    while len(line_) > 900:
        cut = line_.rfind(' ', 0, 900)
        out.append(line_[:cut])
        line_ = '+' + line_[cut:]
    out.append(line_)
    return out


def simulate(M, net, scenario, corner, U1, U3, dt=5e-12):
    el, n1, n3, rep = net_elements(M, net)
    rser = float(os.environ.get('ZULU_RSER', '0'))   # series-resistor study: R between U3's pin and the board
    if rser > 0:
        el = el + ['Rser u3pin %s %g' % (n3, rser)]
        n3 = 'u3pin'
    if scenario == 'write':
        drv_ib, drv_pin, drv_node, rcv_ib, rcv_pin, rcv_node = U1, rep['u1_pin'], n1, U3, rep['u3_pin'], n3
    else:
        drv_ib, drv_pin, drv_node, rcv_ib, rcv_pin, rcv_node = U3, rep['u3_pin'], n3, U1, rep['u1_pin'], n1
    dm = drv_ib.model(drv_ib.pins[drv_pin][1])
    if scenario == 'read' and os.environ.get('ZULU_DQ_MODEL'):   # SDRAM drive-strength study (DQ_72%, DQ_39%, DQ_11%)
        dm = drv_ib.model(os.environ['ZULU_DQ_MODEL'])
    rm = rcv_ib.model(rcv_ib.pins[rcv_pin][1])
    lines = ['* %s %s %s' % (net, scenario, corner)]
    t, ku, kd = I.weights_pwl(dm, corner, EDGES, T_END)
    lines += pwl_source('ku', 'ku', t, ku) + pwl_source('kd', 'kd', t, kd)
    rail = VRAIL[corner]
    b, (vcc_d, _) = I.buffer_netlist('D', dm, corner, 'ddie', drv_node, I.pkg_for(drv_ib, drv_pin, corner), 'ku', 'kd', rail=rail)
    lines += b
    b, (vcc_r, _) = I.buffer_netlist('R', rm, corner, 'rdie', rcv_node, I.pkg_for(rcv_ib, rcv_pin, corner), rail=rail)
    lines += b
    lines += el
    lines += ['.options reltol=1e-4 abstol=1e-12 vntol=1e-6 method=gear', '.ic V(ddie)=0 V(rdie)=0',
              '.tran %g %g 0 %g' % (dt, T_END, dt), '.end']
    r = ngs.run(lines)
    log = ngs.log()
    if 'rdie' not in r or r['time'][-1] < T_END * (1 - 1e-6) or 'cannot recover' in log or 'Timestep too small' in log:
        raise RuntimeError('%s %s %s: transient did not complete (t_end %s)\n%s' % (
            net, scenario, corner, r['time'][-1] if 'time' in r else None, log[-1500:]))
    tt, vr, vd = r['time'], r['rdie'], r['ddie']
    vrp = r.get(rcv_node, vr)
    return tt, vr, vd, vrp, vcc_r, rm, dm, rep


def measure(tt, v, vcc, vil=VIL, vih=VIH):
    """overshoot/undershoot at the receiver, non-monotonic ringback through the threshold band, 10-90 % edge."""
    res = {'vmax': float(v.max()), 'vmin': float(v.min()), 'overshoot': float(v.max() - vcc), 'undershoot': float(-v.min())}
    ring = 0.0
    slews = []
    for (te, kind), nxt in zip(EDGES, [e[0] for e in EDGES[1:]] + [T_END]):
        sel = (tt >= te) & (tt < nxt)
        w, ts = v[sel], tt[sel]
        if kind == 'rise':
            k = np.flatnonzero(w >= vih)
            if len(k):
                after = w[k[0]:]
                ring = max(ring, vih - after.min())          # how far it falls back below VIH after first crossing
            a, b = np.flatnonzero(w >= 0.1 * vcc), np.flatnonzero(w >= 0.9 * vcc)
        else:
            k = np.flatnonzero(w <= vil)
            if len(k):
                after = w[k[0]:]
                ring = max(ring, after.max() - vil)
            a, b = np.flatnonzero(w <= 0.9 * vcc), np.flatnonzero(w <= 0.1 * vcc)
        if len(a) and len(b):
            slews.append((ts[b[0]] - ts[a[0]]) * 1e9)
    res['ringback_into_band'] = float(ring)      # >0: crosses back into the undefined band
    res['t10_90_ns'] = float(np.mean(slews)) if slews else None
    return res


def run_case(task):
    """One (net, scenario, corner, stack) in this worker process; returns the measurement dict or an error dict."""
    global STACK
    net, scen, corner, stack = task
    STACK = stack
    M = json.load(open(MODEL))
    U1, U3 = I.Ibis(U1_IBS), I.Ibis(U3_IBS)
    try:
        tt, vr, vd, vrp, vcc, rm, dm, rep = simulate(M, net, scen, corner, U1, U3)
    except Exception as e:
        return {'net': net, 'scenario': scen, 'corner': corner, 'stack': stack, 'error': str(e)[:600]}
    rail = VRAIL[corner]
    m = measure(tt, vr, rail)
    mp = measure(tt, vrp, rail)
    if m['vmax'] < 0.5 * rail or m['vmin'] > 0.5 * rail:
        return {'net': net, 'scenario': scen, 'corner': corner, 'stack': stack, 'error': 'receiver never switched'}
    m.update({'net': net, 'scenario': scen, 'corner': corner, 'stack': stack, 'rail': rail,
              'driver_model': dm.name, 'receiver_model': rm.name,
              'pin_overshoot': mp['overshoot'], 'pin_undershoot': mp['undershoot'],
              'len_mm': round(rep['len_mm'], 2), 'flight_ps': round(rep['delay_ps']), 'tlines': rep['tlines'],
              'lumped': rep['lumped'], 'vias': rep['vias'], 'connected': rep['connected'], 't_end_ns': float(tt[-1] * 1e9)})
    np.savez_compressed(os.path.join(HERE, 'wave', '%s_%s_%s_%s%s.npz' % (net.replace('#', 'N'), scen, corner, stack, os.environ.get('ZULU_WAVE_TAG', ''))),
                        t=tt, rx_die=vr, tx_die=vd, rx_pin=vrp)
    return m


def main():
    import multiprocessing as mp
    args = sys.argv[1:]
    corners = args[args.index('--corners') + 1].split(',') if '--corners' in args else ['typ', 'max']
    stacks = args[args.index('--stacks') + 1].split(',') if '--stacks' in args else ['fab']
    nets = args[args.index('--nets') + 1].split(',') if '--nets' in args else NETS
    workers = int(args[args.index('--workers') + 1]) if '--workers' in args else 6
    tasks = [(n, sc, c, st) for st in stacks for c in corners for n in nets
             for sc in (['write', 'read'] if n.startswith('D') and n[1:].isdigit() else ['write'])]
    out = []
    with mp.Pool(workers, maxtasksperchild=1) as pool:
        for m in pool.imap_unordered(run_case, tasks):
            out.append(m)
            if 'error' in m:
                print('ERROR %s %s %s %s: %s' % (m['net'], m['scenario'], m['corner'], m['stack'], m['error'][:200]), flush=True)
            else:
                print('%-10s %-5s %-3s %-6s ovs %+6.3f V  uns %6.3f V  ringback %+6.3f  t10-90 %5.2f ns  len %5.1f mm' % (
                    m['net'], m['scenario'], m['corner'], m['stack'], m['overshoot'], m['undershoot'],
                    m['ringback_into_band'], m['t10_90_ns'] or -1, m['len_mm']), flush=True)
    tag = args[args.index('--tag') + 1] if '--tag' in args else ''
    json.dump(out, open(os.path.join(HERE, 'results%s.json' % tag), 'w'), indent=1)
    print('done: %d cases, %d errors' % (len(out), sum('error' in m for m in out)))


if __name__ == '__main__':
    os.makedirs(os.path.join(HERE, 'wave'), exist_ok=True)
    main()
