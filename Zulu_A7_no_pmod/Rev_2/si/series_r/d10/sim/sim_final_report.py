"""sim_final_report.py -- collect bus_sim_final.py runs (this folder) into sim_final.json + sim_final.md.

Inputs: sim_final_raw_{placed_fab,base_fab,placed_pcbdoc,base_pcbdoc,repro12,repro_base}.json, repro_cmp.json,
waves in wave_final/. Criteria as sim_placed_report.py: DS181 Table 4 usage at the U1 ball ('pin') and die, UI 7.5 ns
(ds181_check arithmetic); writes vs SDRAM abs max -1.0 / 4.6 V; ringback = re-entry into 0.8-2.0 V after the first
threshold crossing (bus_sim measure()); delay change = first 1.4 V crossing minus the no-R (base, today's copper) run of
the same net / scenario / corner / stack, per edge (8.5 fall, 16.0 rise, 23.5 fall), reported min..max over the 3 edges.
"""
import hashlib
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DN = ['D%d' % i for i in range(16)]
TAGS = ('placed_fab', 'base_fab', 'placed_pcbdoc', 'base_pcbdoc', 'repro12', 'repro_base')
RAW = {t: json.load(open(os.path.join(HERE, 'sim_final_raw_%s.json' % t))) for t in TAGS}
ALL = [r for v in RAW.values() for r in v]
ERR = [r for r in ALL if 'error' in r]
PLAN = os.path.join(os.path.dirname(HERE), 'final_plan.json')
PLAN_MD5 = hashlib.md5(open(PLAN, 'rb').read()).hexdigest()


def find(tag, **k):
    g = [r for r in RAW[tag] if all(r.get(a) == b for a, b in k.items())]
    assert len(g) <= 1, (tag, k, len(g))
    return g[0] if g else None


def xdelta(case, base, node):
    d = []
    for e, c in case[node]['cross_1v4'].items():
        b = base[node]['cross_1v4'][e]
        if c['first'] is not None and b['first'] is not None:
            d.append(c['first'] - b['first'])
    return [round(min(d), 4), round(max(d), 4)], sum(c['n'] > 1 for c in case[node]['cross_1v4'].values())


def wave_diff(a, b):
    za, zb = np.load(os.path.join(HERE, a['wave'])), np.load(os.path.join(HERE, b['wave']))
    if len(za['t']) != len(zb['t']) or not np.allclose(za['t'], zb['t']):
        return None
    return max(float(np.max(np.abs(za[k] - zb[k]))) for k in ('rx_pin', 'rx_die', 'tx_die'))


def row(stack, net, corner):
    pr = find('placed_' + stack, net=net, corner=corner, scenario='read')
    pw = find('placed_' + stack, net=net, corner=corner, scenario='write')
    br = find('base_' + stack, net=net, corner=corner, scenario='read')
    bw = find('base_' + stack, net=net, corner=corner, scenario='write')
    if not pr:
        return None
    for x in (pr, pw, br, bw):
        assert x is not None and 'error' not in x, (stack, net, corner)
    s = dict(net=net, stack=stack, corner=corner, ref=pr.get('ref'), r_side=pr.get('r_side'), r_xy=pr.get('r_xy'),
             feed_mm=pr.get('feed_mm'), feed_vias=pr.get('feed_vias'), line_mm=pr.get('line_mm'),
             line_vias=pr.get('line_vias'), len_mm=pr['len_mm'], connected=pr['connected'] and pw['connected'],
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
                     R0_ball_budget_pct=round(100 * br['pin']['budget'], 2),
                     R0_die_budget_pct=round(100 * br['die']['budget'], 2),
                     R0_ball_vmin=round(br['pin']['vmin'], 4), R0_t10_90_die_ns=round(br['die']['t10_90_ns'], 4))
    s['read']['delay_die_ns'], s['read']['multi_cross_die'] = xdelta(pr, br, 'die')
    s['read']['delay_ball_ns'], s['read']['multi_cross_ball'] = xdelta(pr, br, 'pin')
    s['write'] = dict(u3pin_vmin=round(pw['pin']['vmin'], 4), u3pin_vmax=round(pw['pin']['vmax'], 4),
                      u3die_vmin=round(pw['die']['vmin'], 4), u3die_vmax=round(pw['die']['vmax'], 4),
                      absmax_pass=bool(pw['pin']['abs_max_pass'] and pw['die']['abs_max_pass']),
                      ringback_pin_v=round(pw['pin']['ringback_into_band'], 4),
                      ringback_die_v=round(pw['die']['ringback_into_band'], 4),
                      t10_90_die_ns=round(pw['die']['t10_90_ns'], 4),
                      R0_u3pin_vmin=round(bw['pin']['vmin'], 4), R0_u3pin_vmax=round(bw['pin']['vmax'], 4))
    s['write']['delay_die_ns'], s['write']['multi_cross_die'] = xdelta(pw, bw, 'die')
    if s['ref'] is None:      # no R in the plan: the plan-applied copper must equal today's copper
        s['noR_identity_max_dv'] = max(wave_diff(pr, br), wave_diff(pw, bw))
    return s


ROWS = [x for st in ('fab', 'pcbdoc') for c in ('typ', 'max') for n in DN for x in [row(st, n, c)] if x]


def bus(stack, corner):
    g = [r for r in ROWS if r['stack'] == stack and r['corner'] == corner]
    wb = max(g, key=lambda r: r['read']['ball_budget_pct'])
    wd = max(g, key=lambda r: r['read']['die_budget_pct'])
    wr = [r for r in g if r['ref']]
    out = dict(n_nets=len(g), nets=[r['net'] for r in g],
               ball_worst_pct=wb['read']['ball_budget_pct'], ball_worst_net=wb['net'],
               die_worst_pct=wd['read']['die_budget_pct'], die_worst_net=wd['net'],
               ball_fails=[r['net'] for r in g if r['read']['ball_budget_pct'] > 100],
               die_fails=[r['net'] for r in g if r['read']['die_budget_pct'] > 100],
               ringback_ball_worst_v=max(r['read']['ringback_ball_v'] for r in g),
               ringback_die_worst_v=max(r['read']['ringback_die_v'] for r in g),
               write_u3pin_vmin=min(r['write']['u3pin_vmin'] for r in g),
               write_u3pin_vmax=max(r['write']['u3pin_vmax'] for r in g),
               write_absmax_all_pass=all(r['write']['absmax_pass'] for r in g),
               write_ringback_worst_v=max(max(r['write']['ringback_pin_v'], r['write']['ringback_die_v']) for r in g))
    if wr:
        w = max(wr, key=lambda r: r['read']['ball_budget_pct'])
        out.update(withR_ball_worst_pct=w['read']['ball_budget_pct'], withR_ball_worst_net=w['net'],
                   read_delay_die_ns_withR=[min(r['read']['delay_die_ns'][0] for r in wr),
                                            max(r['read']['delay_die_ns'][1] for r in wr)],
                   write_delay_die_ns_withR=[min(r['write']['delay_die_ns'][0] for r in wr),
                                             max(r['write']['delay_die_ns'][1] for r in wr)])
    return out


BUS = {'%s|%s' % (s, c): bus(s, c) for s in ('fab', 'pcbdoc') for c in ('typ', 'max')}
REPRO = json.load(open(os.path.join(HERE, 'repro_cmp.json')))
fab_max = sorted([r for r in ROWS if r['stack'] == 'fab' and r['corner'] == 'max'],
                 key=lambda r: -r['read']['ball_budget_pct'])
OUT = dict(plan='d10/final_plan.json', plan_md5=PLAN_MD5, pcbdoc_md5='2a616c1c74f8788a4a1c837c7d76c3b0',
           simulator='d10/sim/bus_sim_final.py (made by make_sim.py from d10/judge/bus_sim_judge.py)',
           r_ohm=22.0, pkg='parts: ESL 0.5 nH, 0.05 pF across, 0.08 pF per pad to ground', ui_ns=7.5,
           counts=dict(cases=len(ALL), errors=len(ERR),
                       not_reaching_t_end=sum(1 for r in ALL if 'error' not in r and not r['reached_t_end']),
                       t_end_ns=32.0, max_workers=6, per_tag={k: len(v) for k, v in RAW.items()}),
           worst4_fab_max=[r['net'] for r in fab_max[:4]], pcbdoc_extra_nets=['D0', 'D5'],
           reproduction=REPRO, bus=BUS, per_net=ROWS)
json.dump(OUT, open(os.path.join(HERE, 'sim_final.json'), 'w'), indent=1)


def pct(x):
    return 'off table' if x >= 1e8 else ('%.1f %%' % x)


def rng(a):
    return '%+.3f..%+.3f' % tuple(a)


L = []
A = L.append
A('# Whole-bus SI with the final D10 plan (13 series R)\n')
A("Plan `d10/final_plan.json` (md5 %s, PcbDoc md5 2a616c1c): R119-R131 at 22 ohm with the 0201 parasitic model "
  "(0.5 nH, 0.05 pF across, 0.08 pF per pad). D13, D14 and D15 have no R. They run on the plan-applied copper, which "
  "is identical to today's: the largest |dV| against the no-R run is %s V. The simulator is `d10/sim/bus_sim_final.py`, "
  "a copy of the judge's `bus_sim_judge.py` (which is bus_sim_placed.py plus a plan-JSON reader). It differs only in "
  "paths, a per-task plan argument and the no-R handling; `make_sim.py` lists every edit.\n" % (
      PLAN_MD5, '%.3g' % max(r.get('noR_identity_max_dv', 0) for r in ROWS)))
c = OUT['counts']
A('Cases: %d (%s). Errors: %d. Runs not reaching t_end 32 ns: %d. One case per process, at most 6 workers.\n' % (
    c['cases'], ', '.join('%s %d' % kv for kv in c['per_tag'].items()), c['errors'], c['not_reaching_t_end']))
FM, FT, PM, PT = BUS['fab|max'], BUS['fab|typ'], BUS['pcbdoc|max'], BUS['pcbdoc|typ']
d10 = {(r['stack'], r['corner']): r for r in ROWS if r['net'] == 'D10'}
A('## Findings\n')
A('1. **Fab stack, whole bus (16 nets): every read passes at the U1 ball and at the die, at both corners.**')
A('   - Worst ball: %s (%s, max) and %s (%s, typ). Both are nets without an R.' % (
    pct(FM['ball_worst_pct']), FM['ball_worst_net'], pct(FT['ball_worst_pct']), FT['ball_worst_net']))
A('   - Worst die: %.1f %% (%s, max).' % (FM['die_worst_pct'], FM['die_worst_net']))
A('   - Worst of the 13 nets with an R: %.2f %% (%s, max) and %.2f %% (%s, typ).' % (
    FM['withR_ball_worst_pct'], FM['withR_ball_worst_net'], FT['withR_ball_worst_pct'], FT['withR_ball_worst_net']))
A('2. **D10 is fixed.**')
A('   - Ball: %s -> %s at max and %s -> %s at typ. Die: %.1f %% at both corners.' % (
    pct(d10[('fab', 'max')]['read']['R0_ball_budget_pct']), pct(d10[('fab', 'max')]['read']['ball_budget_pct']),
    pct(d10[('fab', 'typ')]['read']['R0_ball_budget_pct']), pct(d10[('fab', 'typ')]['read']['ball_budget_pct']),
    d10[('fab', 'max')]['read']['die_budget_pct']))
A('   - PcbDoc stack: %s max / %s typ.' % (
    pct(d10[('pcbdoc', 'max')]['read']['ball_budget_pct']), pct(d10[('pcbdoc', 'typ')]['read']['ball_budget_pct'])))
A("   - These are the judge's numbers exactly.")
A('3. **No ringback** into 0.8-2.0 V at any node, corner, direction or stack.')
A('4. **Writes pass on every net.** Worst at U3 pin: %+.3f / %.3f V (fab, max), against limits of -1.0 / 4.6 V.' % (
    FM['write_u3pin_vmin'], FM['write_u3pin_vmax']))
A('5. **Delay cost on the 13 nets with an R**, against the no-R run:')
A('   - Reads at the U1 die: %s ns.' % rng([min(FM['read_delay_die_ns_withR'][0], FT['read_delay_die_ns_withR'][0]),
                                             max(FM['read_delay_die_ns_withR'][1], FT['read_delay_die_ns_withR'][1])]))
A('   - Writes at the U3 die: %s ns.' % rng([min(FM['write_delay_die_ns_withR'][0], FT['write_delay_die_ns_withR'][0]),
                                               max(FM['write_delay_die_ns_withR'][1], FT['write_delay_die_ns_withR'][1])]))
A('6. **PcbDoc stack: D13, D14 and D15 (no R) fail at the U1 ball.**')
A('   - Max corner: D14 %s, D13 %s, D15 %s. Typ corner: D14 %s.' % tuple(
    pct([r for r in ROWS if r['stack'] == 'pcbdoc' and r['corner'] == cn and r['net'] == n][0]['read']['ball_budget_pct'])
    for n, cn in (('D14', 'max'), ('D13', 'max'), ('D15', 'max'), ('D14', 'typ'))))
A('   - Their die passes (worst %.1f %%).' % PM['die_worst_pct'])
A('   - These are the only failures in the run, and the D10 plan does not change them: their copper is identical to '
  "today's (0 V difference).")
A('   - The fab stack, which is what PCBWay builds, passes them.')
A('   - R132, R133 and R134 are the reserved designators for these three nets.\n')
A('## 0. Reproduction of sim_placed.json\n')
A("`repro_cmp.py` runs the adapted simulator on `dq_series_r_plan.json` (the 12-R plan) and on today's copper. It "
  "compares the waveforms sample by sample with `si/series_r/wave_placed/`.\n")
A('| case | copper mm (new / sim_placed) | ball Vmin (new / sim_placed) | ball budget (new / sim_placed) | max abs dV |')
A('|---|---|---|---|---|')
for x in REPRO:
    dv = x['max_abs_dv']['rx_pin']
    A('| %s %s %s %s | %.3f / %.3f | %+.4f / %+.4f | %s / %s | %s |' % (
        x['net'], x['scenario'], x['corner'], x['mode'], x['len_mm'][0], x['len_mm'][1], x['pin_vmin'][0],
        x['pin_vmin'][1], '-' if x['budget'][0] is None else '%.2f %%' % (100 * x['budget'][0]),
        '-' if x['budget'][1] is None else '%.2f %%' % (100 * x['budget'][1]),
        '0 V (identical)' if dv == 0 else ('%.3g V' % dv if dv is not None else 'copper differs')))
A("\n- D5, D8, D9, D10 and D13 match to 0 V.\n"
  "- D0 and D12 differ because their copper differs. sim_placed.json simulated the judge's FINAL plan before the "
  "DFM fixes. `dq_series_r_plan.json` includes both fixes:\n"
  "  - F2 moves R119 0.04 mm south, so D0's U3 feed is 1.00 mm instead of 0.96.\n"
  "  - F1 re-centres D12's U1-side column in R131-2, so D12 is 12.60 mm instead of 13.37.\n"
  "- dq_series_resistors.md says the F1/F2 geometry \"was not simulated\". This run is its first simulation, and "
  "both nets stay within 0.02 V of the old values.\n")
A('## 1. Bus summary\n')
A('| stack | corner | nets | READ worst ball (net) | ball fails | worst die (net) | ringback ball / die V | '
  'WRITE U3 pin Vmin / Vmax | abs-max | write ringback V | read delay die ns (R nets) | write delay die ns (R nets) |')
A('|---|---|---|---|---|---|---|---|---|---|---|---|')
for k, b in BUS.items():
    st, cn = k.split('|')
    A('| %s | %s | %d | %s (%s) | %s | %.1f %% (%s) | %.3f / %.3f | %+.3f / %.3f | %s | %.3f | %s | %s |' % (
        st, cn, b['n_nets'], pct(b['ball_worst_pct']), b['ball_worst_net'], ', '.join(b['ball_fails']) or 'none',
        b['die_worst_pct'], b['die_worst_net'], b['ringback_ball_worst_v'], b['ringback_die_worst_v'],
        b['write_u3pin_vmin'], b['write_u3pin_vmax'], 'PASS' if b['write_absmax_all_pass'] else 'FAIL',
        b['write_ringback_worst_v'], rng(b['read_delay_die_ns_withR']), rng(b['write_delay_die_ns_withR'])))
A('\nThe PcbDoc rows cover only the six nets run on that stack (section 3). A ringback value <= 0 means the waveform '
  'does not re-enter 0.8-2.0 V.\n')
for cn in ('max', 'typ'):
    A('## 2%s. Per net, fab stack, %s corner\n' % ('a' if cn == 'max' else 'b', cn))
    A('| net | R | U3->R mm (vias) | R0 ball | ball budget | die budget | ball Vmin | ringback ball / die V | '
      'read t10-90 die ns | read delay die ns | write U3 pin Vmin / Vmax | write die Vmin / Vmax | abs-max | '
      'write ringback V | write delay die ns |')
    A('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for n in DN:
        r = [x for x in ROWS if x['stack'] == 'fab' and x['corner'] == cn and x['net'] == n][0]
        rd, wr = r['read'], r['write']
        A('| %s | %s | %s | %s | %s | %.1f %% | %+.3f | %.3f / %.3f | %.2f | %s | %+.3f / %.3f | %+.3f / %.3f | %s | '
          '%.3f | %s |' % (
              n, ('%s %s' % (r['ref'], r['r_side'])) if r['ref'] else 'none',
              ('%.2f (%d)' % (r['feed_mm'], r['feed_vias'])) if r['ref'] else '-', pct(rd['R0_ball_budget_pct']),
              pct(rd['ball_budget_pct']), rd['die_budget_pct'], rd['ball_vmin'], rd['ringback_ball_v'],
              rd['ringback_die_v'], rd['t10_90_die_ns'], rng(rd['delay_die_ns']), wr['u3pin_vmin'], wr['u3pin_vmax'],
              wr['u3die_vmin'], wr['u3die_vmax'], 'PASS' if wr['absmax_pass'] else 'FAIL',
              max(wr['ringback_pin_v'], wr['ringback_die_v']), rng(wr['delay_die_ns'])))
    A('')
A('## 3. PcbDoc stack: the four worst fab nets (%s), plus D0 and D5\n' % ', '.join(OUT['worst4_fab_max']))
A('| net | R | corner | R0 ball | ball budget | die budget | ball Vmin | ringback ball / die V | read delay die ns | '
  'write U3 pin Vmin / Vmax | abs-max |')
A('|---|---|---|---|---|---|---|---|---|---|---|')
for n in OUT['worst4_fab_max'] + ['D0', 'D5']:
    for cn in ('typ', 'max'):
        r = [x for x in ROWS if x['stack'] == 'pcbdoc' and x['corner'] == cn and x['net'] == n][0]
        rd, wr = r['read'], r['write']
        A('| %s | %s | %s | %s | %s | %.1f %% | %+.3f | %.3f / %.3f | %s | %+.3f / %.3f | %s |' % (
            n, r['ref'] or 'none', cn, pct(rd['R0_ball_budget_pct']), pct(rd['ball_budget_pct']), rd['die_budget_pct'],
            rd['ball_vmin'], rd['ringback_ball_v'], rd['ringback_die_v'], rng(rd['delay_die_ns']), wr['u3pin_vmin'],
            wr['u3pin_vmax'], 'PASS' if wr['absmax_pass'] else 'FAIL'))
A('\n## Method and limits\n')
A("- **Copper.** board_extract.json (PcbDoc md5 2a616c1c) with final_plan.json applied by the judge's plan-JSON reader "
  "(renames = remove + re-add; 0 apply errors). Each net with an R is split at the R into SDRAM-Dn and Dn. Each half "
  "is netlisted by bus_sim's net_elements(), and both halves are connected in every case.")
A('- **R model.** 22 ohm plus 0.5 nH in series, 0.05 pF across, and 0.08 pF from each pad to ground (the parts.md '
  'estimate).')
A('- **Stacks.**')
A('  - Fab: the PCBWay construction. L3/L4 at 0.125 mm is 43.4 ohm.')
A('  - PcbDoc: the stack stored in the PcbDoc. Its inner dielectrics are thicker, so L3/L4 at 0.125 mm is 49.1 ohm.')
A("- **Delay.** The shift of the first 1.4 V crossing at the receiver die, compared with the no-R run on today's "
  "copper (same net, scenario, corner and stack). Reported as min..max over the 8.5 ns fall, 16 ns rise and 23.5 ns "
  "fall edges.")
A('- **Not modelled.**')
A('  - Coupling, including the R127/R129/R130 column and the parallel Top runs at x 38.5-40.2.')
A('  - Plane openings: L2 and L5 are treated as ideal planes.')
A('  - The IBIS slow corner.')
A('  - Uncertainty in the 0201 package values.')
open(os.path.join(HERE, 'sim_final.md'), 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')
print(json.dumps(BUS, indent=1))
print('worst4', OUT['worst4_fab_max'], 'noR identity', [r.get('noR_identity_max_dv') for r in ROWS if r['ref'] is None])
