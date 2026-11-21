"""sim_report.py -- collect d13/sim bus_sim_final.py runs into sim_final.json + sim_final.md.

Simulator: d13/sim/bus_sim_final.py, a byte copy of d10/sim/bus_sim_final.py (md5 3a9ba636).
Inputs (this folder): sim_final_raw_{placed22,base,sweep,repro_d10,repro_d14base}.json and wave_final/.
References (read only): d10/sim/sim_final.json + d10/sim/wave_final (reproduction and the D0-D12 identity check),
d13/combine/sim_final_raw_final.json + d13/combine/wave_final (D13-D15 identity check).

Criteria are those of d10/sim/sim_final_report.py: DS181 Table 4 usage at the U1 ball ('pin') and die, UI 7.5 ns;
writes vs the SDRAM abs max -1.0 / 4.6 V; ringback = re-entry into 0.8-2.0 V after the first threshold crossing;
delay change = first 1.4 V crossing minus the no-R (base, today's copper) run of the same net / scenario / corner /
stack, per edge (8.5 fall, 16.0 rise, 23.5 fall), min..max over the 3 edges.
Added here (from the waves): settle = time after the stimulus edge of the LAST crossing of VIH (rise) / VIL (fall) at
the receiver die, i.e. when the input is valid for good; max over the 3 edges.
"""
import hashlib
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
D13 = os.path.dirname(HERE)
SR = os.path.dirname(D13)
D10S = os.path.join(SR, 'd10', 'sim')
CMB = os.path.join(D13, 'combine')
DN = ['D%d' % i for i in range(16)]
EDGES = [(8.5, 'fall', 16.0), (16.0, 'rise', 23.5), (23.5, 'fall', 32.0)]
VIL, VIH = 0.8, 2.0


def load(tag, d=HERE, pre='sim_final_raw_'):
    p = os.path.join(d, pre + tag + '.json')
    return json.load(open(p)) if os.path.exists(p) else []


RAW = {t: load(t) for t in ('placed22', 'base', 'sweep', 'repro_d10', 'repro_d14base')}
ALL = [r for v in RAW.values() for r in v]
ERR = [r for r in ALL if 'error' in r]
PLAN = os.path.join(D13, 'final_plan.json')
PLAN_MD5 = hashlib.md5(open(PLAN, 'rb').read()).hexdigest()
SIM_MD5 = hashlib.md5(open(os.path.join(HERE, 'bus_sim_final.py'), 'rb').read()).hexdigest()


def find(rows, **k):
    g = [r for r in rows if all(r.get(a) == b for a, b in k.items())]
    assert len(g) <= 1, (k, len(g))
    return g[0] if g else None


def wave(rec, d=HERE):
    return np.load(os.path.join(d, rec['wave']))


def wave_diff(a, b, da=HERE, db=HERE):
    za, zb = wave(a, da), wave(b, db)
    if len(za['t']) != len(zb['t']) or not np.allclose(za['t'], zb['t'], rtol=0, atol=0):
        return None
    return max(float(np.max(np.abs(za[k] - zb[k]))) for k in ('rx_pin', 'rx_die', 'tx_die'))


def xdelta(case, base, node):
    d = []
    for e, c in case[node]['cross_1v4'].items():
        b = base[node]['cross_1v4'][e]
        if c['first'] is not None and b['first'] is not None:
            d.append(c['first'] - b['first'])
    return [round(min(d), 4), round(max(d), 4)]


def settle(rec, node='rx_die'):
    """max over the 3 used edges of the last VIH (rise) / VIL (fall) crossing after the edge, ns"""
    z = wave(rec)
    t, v = z['t'] * 1e9, z[node]
    worst = 0.0
    for te, kind, tn in EDGES:
        s = (t >= te) & (t < tn)
        tt, vv = t[s], v[s]
        bad = vv < VIH if kind == 'rise' else vv > VIL
        idx = np.flatnonzero(bad)
        if len(idx) == len(vv):
            return None
        last = tt[idx[-1] + 1] - te if len(idx) else 0.0
        worst = max(worst, float(last))
    return round(worst, 4)


def row(rows_c, rows_b, stack, net, corner, r=22.0):
    pr = find(rows_c, net=net, corner=corner, scenario='read', stack=stack, r=r)
    pw = find(rows_c, net=net, corner=corner, scenario='write', stack=stack, r=r)
    br = find(rows_b, net=net, corner=corner, scenario='read', stack=stack)
    bw = find(rows_b, net=net, corner=corner, scenario='write', stack=stack)
    if not pr:
        return None
    for x in (pr, pw, br, bw):
        assert x is not None and 'error' not in x, (stack, net, corner, r)
    s = dict(net=net, stack=stack, corner=corner, r_ohm=r, ref=pr.get('ref'), r_side=pr.get('r_side'),
             r_xy=pr.get('r_xy'), feed_mm=pr.get('feed_mm'), feed_vias=pr.get('feed_vias'), line_mm=pr.get('line_mm'),
             line_vias=pr.get('line_vias'), len_mm=pr['len_mm'], connected=bool(pr['connected'] and pw['connected']),
             connected_halves=pr.get('connected_halves'),
             reached_t_end=all(x['reached_t_end'] for x in (pr, pw, br, bw)),
             t_end_ns=round(min(x['t_end_ns'] for x in (pr, pw, br, bw)), 4),
             waves=dict(read=pr['wave'], write=pw['wave'], read_noR=br['wave'], write_noR=bw['wave']))
    s['read'] = dict(ball_budget_pct=round(100 * pr['pin']['budget'], 2),
                     die_budget_pct=round(100 * pr['die']['budget'], 2),
                     ball_budget_detail=pr['pin']['budget_detail'], die_budget_detail=pr['die']['budget_detail'],
                     ball_vmin=round(pr['pin']['vmin'], 4), ball_vmax=round(pr['pin']['vmax'], 4),
                     die_vmin=round(pr['die']['vmin'], 4), die_vmax=round(pr['die']['vmax'], 4),
                     ringback_ball_v=round(pr['pin']['ringback_into_band'], 4),
                     ringback_die_v=round(pr['die']['ringback_into_band'], 4),
                     t10_90_die_ns=round(pr['die']['t10_90_ns'], 4),
                     settle_die_ns=settle(pr), R0_settle_die_ns=settle(br),
                     R0_ball_budget_pct=round(100 * br['pin']['budget'], 2),
                     R0_die_budget_pct=round(100 * br['die']['budget'], 2),
                     R0_ball_vmin=round(br['pin']['vmin'], 4), R0_ball_vmax=round(br['pin']['vmax'], 4),
                     R0_t10_90_die_ns=round(br['die']['t10_90_ns'], 4))
    s['read']['delay_die_ns'] = xdelta(pr, br, 'die')
    s['read']['delay_ball_ns'] = xdelta(pr, br, 'pin')
    s['write'] = dict(u3pin_vmin=round(pw['pin']['vmin'], 4), u3pin_vmax=round(pw['pin']['vmax'], 4),
                      u3die_vmin=round(pw['die']['vmin'], 4), u3die_vmax=round(pw['die']['vmax'], 4),
                      absmax_pass=bool(pw['pin']['abs_max_pass'] and pw['die']['abs_max_pass']),
                      ringback_pin_v=round(pw['pin']['ringback_into_band'], 4),
                      ringback_die_v=round(pw['die']['ringback_into_band'], 4),
                      t10_90_die_ns=round(pw['die']['t10_90_ns'], 4),
                      settle_die_ns=settle(pw), R0_settle_die_ns=settle(bw),
                      R0_u3pin_vmin=round(bw['pin']['vmin'], 4), R0_u3pin_vmax=round(bw['pin']['vmax'], 4))
    s['write']['delay_die_ns'] = xdelta(pw, bw, 'die')
    return s


ROWS = [x for st in ('fab', 'pcbdoc') for c in ('typ', 'max') for n in DN
        for x in [row(RAW['placed22'], RAW['base'], st, n, c)] if x]


def bus(stack, corner):
    g = [r for r in ROWS if r['stack'] == stack and r['corner'] == corner]
    wb = max(g, key=lambda r: (r['read']['ball_budget_pct'], -r['read']['ball_vmin']))
    wd = max(g, key=lambda r: (r['read']['die_budget_pct'], -r['read']['die_vmin']))
    return dict(n_nets=len(g), nets=[r['net'] for r in g], n_with_R=sum(1 for r in g if r['ref']),
                ball_worst_pct=wb['read']['ball_budget_pct'], ball_worst_net=wb['net'],
                die_worst_pct=wd['read']['die_budget_pct'], die_worst_net=wd['net'],
                ball_fails=[r['net'] for r in g if r['read']['ball_budget_pct'] > 100],
                die_fails=[r['net'] for r in g if r['read']['die_budget_pct'] > 100],
                ball_vmin_worst=min(r['read']['ball_vmin'] for r in g),
                ball_vmin_worst_net=min(g, key=lambda r: r['read']['ball_vmin'])['net'],
                ringback_ball_worst_v=max(r['read']['ringback_ball_v'] for r in g),
                ringback_die_worst_v=max(r['read']['ringback_die_v'] for r in g),
                write_u3pin_vmin=min(r['write']['u3pin_vmin'] for r in g),
                write_u3pin_vmax=max(r['write']['u3pin_vmax'] for r in g),
                write_u3die_vmin=min(r['write']['u3die_vmin'] for r in g),
                write_u3die_vmax=max(r['write']['u3die_vmax'] for r in g),
                write_absmax_all_pass=all(r['write']['absmax_pass'] for r in g),
                write_ringback_worst_v=max(max(r['write']['ringback_pin_v'], r['write']['ringback_die_v']) for r in g),
                read_delay_die_ns=[min(r['read']['delay_die_ns'][0] for r in g),
                                   max(r['read']['delay_die_ns'][1] for r in g)],
                write_delay_die_ns=[min(r['write']['delay_die_ns'][0] for r in g),
                                    max(r['write']['delay_die_ns'][1] for r in g)],
                all_connected=all(r['connected'] for r in g), all_reached_t_end=all(r['reached_t_end'] for r in g))


BUS = {'%s|%s' % (s, c): bus(s, c) for s in ('fab', 'pcbdoc') for c in ('typ', 'max')}

# ------------------------------------------------------------------ reproduction of d10/sim/sim_final.json
D10J = json.load(open(os.path.join(D10S, 'sim_final.json')))


def d10row(net, stack, corner):
    return [x for x in D10J['per_net'] if x['net'] == net and x['stack'] == stack and x['corner'] == corner][0]


REPRO = []
for tag, net, stack, mode, src_key in (('repro_d10', 'D10', 'fab', 'placed', 'read'),
                                       ('repro_d14base', 'D14', 'pcbdoc', 'base', 'read_noR')):
    m = RAW[tag][0]
    ref = d10row(net, stack, 'max')
    refwave = ref['waves'][src_key]
    z_ref = np.load(os.path.join(D10S, refwave))
    z = wave(m)
    same_t = len(z['t']) == len(z_ref['t']) and bool(np.array_equal(z['t'], z_ref['t']))
    dv = max(float(np.max(np.abs(z[k] - z_ref[k]))) for k in ('rx_pin', 'rx_die', 'tx_die')) if same_t else None
    if mode == 'placed':
        mine = dict(ball=round(100 * m['pin']['budget'], 2), die=round(100 * m['die']['budget'], 2),
                    vmin=round(m['pin']['vmin'], 4), len=m['len_mm'])
        theirs = dict(ball=ref['read']['ball_budget_pct'], die=ref['read']['die_budget_pct'],
                      vmin=ref['read']['ball_vmin'], len=ref['len_mm'])
    else:
        mine = dict(ball=round(100 * m['pin']['budget'], 2), die=round(100 * m['die']['budget'], 2),
                    vmin=round(m['pin']['vmin'], 4))
        theirs = dict(ball=ref['read']['R0_ball_budget_pct'], die=ref['read']['R0_die_budget_pct'],
                      vmin=ref['read']['R0_ball_vmin'])
    REPRO.append(dict(case='%s read max %s %s' % (net, stack, mode), plan=m.get('plan'), plan_md5=m.get('plan_md5'),
                      new=mine, d10=theirs, d10_wave='d10/sim/' + refwave, same_timebase=same_t, max_abs_dv=dv,
                      agree=same_t and dv == 0.0 and mine == theirs))

# ------------------------------------------------------------------ identity checks of the whole run
IDENT = []
d10raw = {t: load(t, D10S) for t in ('placed_fab', 'placed_pcbdoc', 'base_fab', 'base_pcbdoc')}
cmbraw = load('final', CMB)
for m in RAW['placed22'] + RAW['base']:
    if 'error' in m:
        continue
    k = dict(net=m['net'], scenario=m['scenario'], corner=m['corner'], stack=m['stack'])
    if m['mode'] == 'base':
        g = find(d10raw['base_' + m['stack']], **k)
        src, d = 'd10 base', D10S
    elif m['net'] in ('D13', 'D14', 'D15'):
        g = find(cmbraw, **k)
        src, d = 'd13/combine', CMB
    else:
        g = find(d10raw['placed_' + m['stack']], **k)
        src, d = 'd10 placed (13-R plan)', D10S
    if g is None or 'error' in g:
        continue
    IDENT.append(dict(src=src, mode=m['mode'], dv=wave_diff(m, g, HERE, d), **k))
IDSUM = {}
for x in IDENT:
    s = IDSUM.setdefault(x['src'], dict(n=0, identical=0, max_dv=0.0, timebase_differs=0))
    s['n'] += 1
    if x['dv'] is None:
        s['timebase_differs'] += 1
    else:
        s['identical'] += x['dv'] == 0.0
        s['max_dv'] = max(s['max_dv'], x['dv'])

# ------------------------------------------------------------------ R sweep on the PcbDoc stack
pc_max = [r for r in ROWS if r['stack'] == 'pcbdoc' and r['corner'] == 'max']
WORST4 = [r['net'] for r in sorted(pc_max, key=lambda r: (-r['read']['ball_budget_pct'], -r['read']['die_budget_pct'],
                                                          r['read']['ball_vmin']))[:4]]
SWEEP_NETS = sorted({m['net'] for m in RAW['sweep']}, key=lambda n: int(n[1:]))
SWEEP = []
for n in SWEEP_NETS:
    for c in ('typ', 'max'):
        for rv in (15.0, 22.0, 33.0):
            x = row(RAW['sweep'] if rv != 22.0 else RAW['placed22'], RAW['base'], 'pcbdoc', n, c, rv)
            if x:
                SWEEP.append(x)

OUT = dict(plan='d13/final_plan.json', plan_md5=PLAN_MD5, pcbdoc_md5='2a616c1c74f8788a4a1c837c7d76c3b0',
           board_extract_md5='81469ef0881851109d76126db08dc5e8',
           simulator='d13/sim/bus_sim_final.py (byte copy of d10/sim/bus_sim_final.py)', simulator_md5=SIM_MD5,
           r_ohm=22.0, pkg='parts: ESL 0.5 nH, 0.05 pF across, 0.08 pF per pad to ground', ui_ns=7.5,
           counts=dict(cases=len(ALL), errors=len(ERR),
                       not_reaching_t_end=sum(1 for r in ALL if 'error' not in r and not r['reached_t_end']),
                       not_connected=sum(1 for r in ALL if 'error' not in r and not r['connected']),
                       t_end_ns=32.0, max_workers=6, per_tag={k: len(v) for k, v in RAW.items()}),
           reproduction=REPRO, identity_summary=IDSUM, identity=IDENT, bus=BUS, per_net=ROWS,
           sweep_worst4_pcbdoc_max=WORST4, sweep_nets=SWEEP_NETS, sweep=SWEEP)
json.dump(OUT, open(os.path.join(HERE, 'sim_final.json'), 'w'), indent=1)
print(json.dumps(dict(counts=OUT['counts'], repro=REPRO, ident=IDSUM, worst4=WORST4), indent=1))
