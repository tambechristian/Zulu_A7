"""[d10/judge/bus_sim_judge.py: byte copy of d10/relocate/bus_sim_plan.py (itself bus_sim_placed.py + a plan-JSON reader, diff reviewed by the judge) with outputs renamed to sim_judge_raw_<tag>.json / wave_judge/. Plan via env ZULU_PLAN.]
its edit list from ONE plan JSON in the dq_series_r_plan.json format (--plan, default plan.json in this folder)
instead of judge_check.py's plan readers; outputs go to this folder (sim_plan_raw_<tag>.json, wave_plan/).]

bus_sim_placed.py -- COPY of si/spice/bus_sim.py (that file is not edited) with one added option: the U3 DQ series R
at its REAL planned position (the judge's FINAL plan in this folder), not at U3's pin.

ADDED OPTION (everything below the original docstring is bus_sim.py unchanged unless marked 'PLACED'):
  mode 'base'   : today's copper, no R (board_extract.json = PcbDoc md5 2a616c1c, converted to model.json's format;
                  --src model uses tools/route/model.json instead, for the reproduction check)
  mode 'pin'    : today's copper, R right at U3's pin (bus_sim's ZULU_RSER behaviour, optional package model)
  mode 'placed' : the FINAL plan's copper (judge_check.py plan_arrays() + plan_top(D8,D11,D12) + plan_judge_d9(),
                  or + D15 with --with-d15) applied to board_extract.json exactly as judge_check.apply() does; the
                  net is split into SDRAM-Dn (U3 pin .. R pad 1) and Dn (R pad 2 .. U1 ball); each half is netlisted
                  by the original net_elements() (so the U3-pin-to-R copper stays modelled as it is today, the
                  removed copper is gone, the added segments get fieldsolve's line for their layer/width, the new
                  microvia columns get bus_sim's via ladder) and the halves are joined by the R plus a package model:
                  Rser A-x, Lesl x-B, Cpar A-B, Cpad A-0, Cpad B-0 (A = R pad 1, U3 side; B = R pad 2, U1 side).
                  Nets with no R in the plan (D10, D13, D14, D15 unless --with-d15) run as 'base'.
  Package sets: 'parts' = parts.md's 0201 estimate (ESL 0.5 nH, 0.05 pF across, 0.08 pF per pad to plane);
                'light' = the task's lighter set (0.3 nH, 0.03 pF across, 0.04 pF per pad); 'ideal' = R only.
  One case per process (ngspice.dll leaks when reused), at most 6 workers. Waves -> wave_placed/, results ->
  sim_placed_raw_<tag>.json. Every run must reach T_END (simulate() raises otherwise).

    python bus_sim_placed.py --mode placed --r 22 --corners typ,max --stacks fab [--nets D0,..] [--pkg parts] --tag x

ORIGINAL bus_sim.py DOCSTRING:
SDRAM bus SI cross-check for Zulu_a7_no_pmod Rev 2: board copper -> ngspice, IBIS buffers at both ends, 3.3 V.

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

HERE = os.path.dirname(os.path.abspath(__file__))           # d10/relocate (outputs)
SR = os.path.dirname(os.path.dirname(HERE))                    # si/series_r (judge_check.py, board_extract.json)
SPICE = os.path.join(os.path.dirname(SR), 'spice')     # PLACED: the shared modules stay in si/spice
sys.path.insert(0, SR)
sys.path.insert(1, SPICE)
import ngs
import ibis2spice as I
import fieldsolve as F

ROOT = os.path.dirname(os.path.dirname(SR))            # Rev_2
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
    if PLACED.get('split'):                          # PLACED: two halves joined by the R at its planned position
        el, n1, n3, rep = placed_elements(M, net)
    else:
        el, n1, n3, rep = net_elements(M, net)
    rser = float(os.environ.get('ZULU_RSER', '0'))   # series-resistor study: R between U3's pin and the board
    if rser > 0:
        el = el + r_package('u3pin', n3, rser, PLACED.get('pkg'))   # PLACED: optional package model at the pin
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




# ================================================================================ PLACED: everything below is new
import re

EXTRACT = os.path.join(SR, 'board_extract.json')
WAVE = os.path.join(HERE, 'wave_judge')
PLAN = os.environ.get('ZULU_PLAN', os.path.join(HERE, 'plan.json'))
PKG = {'parts': dict(L=0.5e-9, Cpar=0.05e-12, Cpad=0.08e-12),     # parts.md 0201 estimate (judge's sims used it)
       'light': dict(L=0.3e-9, Cpar=0.03e-12, Cpad=0.04e-12),     # the task's lighter estimate
       'ideal': None}
PLAN_NETS = ['D%d' % i for i in range(13)]                          # this plan: R119-R131
OPTIONAL_NETS = ['D15']                                              # R134, optional extra in the judge's plan
PLACED = {}                                                          # per process: split, pkg, r, rref
LN_OUT = {'Top': 'Top Layer', 'Bottom': 'Bottom Layer', 'Top Layer': 'Top Layer', 'Bottom Layer': 'Bottom Layer',
          'L2-GND': 'L2-GND', 'L3-SIG': 'L3-SIG', 'L4-SIG': 'L4-SIG', 'L5-VCC3V3': 'L5-VCC3V3'}
USE_EDGES = EDGES[1:]          # the 1.0 ns rise starts from the .ic state (timing.py skips it too)
VTH = 1.4                      # LVTTL / datasheet Vmeas threshold for the delay comparison


def r_package(a, b, r, pkg, tag='rp'):
    """series R from node a (U3 side) to node b (U1 side), optionally with the 0201 package model"""
    if not pkg:
        return ['R%s %s %s %g' % (tag, a, b, r)]
    x = tag + 'x'
    return ['R%s %s %s %g' % (tag, a, x, r), 'L%s %s %s %g' % (tag, x, b, pkg['L']),
            'C%sp %s %s %g' % (tag, a, b, pkg['Cpar']), 'C%sa %s 0 %g' % (tag, a, pkg['Cpad']),
            'C%sb %s 0 %g' % (tag, b, pkg['Cpad'])]


CUL = ['Top', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom']
LNS = {'Top Layer': 'Top', 'Bottom Layer': 'Bottom', 'Top': 'Top', 'Bottom': 'Bottom', 'L2-GND': 'L2-GND',
       'L3-SIG': 'L3-SIG', 'L4-SIG': 'L4-SIG', 'L5-VCC3V3': 'L5-VCC3V3'}


def _span(a, b):
    i, j = CUL.index(LNS[a]), CUL.index(LNS[b])
    return CUL[min(i, j):max(i, j) + 1]


def final_edits(net):
    """the plan JSON (dq_series_r_plan.json format) as judge_check's edit list; renames are remove + re-add"""
    P = json.load(open(PLAN))
    E = dict(remove_tracks=[], remove_vias=[], rename_tracks=[], rename_vias=[], renet_pads=[], add_tracks=[],
             add_vias=[], add_pads=[], parts={})
    for t in P['remove']:
        E['remove_tracks'].append(dict(layer=LNS[t['layer']], net=t['net'], x1=t['x1'], y1=t['y1'], x2=t['x2'], y2=t['y2']))
    for v in P['remove_vias']:
        E['remove_vias'].append(dict(net=v['net'], x=v['x'], y=v['y'], span=_span(v['span'][0], v['span'][-1])))
    for t in P['tracks']:
        E['add_tracks'].append(dict(layer=LNS[t['layer']], net=t['net'], w=t['w'], x1=t['x1'], y1=t['y1'], x2=t['x2'], y2=t['y2']))
    for v in P['vias']:
        E['add_vias'].append(dict(net=v['net'], x=v['x'], y=v['y'], size=v['size'], hole=v['hole'], span=_span(v['from'], v['to'])))
    E['renet_pads'] = [dict(r) for r in P['renet_pads']]
    for pr in P['parts']:
        for k, pd in (('1', pr['pad1']), ('2', pr['pad2'])):
            E['add_pads'].append(dict(ref=pr['ref'], pad=k, layer=pr['side'], net=pd['net'], x=pd['x'], y=pd['y'], w=0.30,
                                      h=0.30, shape='rect', hole=0.0))
        E['parts']['D%d' % pr['net_bit']] = dict(ref=pr['ref'], side=pr['side'], x=pr['x'], y=pr['y'], rot=pr['rot'])
    return E


def extract_model(E=None):
    """board_extract.json (+ optional edit list, applied in judge_check.apply()'s order) -> model.json format"""
    import judge_check as J
    pads, tracks, vias = J.build_board()
    errs = []
    if E:
        for rm in E['remove_tracks']:
            i = J.match_track(tracks, rm)
            if i is None:
                errs.append(('remove track', rm))
            else:
                tracks[i] = None
        for rm in E['remove_vias']:
            i = J.match_via(vias, rm)
            if i is None:
                errs.append(('remove via', rm))
            else:
                vias[i] = None
        for rn in E['rename_tracks']:
            i = J.match_track(tracks, rn)
            if i is None:
                errs.append(('rename track', rn))
            else:
                tracks[i] = dict(tracks[i], net=rn['new'])
        for rn in E['rename_vias']:
            i = J.match_via(vias, rn)
            if i is None:
                errs.append(('rename via', rn))
            else:
                vias[i] = dict(vias[i], net=rn['new'])
        for rp in E['renet_pads']:
            hit = [i for i, p in enumerate(pads) if p['ref'] == rp['ref'] and p['pad'] == rp['pad']]
            if not hit:
                errs.append(('renet pad', rp))
            for i in hit:
                pads[i] = dict(pads[i], net=rp['net'])
        tracks = tracks + list(E['add_tracks'])
        vias = vias + list(E['add_vias'])
        pads = pads + list(E['add_pads'])
    if errs:
        raise RuntimeError('plan edits did not apply: %s' % errs[:5])
    M = {'pads': [], 'tracks': [], 'vias': []}
    for p in pads:
        lay = ORDER if p['layer'] == 'Multi' else [LN_OUT[p['layer']]]
        # model.json writes U1's round lands as their bounding square; keep that so 'base' reproduces bus_sim
        M['pads'].append(dict(ref=p['ref'], pad=p['pad'], net=p['net'], x=p['x'], y=p['y'],
                              shape='circle' if p['shape'] == 'circle' else 'rect', w=p['w'], h=p['h'], layers=lay,
                              drill=p.get('hole', 0.0), plated=False))
    for t in tracks:
        if t is None:
            continue
        M['tracks'].append(dict(net=t['net'], layer=LN_OUT[t['layer']], w=t['w'], x1=t['x1'], y1=t['y1'],
                                x2=t['x2'], y2=t['y2']))
    for v in vias:
        if v is None:
            continue
        M['vias'].append(dict(net=v['net'], x=v['x'], y=v['y'], size=v['size'], hole=v['hole'],
                              span=[LN_OUT[L] for L in v['span']]))
    return M


def _prefix(lines, pre):
    out = []
    for ln in lines:
        tok = ln.split()
        tok[0] = tok[0][0] + pre + tok[0][1:]
        tok = [tok[0]] + [(pre + x if re.fullmatch(r'n\d+', x) else x) for x in tok[1:]]
        out.append(' '.join(tok))
    return out


def placed_elements(M, net):
    """SDRAM-<net> half (U3 pin .. R pad 1) + <net> half (R pad 2 .. U1 ball), each by the original net_elements(),
    joined by the R + package. R pad 1 stands in as the 'U1' end of the SDRAM half, R pad 2 as the 'U3' end of the
    line half (net_elements needs exactly one U1 and one U3 pad per net)."""
    sn = 'SDRAM-' + net
    rref = PLACED['rref']
    Mx = dict(M)
    Mx['pads'] = []
    seen = set()
    for p in M['pads']:
        q = dict(p)
        if q['ref'] == rref:
            if q['net'] == sn:
                q['ref'], q['pad'] = 'U1', 'RA'
            elif q['net'] == net:
                q['ref'], q['pad'] = 'U3', 'RB'
            else:
                raise RuntimeError('R pad on an unexpected net %s' % q)
            seen.add(q['pad'])
        Mx['pads'].append(q)
    assert seen == {'RA', 'RB'}, (net, rref, seen)
    ea, a1, a3, ra = net_elements(Mx, sn)      # a1 = R pad 1, a3 = real U3 pin
    eb, b1, b3, rb = net_elements(Mx, net)     # b1 = real U1 ball, b3 = R pad 2
    el = _prefix(ea, 'a') + _prefix(eb, 'b') + r_package('a' + a1, 'b' + b3, PLACED['r'], PLACED['pkg'])
    rep = dict(rb)
    rep['u1_pin'], rep['u3_pin'] = rb['u1_pin'], ra['u3_pin']
    rep['len_mm'] = ra['len_mm'] + rb['len_mm']
    rep['delay_ps'] = ra['delay_ps'] + rb['delay_ps']
    rep['vias'] = ra['vias'] + rb['vias']
    rep['tlines'] = ra['tlines'] + rb['tlines']
    rep['lumped'] = ra['lumped'] + rb['lumped']
    rep['feed_mm'], rep['feed_ps'], rep['feed_vias'] = ra['len_mm'], ra['delay_ps'], ra['vias']
    rep['line_mm'], rep['line_ps'], rep['line_vias'] = rb['len_mm'], rb['delay_ps'], rb['vias']
    rep['connected'] = ra['connected'] and rb['connected']
    rep['connected_halves'] = [ra['connected'], rb['connected']]
    return el, 'b' + b1, 'a' + a3, rep


def budget(t, v, rail):
    """DS181 Table 4 usage ratio (UI 7.5 ns), same arithmetic as ds181_check.py / series_study.py"""
    import ds181_check as D
    worst, detail = 0.0, None
    for w in D.windows(t, v, rail):
        for kind, peak, dur, tab in (('over', w['peak_over'], w['t_over_ns'], D.OVER),
                                     ('under', w['peak_under'], w['t_under_ns'], D.UNDER)):
            if peak <= 0.20:
                continue
            used = dur / 7.5 * 100
            lim = D.allowed(tab, peak)
            ratio = used / lim if lim > 0 else 1e9
            if ratio > worst:
                worst, detail = ratio, dict(kind=kind, peak_v=round(peak, 4), dur_ns=round(dur, 4),
                                            used_pct_ui=round(used, 3), allowed_pct_ui=lim)
    return worst, detail


def crossings(t, v, vth=VTH):
    """first and last crossing of vth (ns after the stimulus edge) for each edge in USE_EDGES"""
    out = {}
    nxt = [e[0] for e in EDGES[1:]] + [T_END]
    for (te, kind), tn in zip(EDGES, nxt):
        if (te, kind) not in USE_EDGES:
            continue
        s = (t >= te) & (t < tn)
        tt, vv = t[s], v[s]
        above = vv >= vth
        idx = np.flatnonzero(above[1:] != above[:-1])
        idx = [i for i in idx if (not above[i] and above[i + 1]) == (kind == 'rise')]
        c = []
        for i in idx:
            f = (vth - vv[i]) / (vv[i + 1] - vv[i])
            c.append(float((tt[i] + f * (tt[i + 1] - tt[i]) - te) * 1e9))
        out['%s@%.1f' % (kind, te * 1e9)] = {'first': c[0] if c else None, 'last': c[-1] if c else None, 'n': len(c)}
    return out


def evaluate(tt, vr, vd, vrp, rail, scen):
    res = {'t_end_ns': float(tt[-1] * 1e9), 'reached_t_end': bool(tt[-1] >= T_END * (1 - 1e-6))}
    for name, v in (('die', vr), ('pin', vrp)):
        m = measure(tt, v, rail)
        res[name] = dict(vmin=float(v.min()), vmax=float(v.max()), ringback_into_band=m['ringback_into_band'],
                         t10_90_ns=m['t10_90_ns'], cross_1v4=crossings(tt, v))
        if scen == 'read':
            b, d = budget(tt, v, rail)
            res[name]['budget'] = b
            res[name]['budget_detail'] = d
        else:
            res[name]['abs_max_pass'] = bool(v.max() <= 4.6 and v.min() >= -1.0)
    res['tx_die_cross_1v4'] = crossings(tt, vd)
    return res


def run_case(task):
    """one case per worker process: task = dict(net, scen, corner, stack, mode, r, pkg, src)"""
    global STACK
    net, scen, corner, stack, mode = task['net'], task['scen'], task['corner'], task['stack'], task['mode']
    r, pkgname, src = float(task.get('r', 0.0)), task.get('pkg', 'parts'), task.get('src', 'extract')
    STACK = stack
    key = dict(net=net, scenario=scen, corner=corner, stack=stack, mode=mode, r=r, pkg=pkgname, src=src)
    PLACED.clear()
    os.environ['ZULU_RSER'] = '0'
    try:
        if mode == 'placed':
            E = final_edits(net)
            if net not in E['parts']:
                raise RuntimeError('%s has no R in the plan' % net)
            part = E['parts'][net]
            PLACED.update(split=True, r=r, pkg=PKG[pkgname], rref=part['ref'])
            key['ref'] = part['ref']
            key['r_side'] = part['side']
            key['r_xy'] = [part['x'], part['y']]
            M = extract_model(E)
        else:
            M = json.load(open(MODEL)) if src == 'model' else extract_model(None)
            if mode == 'pin':
                os.environ['ZULU_RSER'] = repr(r)
                PLACED.update(pkg=PKG[pkgname])
        U1, U3 = I.Ibis(U1_IBS), I.Ibis(U3_IBS)
        tt, vr, vd, vrp, vcc, rm, dm, rep = simulate(M, net, scen, corner, U1, U3)
    except Exception as e:
        key['error'] = str(e)[:800]
        return key
    rail = VRAIL[corner]
    if vr.max() < 0.5 * rail or vr.min() > 0.5 * rail:
        key['error'] = 'receiver never switched'
        return key
    key.update(evaluate(tt, vr, vd, vrp, rail, scen))
    key.update(rail=rail, driver_model=dm.name, receiver_model=rm.name, u1_pin=rep['u1_pin'], u3_pin=rep['u3_pin'],
               len_mm=round(rep['len_mm'], 3), flight_ps=round(rep['delay_ps'], 1), vias=rep['vias'],
               tlines=rep['tlines'], lumped=rep['lumped'], connected=rep['connected'])
    for k in ('feed_mm', 'feed_ps', 'feed_vias', 'line_mm', 'line_ps', 'line_vias', 'connected_halves'):
        if k in rep:
            key[k] = round(rep[k], 3) if isinstance(rep[k], float) else rep[k]
    wf = '%s_%s_%s_%s_%s_r%g_%s_%s.npz' % (net, scen, corner, stack, mode, r, pkgname, src)
    np.savez_compressed(os.path.join(WAVE, wf), t=tt, rx_die=vr, tx_die=vd, rx_pin=vrp)
    key['wave'] = 'wave_judge/' + wf
    return key


def main():
    import multiprocessing as mp
    a = sys.argv[1:]

    def opt(k, d):
        return a[a.index(k) + 1] if k in a else d
    mode = opt('--mode', 'placed')
    rs = [float(x) for x in opt('--r', '22').split(',')]
    corners = opt('--corners', 'typ,max').split(',')
    stacks = opt('--stacks', 'fab').split(',')
    scens = opt('--scen', 'read,write').split(',')
    pkgs = opt('--pkg', 'parts').split(',')
    src = opt('--src', 'extract')
    nets = opt('--nets', ','.join(PLAN_NETS if mode == 'placed' else ['D%d' % i for i in range(16)])).split(',')
    workers = min(6, int(opt('--workers', '6')))
    tag = opt('--tag', mode)
    if mode == 'base':
        rs = [0.0]
    tasks = [dict(net=n, scen=sc, corner=c, stack=st, mode=mode, r=r, pkg=p, src=src)
             for st in stacks for p in pkgs for r in rs for c in corners for sc in scens for n in nets]
    out = []
    with mp.Pool(workers, maxtasksperchild=1) as pool:
        for m in pool.imap_unordered(run_case, tasks):
            out.append(m)
            if 'error' in m:
                print('ERROR %s %s %s %s %s r%g: %s' % (m['net'], m['scenario'], m['corner'], m['stack'], m['mode'],
                                                        m['r'], m['error'][:300]), flush=True)
            else:
                b = m['pin'].get('budget')
                print('%-4s %-5s %-3s %-6s %-6s r%-4g %-5s pin %+.3f/%.3f die %+.3f/%.3f %s t_end %.2f conn %s' % (
                    m['net'], m['scenario'], m['corner'], m['stack'], m['mode'], m['r'], m['pkg'], m['pin']['vmin'],
                    m['pin']['vmax'], m['die']['vmin'], m['die']['vmax'],
                    'ball budget %.1f%% die %.1f%%' % (100 * b, 100 * m['die']['budget']) if b is not None else
                    'absmax pin %s die %s' % (m['pin']['abs_max_pass'], m['die']['abs_max_pass']),
                    m['t_end_ns'], m['connected']), flush=True)
    json.dump(out, open(os.path.join(HERE, 'sim_judge_raw_%s.json' % tag), 'w'), indent=1)
    print('done: %d cases, %d errors' % (len(out), sum('error' in m for m in out)))


if __name__ == '__main__':
    os.makedirs(WAVE, exist_ok=True)
    main()
