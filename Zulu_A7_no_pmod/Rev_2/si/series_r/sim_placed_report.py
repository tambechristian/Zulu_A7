"""sim_placed_report.py -- collect bus_sim_placed.py runs into sim_placed.json + sim_placed.md (this folder only).

Inputs (all in this folder): sim_placed_raw_{base_fab,pin_check,placed_fab,pkg_sens,base_pcbdoc,placed_pcbdoc}.json
and their waves in wave_placed/; the pin-position reference = si/spice/wave/<net>_<scen>_<corner>_fab{,_r15,_r22,_r33}.npz
(bus_sim.py's ZULU_RSER runs behind results_all/r15/r22/r33.json), evaluated here with the SAME evaluate() as the
placed runs (DS181 Table 4 at UI 7.5 ns, ds181_check arithmetic; SDRAM abs max 4.6 / -1.0 V; ringback; 10-90 %;
1.4 V crossings). Delay change = first 1.4 V crossing minus the no-resistor run's, per edge (8.5 fall, 16.0 rise,
23.5 fall), same net / scenario / corner / stack; reported as the min..max over the three edges.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SPW = os.path.join(os.path.dirname(HERE), 'spice', 'wave')
sys.path.insert(0, HERE)
import bus_sim_placed as P    # noqa: E402  (evaluate() only; no simulation is run here)

DN = ['D%d' % i for i in range(16)]
RAW = {}
for tag in ('base_fab', 'pin_check', 'placed_fab', 'pkg_sens', 'base_pcbdoc', 'placed_pcbdoc'):
    f = os.path.join(HERE, 'sim_placed_raw_%s.json' % tag)
    if os.path.exists(f):
        RAW[tag] = json.load(open(f))
ALL = [r for v in RAW.values() for r in v]
ERR = [r for r in ALL if 'error' in r]
OK = [r for r in ALL if 'error' not in r]


def find(rows, **k):
    g = [r for r in rows if all(r.get(a) == b for a, b in k.items())]
    assert len(g) <= 1, (k, len(g))
    return g[0] if g else None


def xdelta(case, base, node):
    """min..max over edges of the first-crossing shift (ns) at node ('die'/'pin') vs base"""
    d, dl = [], []
    for e, c in case[node]['cross_1v4'].items():
        b = base[node]['cross_1v4'][e]
        if c['first'] is not None and b['first'] is not None:
            d.append(c['first'] - b['first'])
        if c['last'] is not None and b['last'] is not None:
            dl.append(c['last'] - b['last'])
    return dict(first_min=min(d), first_max=max(d), last_min=min(dl), last_max=max(dl),
                multi_crossings=sum(c['n'] > 1 for c in case[node]['cross_1v4'].values()))


def pin_ref(net, scen, corner, r):
    tag = '' if r == 0 else '_r%d' % r
    f = os.path.join(SPW, '%s_%s_%s_fab%s.npz' % (net, scen, corner, tag))
    if not os.path.exists(f):
        return None
    z = np.load(f)
    res = P.evaluate(z['t'], z['rx_die'], z['tx_die'], z['rx_pin'], P.VRAIL[corner], scen)
    res.update(net=net, scenario=scen, corner=corner, stack='fab', mode='pin_ref', r=float(r), pkg='ideal',
               src='si/spice/wave/' + os.path.basename(f))
    return res


def summary_row(r, base):
    s = dict(net=r['net'], scenario=r['scenario'], corner=r['corner'], stack=r['stack'], mode=r['mode'], r=r['r'],
             pkg=r['pkg'], ref=r.get('ref'), reached_t_end=r['reached_t_end'], t_end_ns=round(r['t_end_ns'], 3))
    for node in ('die', 'pin'):
        n = r[node]
        s[node + '_vmin'] = round(n['vmin'], 4)
        s[node + '_vmax'] = round(n['vmax'], 4)
        s[node + '_ringback'] = round(n['ringback_into_band'], 4)
        s[node + '_t10_90_ns'] = None if n['t10_90_ns'] is None else round(n['t10_90_ns'], 4)
        if r['scenario'] == 'read':
            s[node + '_budget_pct'] = round(100 * n['budget'], 2)
            s[node + '_budget_detail'] = n['budget_detail']
        else:
            s[node + '_absmax_pass'] = n['abs_max_pass']
        if base is not None:
            s[node + '_dly_vs_noR_ns'] = {k: round(v, 4) if isinstance(v, float) else v
                                          for k, v in xdelta(r, base, node).items()}
    for k in ('len_mm', 'feed_mm', 'feed_ps', 'feed_vias', 'line_mm', 'line_vias', 'vias', 'connected', 'r_side',
              'r_xy', 'wave', 'src'):
        if k in r:
            s[k] = r[k]
    return s


PLAN = ['D%d' % i for i in range(10)] + ['D11', 'D12']
NOR = ['D10', 'D13', 'D14', 'D15']


def group_stats(g, scen):
    if not g:
        return None
    s = dict(n=len(g), nets=sorted({r['net'] for r in g}, key=lambda x: int(x[1:])))
    s['t10_90_die_ns'] = [round(min(r['die_t10_90_ns'] for r in g), 3), round(max(r['die_t10_90_ns'] for r in g), 3)]
    s['ringback_die_worst_v'] = round(max(r['die_ringback'] for r in g), 4)
    s['ringback_pin_worst_v'] = round(max(r['pin_ringback'] for r in g), 4)
    d = [r['die_dly_vs_noR_ns'] for r in g if 'die_dly_vs_noR_ns' in r]
    if d:
        s['dly_die_first_ns'] = [round(min(x['first_min'] for x in d), 4), round(max(x['first_max'] for x in d), 4)]
        s['dly_die_last_ns'] = [round(min(x['last_min'] for x in d), 4), round(max(x['last_max'] for x in d), 4)]
    p = [r['pin_dly_vs_noR_ns'] for r in g if 'pin_dly_vs_noR_ns' in r]
    if p:
        s['dly_pin_first_ns'] = [round(min(x['first_min'] for x in p), 4), round(max(x['first_max'] for x in p), 4)]
    if scen == 'read':
        wb = max(g, key=lambda r: r['pin_budget_pct'])
        wd = max(g, key=lambda r: r['die_budget_pct'])
        s.update(ball_budget_worst_pct=wb['pin_budget_pct'], ball_budget_worst_net=wb['net'],
                 die_budget_worst_pct=wd['die_budget_pct'], die_budget_worst_net=wd['net'],
                 ball_fails=sorted([r['net'] for r in g if r['pin_budget_pct'] > 100], key=lambda x: int(x[1:])),
                 die_fails=sorted([r['net'] for r in g if r['die_budget_pct'] > 100], key=lambda x: int(x[1:])),
                 ball_vmin=round(min(r['pin_vmin'] for r in g), 4), ball_vmax=round(max(r['pin_vmax'] for r in g), 4),
                 die_vmin=round(min(r['die_vmin'] for r in g), 4), die_vmax=round(max(r['die_vmax'] for r in g), 4))
    else:
        s.update(u3pin_vmin=round(min(r['pin_vmin'] for r in g), 4), u3pin_vmax=round(max(r['pin_vmax'] for r in g), 4),
                 u3die_vmin=round(min(r['die_vmin'] for r in g), 4), u3die_vmax=round(max(r['die_vmax'] for r in g), 4),
                 absmax_all_pass=all(r['pin_absmax_pass'] and r['die_absmax_pass'] for r in g))
    return s


def summarise(rows, pref):
    S = {}
    for stack in ('fab', 'pcbdoc'):
        for c in ('typ', 'max'):
            for sc in ('read', 'write'):
                base = [r for r in rows if r['mode'] == 'base' and r['stack'] == stack and r['corner'] == c and r['scenario'] == sc]
                k = '%s|%s|%s' % (stack, c, sc)
                S[k + '|R0_today|plan12'] = group_stats([r for r in base if r['net'] in PLAN], sc)
                S[k + '|R0_today|all16'] = group_stats(base, sc)
                for R in (15.0, 22.0, 33.0):
                    pl = [r for r in rows if r['mode'] == 'placed' and r['pkg'] == 'parts' and r['stack'] == stack and
                          r['corner'] == c and r['scenario'] == sc and r['r'] == R]
                    S[k + '|placed_r%g|plan12' % R] = group_stats([r for r in pl if r['net'] in PLAN], sc)
                    # the whole bus as the plan leaves it: 12 placed + D10/D13/D14/D15 unchanged (D15 without R134)
                    whole = [r for r in pl if r['net'] in PLAN] + [r for r in base if r['net'] in NOR]
                    S[k + '|placed_r%g|all16_as_planned' % R] = group_stats(whole, sc) if len(whole) == 16 else None
                    d15 = [r for r in pl if r['net'] == 'D15']
                    S[k + '|placed_r%g|D15_optional' % R] = group_stats(d15, sc)
                    if stack == 'fab':
                        pr = [r for r in pref if r['corner'] == c and r['scenario'] == sc and r['r'] == R]
                        S[k + '|pin_r%g|plan12' % R] = group_stats([r for r in pr if r['net'] in PLAN], sc)
                        S[k + '|pin_r%g|all16' % R] = group_stats(pr, sc)
                for pk in ('light', 'ideal'):
                    pl = [r for r in rows if r['mode'] == 'placed' and r['pkg'] == pk and r['stack'] == stack and
                          r['corner'] == c and r['scenario'] == sc]
                    S[k + '|placed_r22_%s|plan12' % pk] = group_stats([r for r in pl if r['net'] in PLAN], sc)
    return {k: v for k, v in S.items() if v}


def f1(x, nd=2):
    return '-' if x is None else ('%.*f' % (nd, x))


def pct(x):
    # ds181 convention: a peak beyond the last Table 4 row has 0 % allowed -> ratio 1e9 (bus_sim's 'inf')
    return 'off table' if x >= 1e8 else '%.1f %%' % x


def write_md(out, rows, pref):
    S = out['summary']
    L = []
    L.append('# Series R at its planned position: SI re-simulation\n')
    L.append('The source of every number is `sim_placed.json` (written by `sim_placed_report.py`) and the '
             '`sim_placed_raw_*.json` runs of `bus_sim_placed.py`. That script is a copy of `si/spice/bus_sim.py` '
             'with a PLACED option; the original is not edited. Board: `board_extract.json` (PcbDoc md5 2a616c1c) '
             'with the judge\'s FINAL copper edits applied by `judge_check.py`\'s own plan readers. The R is the '
             'parts.md 0201 model unless stated: 0.5 nH ESL, 0.05 pF across, 0.08 pF per pad to ground.\n')
    c = out['counts']
    L.append('Cases: %d, errors: %d, runs not reaching t_end 32 ns: %d. Each case ran in its own process, with at most 6 '
             'workers.\n' % (c['cases'], c['errors'], c['not_reaching_t_end']))
    rc = [x for x in out['reproduction_checks'] if x['max_abs_diff_v'] is not None]
    if rc:
        L.append('Reproduction check: %d runs of today\'s copper (and the R-at-pin check cases) were compared with '
                 'si/spice/wave. The largest |dV| at the receiver pin is %.3g V.\n' % (len(rc), max(x['max_abs_diff_v'] for x in rc)))
    L.append('## 1. Bus summary, fab stack (DS181 Table 4 at UI 7.5 ns; % = share of the allowed time used)\n')
    L.append('Columns: "R0 today" is the board as it is. "pin" is the R at U3\'s pin (ideal R, from si/spice/wave). '
             '"placed" is the R at the planned position with the 0201 model. Read rows cover the 12 nets that get an '
             'R; write rows cover the same 12 nets. The undershoot limit at U3 is the SDRAM\'s -1.0 / 4.6 V. Delay is '
             'the shift of the first 1.4 V crossing at the receiver die, compared with the no-R run '
             '(min..max over 3 edges and all nets).\n')
    L.append('| corner | case | READ worst ball budget (net) | ball fails | worst die budget | ball Vmin | ringback die / ball | t10-90 die ns | delay die ns | WRITE U3 pin Vmin/Vmax | abs-max | write ringback die / pin | write delay ns |')
    L.append('|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for cn in ('typ', 'max'):
        for case in ['R0_today'] + ['%s_r%d' % (m, R) for R in (15, 22, 33) for m in ('pin', 'placed')]:
            rd = S.get('fab|%s|read|%s|plan12' % (cn, case))
            wr = S.get('fab|%s|write|%s|plan12' % (cn, case))
            if not rd or not wr:
                continue
            L.append('| %s | %s | %s (%s) | %s | %.1f %% | %+.3f | %.3f / %.3f | %.2f-%.2f | %s | %+.3f / %.3f | %s | %.3f / %.3f | %s |' % (
                cn, case, pct(rd['ball_budget_worst_pct']), rd['ball_budget_worst_net'], len(rd['ball_fails']) or 0,
                rd['die_budget_worst_pct'], rd['ball_vmin'], rd['ringback_die_worst_v'], rd['ringback_pin_worst_v'], rd['t10_90_die_ns'][0],
                rd['t10_90_die_ns'][1], '%+.3f..%+.3f' % tuple(rd['dly_die_first_ns']) if 'dly_die_first_ns' in rd else '-',
                wr['u3pin_vmin'], wr['u3pin_vmax'], 'PASS' if wr['absmax_all_pass'] else 'FAIL', wr['ringback_die_worst_v'], wr['ringback_pin_worst_v'],
                '%+.3f..%+.3f' % tuple(wr['dly_die_first_ns']) if 'dly_die_first_ns' in wr else '-'))
    L.append('\nA ringback value > 0 means the waveform re-enters the 0.8-2.0 V band by that many volts after its first '
             'crossing; a value <= 0 means it does not.\n')
    L.append('## 2. Whole bus as planned (12 placed R + D10/D13/D14/D15 unchanged), fab, READ\n')
    L.append('| corner | R | worst ball budget (net) | nets failing at the ball | nets failing at the die |')
    L.append('|---|---|---|---|---|')
    for cn in ('typ', 'max'):
        for R in (15, 22, 33):
            s = S.get('fab|%s|read|placed_r%d|all16_as_planned' % (cn, R))
            if s:
                L.append('| %s | %d | %.1f %% (%s) | %s | %s |' % (cn, R, s['ball_budget_worst_pct'], s['ball_budget_worst_net'],
                                                             ', '.join(s['ball_fails']) or 'none', ', '.join(s['die_fails']) or 'none'))
    L.append('\n## 3. Per net, fab, max corner (planned value 22 ohm)\n')
    L.append('| net | R ref / side | U3 pin to R copper mm (vias) | R0 ball budget | pin-R22 ball budget | placed-R22 ball Vmin | placed-R22 ball budget | die budget | read t10-90 ns | read delay die ns | write U3 pin Vmin/Vmax | write delay ns |')
    L.append('|---|---|---|---|---|---|---|---|---|---|---|---|')
    for n in DN:
        b = find([r for r in rows if r['mode'] == 'base' and r['stack'] == 'fab'], net=n, scenario='read', corner='max')
        p = find([r for r in pref if r['r'] == 22.0], net=n, scenario='read', corner='max')
        pl = find([r for r in rows if r['mode'] == 'placed' and r['pkg'] == 'parts' and r['stack'] == 'fab' and r['r'] == 22.0],
                  net=n, scenario='read', corner='max')
        pw = find([r for r in rows if r['mode'] == 'placed' and r['pkg'] == 'parts' and r['stack'] == 'fab' and r['r'] == 22.0],
                  net=n, scenario='write', corner='max')
        if pl is None:
            L.append('| %s | no R | - | %s | %s | - | - | - | - | - | - | - |' % (
                n, pct(b['pin_budget_pct']), '%.1f %%' % p['pin_budget_pct'] if p else '-'))
            continue
        dd = pl.get('die_dly_vs_noR_ns', {})
        wd = pw.get('die_dly_vs_noR_ns', {}) if pw else {}
        L.append('| %s%s | %s %s | %.2f (%d) | %s | %s | %+.3f | %.2f %% | %.2f %% | %.2f | %s | %s | %s |' % (
            n, ' (optional)' if n == 'D15' else '', pl['ref'], pl['r_side'], pl['feed_mm'], pl['feed_vias'],
            pct(b['pin_budget_pct']), '%.1f %%' % p['pin_budget_pct'] if p else '-', pl['pin_vmin'], pl['pin_budget_pct'],
            pl['die_budget_pct'], pl['die_t10_90_ns'],
            '%+.3f..%+.3f' % (dd['first_min'], dd['first_max']) if dd else '-',
            '%+.3f / %.3f' % (pw['pin_vmin'], pw['pin_vmax']) if pw else '-',
            '%+.3f..%+.3f' % (wd['first_min'], wd['first_max']) if wd else '-'))
    L.append('\n## 4. Package-model sensitivity (fab, max, 22 ohm, 12 plan nets)\n')
    L.append('| package | worst read ball budget (net) | ball Vmin | worst die budget | write U3 pin Vmin/Vmax |')
    L.append('|---|---|---|---|---|')
    for pk, key in (('ideal R', 'placed_r22_ideal'), ('light 0.3 nH / 0.03 pF / 0.04 pF', 'placed_r22_light'),
                    ('parts 0.5 nH / 0.05 pF / 0.08 pF', 'placed_r22')):
        rd, wr = S.get('fab|max|read|%s|plan12' % key), S.get('fab|max|write|%s|plan12' % key)
        if rd and wr:
            L.append('| %s | %.2f %% (%s) | %+.3f | %.2f %% | %+.3f / %.3f |' % (pk, rd['ball_budget_worst_pct'], rd['ball_budget_worst_net'],
                                                                         rd['ball_vmin'], rd['die_budget_worst_pct'], wr['u3pin_vmin'], wr['u3pin_vmax']))
    pc = [r for r in rows if r['stack'] == 'pcbdoc']
    if pc:
        L.append('\n## 5. PcbDoc stack, worst nets\n')
        L.append('| net | corner | case | read ball budget | read die budget | ball Vmin | write U3 pin Vmin/Vmax | abs-max |')
        L.append('|---|---|---|---|---|---|---|---|')
        for n in sorted({r['net'] for r in pc}, key=lambda x: int(x[1:])):
            for cn in ('typ', 'max'):
                for mode, R in (('base', 0.0), ('placed', 15.0), ('placed', 22.0), ('placed', 33.0)):
                    rd = find(pc, net=n, corner=cn, scenario='read', mode=mode, r=R)
                    wr = find(pc, net=n, corner=cn, scenario='write', mode=mode, r=R)
                    if rd and wr:
                        L.append('| %s | %s | %s | %s | %.1f %% | %+.3f | %+.3f / %.3f | %s |' % (
                            n, cn, 'R0 today' if mode == 'base' else 'placed %g' % R, pct(rd['pin_budget_pct']), rd['die_budget_pct'],
                            rd['pin_vmin'], wr['pin_vmin'], wr['pin_vmax'], 'PASS' if wr['pin_absmax_pass'] and wr['die_absmax_pass'] else 'FAIL'))
    notes = os.path.join(HERE, 'sim_placed_notes.md.in')     # hand-written findings, inserted after the title
    if os.path.exists(notes):
        L.insert(1, open(notes).read())
    open(os.path.join(HERE, 'sim_placed.md'), 'w').write('\n'.join(L) + '\n')


def main():
    out = dict(source=dict(
        script='si/series_r/bus_sim_placed.py (copy of si/spice/bus_sim.py + PLACED option) and sim_placed_report.py',
        board='board_extract.json (PcbDoc md5 2a616c1c) + judge FINAL edits via judge_check.plan_arrays/plan_top/plan_judge_d9',
        package={k: v for k, v in P.PKG.items()}, criteria='DS181 Table 4 UI 7.5 ns (ds181_check), SDRAM abs max 4.6/-1.0 V, '
        'ringback into 0.8-2.0 V, 10-90 %, 1.4 V crossing shift vs no R'),
        counts=dict(cases=len(ALL), errors=len(ERR), not_reaching_t_end=sum(not r['reached_t_end'] for r in OK)),
        errors=[{k: r[k] for k in ('net', 'scenario', 'corner', 'stack', 'mode', 'r', 'pkg', 'error')} for r in ERR])
    bases = [r for r in OK if r['mode'] == 'base']
    rows = []
    for r in OK:
        b = find(bases, net=r['net'], scenario=r['scenario'], corner=r['corner'], stack=r['stack'])
        rows.append(summary_row(r, b))
    # pin-position reference (R at U3's pin, ideal R, model.json copper = identical to the extract, see check)
    pref = []
    for rr in (0, 15, 22, 33):
        for n in DN:
            for sc in ('read', 'write'):
                for c in ('typ', 'max'):
                    x = pin_ref(n, sc, c, rr)
                    if x is None:
                        continue
                    b = find(bases, net=n, scenario=sc, corner=c, stack='fab')
                    pref.append(summary_row(dict(x, reached_t_end=x['reached_t_end'], t_end_ns=x['t_end_ns']), b))
    out['cases'] = rows
    out['pin_position_reference'] = pref
    # reproduction checks
    chk = []
    for r in OK:
        if r['mode'] == 'base' and r['stack'] == 'fab':
            f = os.path.join(SPW, '%s_%s_%s_fab.npz' % (r['net'], r['scenario'], r['corner']))
            if os.path.exists(f):
                a, z = np.load(f), np.load(os.path.join(HERE, r['wave']))
                same = float(np.abs(a['rx_pin'] - z['rx_pin']).max()) if len(a['t']) == len(z['t']) else None
                chk.append(dict(case='base %s %s %s vs si/spice R=0' % (r['net'], r['scenario'], r['corner']),
                                max_abs_diff_v=same))
        if r['mode'] == 'pin':
            f = os.path.join(SPW, '%s_%s_%s_fab_r%d.npz' % (r['net'], r['scenario'], r['corner'], r['r']))
            if os.path.exists(f):
                a, z = np.load(f), np.load(os.path.join(HERE, r['wave']))
                same = float(np.abs(a['rx_pin'] - z['rx_pin']).max()) if len(a['t']) == len(z['t']) else None
                chk.append(dict(case='pin %s %s %s r%g vs si/spice' % (r['net'], r['scenario'], r['corner'], r['r']),
                                max_abs_diff_v=same))
    out['reproduction_checks'] = chk
    out['summary'] = summarise(rows, pref)
    json.dump(out, open(os.path.join(HERE, 'sim_placed.json'), 'w'), indent=1)
    write_md(out, rows, pref)
    print('cases %d errors %d not-t_end %d checks %d (max diff %s)' % (
        len(ALL), len(ERR), out['counts']['not_reaching_t_end'], len(chk),
        max([c['max_abs_diff_v'] for c in chk if c['max_abs_diff_v'] is not None], default=None)))


if __name__ == '__main__':
    main()
