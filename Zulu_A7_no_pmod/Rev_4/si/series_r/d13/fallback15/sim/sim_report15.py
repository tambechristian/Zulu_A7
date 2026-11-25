"""sim_report15.py -- collect the fallback15 (15-R plan, D13 without R) runs into sim_fb15.json.

Inputs (this folder): sim_final_raw_{p15,spot_d8,spot_d10}.json + wave_final/ (bus_sim_final.py copy, placed mode,
22 ohm, parts 0201 model, plan = ../plan15.json).
References (read only): d13/sim/sim_final_raw_{placed22,base}.json + d13/sim/wave_final/ (the 16-R study).
Row arithmetic = d13/sim/sim_report.py row(): ball/die = DS181 Table 4 usage at U1 ball ('pin') / die; delay = first
1.4 V crossing minus the no-R (base, today's copper) run, min..max over the 3 used edges.
Identity: D14/D15/D8/D10 vs the 16-R placed22 run of the same case; D13 vs the 16-R BASE (no-R) run.
"""
import hashlib
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FB = os.path.dirname(HERE)
D13 = os.path.dirname(FB)
S16 = os.path.join(D13, 'sim')
PLAN = os.path.join(FB, 'plan15.json')
EDGES = [(8.5, 'fall', 16.0), (16.0, 'rise', 23.5), (23.5, 'fall', 32.0)]
VIL, VIH = 0.8, 2.0
META = {'plan', 'plan_md5', 'wave', 'mode', 'ref', 'r_side', 'r_xy', 'r', 'feed_mm', 'feed_ps', 'feed_vias', 'line_mm',
        'line_ps', 'line_vias', 'connected_halves'}


def load(d, tag):
    return json.load(open(os.path.join(d, 'sim_final_raw_%s.json' % tag)))


NEW = load(HERE, 'p15') + load(HERE, 'spot_d8') + load(HERE, 'spot_d10')
P22 = load(S16, 'placed22')
BASE = load(S16, 'base')


def find(rows, **k):
    g = [r for r in rows if all(r.get(a) == b for a, b in k.items())]
    assert len(g) <= 1, (k, len(g))
    return g[0] if g else None


def wave(rec, d):
    return np.load(os.path.join(d, rec['wave']))


def wave_cmp(a, da, b, db):
    za, zb = wave(a, da), wave(b, db)
    same_t = len(za['t']) == len(zb['t']) and bool(np.array_equal(za['t'], zb['t']))
    if not same_t:
        return dict(same_timebase=False, n=len(za['t']), n_ref=len(zb['t']), max_abs_dv=None)
    return dict(same_timebase=True, n=len(za['t']),
                max_abs_dv=max(float(np.max(np.abs(za[k] - zb[k]))) for k in ('rx_pin', 'rx_die', 'tx_die')),
                bit_identical=all(bool(np.array_equal(za[k], zb[k])) for k in ('t', 'rx_pin', 'rx_die', 'tx_die')))


def metrics_equal(a, b):
    ka = {k: v for k, v in a.items() if k not in META}
    kb = {k: v for k, v in b.items() if k not in META}
    diff = sorted(k for k in set(ka) | set(kb) if ka.get(k) != kb.get(k))
    return diff


def xdelta(case, base, node):
    d = []
    for e, c in case[node]['cross_1v4'].items():
        b = base[node]['cross_1v4'][e]
        if c['first'] is not None and b['first'] is not None:
            d.append(c['first'] - b['first'])
    return [round(min(d), 4), round(max(d), 4)]


def settle(rec, d, node='rx_die'):
    z = wave(rec, d)
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


# ------------------------------------------------------------------ identity
IDENT = []
for m in NEW:
    assert 'error' not in m, m
    k = dict(net=m['net'], scenario=m['scenario'], corner=m['corner'], stack=m['stack'])
    if m['net'] == 'D13':
        ref, src = find(BASE, **k), '16-R study BASE (no R, today copper)'
    else:
        ref, src = find(P22, **k), '16-R study placed22'
    c = wave_cmp(m, HERE, ref, S16)
    x = dict(src=src, ref_wave='d13/sim/' + ref['wave'], new_wave='d13/fallback15/sim/' + m['wave'],
             metric_keys_differing=metrics_equal(m, ref), **k, **c)
    if m['net'] == 'D13':                     # also show how far D13 moved from the 16-R (R132) run
        p = find(P22, **k)
        x['vs_16R_placed22_with_R132'] = wave_cmp(m, HERE, p, S16)
    IDENT.append(x)

# ------------------------------------------------------------------ table rows (D13-D15, both stacks, both corners)
ROWS = []
for st in ('fab', 'pcbdoc'):
    for c in ('typ', 'max'):
        for n in ('D13', 'D14', 'D15'):
            pr = find(NEW, net=n, corner=c, scenario='read', stack=st)
            pw = find(NEW, net=n, corner=c, scenario='write', stack=st)
            br = find(BASE, net=n, corner=c, scenario='read', stack=st)
            bw = find(BASE, net=n, corner=c, scenario='write', stack=st)
            ROWS.append(dict(
                net=n, stack=st, corner=c, ref=pr.get('ref'), r_ohm=22.0 if pr.get('ref') else 0.0,
                r_side=pr.get('r_side'), r_xy=pr.get('r_xy'), len_mm=pr['len_mm'],
                connected=bool(pr['connected'] and pw['connected']),
                reached_t_end=all(x['reached_t_end'] for x in (pr, pw)),
                read=dict(ball_budget_pct=round(100 * pr['pin']['budget'], 2),
                          die_budget_pct=round(100 * pr['die']['budget'], 2),
                          ball_budget_detail=pr['pin']['budget_detail'], die_budget_detail=pr['die']['budget_detail'],
                          ball_vmin=round(pr['pin']['vmin'], 4), ball_vmax=round(pr['pin']['vmax'], 4),
                          die_vmin=round(pr['die']['vmin'], 4), die_vmax=round(pr['die']['vmax'], 4),
                          ringback_ball_v=round(pr['pin']['ringback_into_band'], 4),
                          ringback_die_v=round(pr['die']['ringback_into_band'], 4),
                          settle_die_ns=settle(pr, HERE),
                          delay_die_ns=xdelta(pr, br, 'die'), delay_ball_ns=xdelta(pr, br, 'pin')),
                write=dict(u3pin_vmin=round(pw['pin']['vmin'], 4), u3pin_vmax=round(pw['pin']['vmax'], 4),
                           u3die_vmin=round(pw['die']['vmin'], 4), u3die_vmax=round(pw['die']['vmax'], 4),
                           absmax_pass=bool(pw['pin']['abs_max_pass'] and pw['die']['abs_max_pass']),
                           ringback_pin_v=round(pw['pin']['ringback_into_band'], 4),
                           ringback_die_v=round(pw['die']['ringback_into_band'], 4),
                           delay_die_ns=xdelta(pw, bw, 'die')),
                waves=dict(read=pr['wave'], write=pw['wave'])))

SPOT = []
for m in NEW:
    if m['net'] in ('D8', 'D10'):
        SPOT.append(dict(net=m['net'], scenario=m['scenario'], corner=m['corner'], stack=m['stack'], ref=m['ref'],
                         ball_budget_pct=round(100 * m['pin']['budget'], 2), die_budget_pct=round(100 * m['die']['budget'], 2),
                         ball_vmin=round(m['pin']['vmin'], 4), len_mm=m['len_mm']))

ok = all(x['same_timebase'] and x['max_abs_dv'] == 0.0 and not x['metric_keys_differing'] for x in IDENT)
OUT = dict(plan='d13/fallback15/plan15.json', plan_md5=hashlib.md5(open(PLAN, 'rb').read()).hexdigest(),
           simulator='d13/fallback15/sim/bus_sim_final.py (copy of d13/sim/bus_sim_final.py md5 3a9ba636, SR path only)',
           simulator_md5=hashlib.md5(open(os.path.join(HERE, 'bus_sim_final.py'), 'rb').read()).hexdigest(),
           r_ohm=22.0, pkg='parts: ESL 0.5 nH, 0.05 pF across, 0.08 pF per pad to ground', ui_ns=7.5,
           cases=len(NEW), errors=sum('error' in m for m in NEW),
           identity_all_zero=ok, identity=IDENT, rows=ROWS, spot=SPOT)
json.dump(OUT, open(os.path.join(HERE, 'sim_fb15.json'), 'w'), indent=1)
print('cases', len(NEW), 'identity_all_zero', ok)
for x in IDENT:
    print('%-4s %-5s %-3s %-6s vs %-40s same_t %s max|dV| %s bit %s keys %s%s' % (
        x['net'], x['scenario'], x['corner'], x['stack'], x['src'], x['same_timebase'], x['max_abs_dv'],
        x.get('bit_identical'), x['metric_keys_differing'],
        ('  [vs R132 run: max|dV| %.4f V]' % x['vs_16R_placed22_with_R132']['max_abs_dv'])
        if 'vs_16R_placed22_with_R132' in x and x['vs_16R_placed22_with_R132']['max_abs_dv'] is not None else ''))
for r in ROWS:
    a, w = r['read'], r['write']
    print('%-4s %-5s %-6s %-3s ball %7.2f%% die %6.2f%% Vmin %+.4f rb %.4f/%.4f | W pin %+.4f/%.4f die %+.4f/%.4f rb %.4f/%.4f | '
          'dly R %s W %s' % (r['net'], r['ref'], r['stack'], r['corner'], a['ball_budget_pct'], a['die_budget_pct'],
                             a['ball_vmin'], a['ringback_ball_v'], a['ringback_die_v'], w['u3pin_vmin'], w['u3pin_vmax'],
                             w['u3die_vmin'], w['u3die_vmax'], w['ringback_pin_v'], w['ringback_die_v'],
                             a['delay_die_ns'], w['delay_die_ns']))
print(json.dumps(SPOT))
