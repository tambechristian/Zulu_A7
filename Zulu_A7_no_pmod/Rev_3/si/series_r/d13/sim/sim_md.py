"""sim_md.py -- writes sim_final.md from sim_report.py's results (imports it, which also rewrites sim_final.json).
Findings text with the numbers filled in from the data lives in findings.py (findings(OUT), sweep_note(OUT))."""
import importlib.util
import os

import sim_report as S

HERE = S.HERE
OUT, ROWS, BUS, REPRO, IDSUM, SWEEP, WORST4, DN = S.OUT, S.ROWS, S.BUS, S.REPRO, S.IDSUM, S.SWEEP, S.WORST4, S.DN


def pct(x):
    return 'off table' if x >= 1e8 else ('%.1f %%' % x)


def rng(a):
    return '%+.3f..%+.3f' % tuple(a)


def rtxt(r):
    return ('%s %s' % (r['ref'], r['r_side'])) if r['ref'] else 'none'


def per_net_table(A, stack, cn):
    A('| net | R | U3->R mm (vias) | len mm | R0 ball | ball budget | die budget | ball Vmin / Vmax | '
      'ringback ball / die V | read t10-90 die ns | read settle die ns (R0) | read delay die ns | '
      'write U3 pin Vmin / Vmax | write die Vmin / Vmax | abs-max | write ringback V | write delay die ns |')
    A('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for n in DN:
        r = [x for x in ROWS if x['stack'] == stack and x['corner'] == cn and x['net'] == n][0]
        rd, wr = r['read'], r['write']
        A('| %s | %s | %s | %.2f | %s | %s | %.1f %% | %+.3f / %.3f | %.3f / %.3f | %.2f | %.2f (%.2f) | %s | '
          '%+.3f / %.3f | %+.3f / %.3f | %s | %.3f | %s |' % (
              n, rtxt(r), ('%.2f (%d)' % (r['feed_mm'], r['feed_vias'])) if r['ref'] else '-', r['len_mm'],
              pct(rd['R0_ball_budget_pct']), pct(rd['ball_budget_pct']), rd['die_budget_pct'], rd['ball_vmin'],
              rd['ball_vmax'], rd['ringback_ball_v'], rd['ringback_die_v'], rd['t10_90_die_ns'],
              rd['settle_die_ns'], rd['R0_settle_die_ns'], rng(rd['delay_die_ns']), wr['u3pin_vmin'],
              wr['u3pin_vmax'], wr['u3die_vmin'], wr['u3die_vmax'], 'PASS' if wr['absmax_pass'] else 'FAIL',
              max(wr['ringback_pin_v'], wr['ringback_die_v']), rng(wr['delay_die_ns'])))
    A('')


def write_md(findings, sweep_note):
    L = []
    A = L.append
    A('# Whole-bus SI with the D13 plan (16 series R, R119-R134)\n')
    A("Plan `d13/final_plan.json` (md5 %s; PcbDoc md5 2a616c1c, board_extract.json md5 81469ef0). R119-R134 at 22 ohm "
      "with the 0201 model of d10/sim (0.5 nH series, 0.05 pF across, 0.08 pF per pad to ground). Simulator "
      "`d13/sim/bus_sim_final.py`, a byte copy of `d10/sim/bus_sim_final.py` (md5 %s), placed mode, plan per task; "
      "the no-R references are its `base` mode (today's copper). `sim_report.py` builds sim_final.json from the raw "
      "JSON and the waveforms; `sim_md.py` writes this file.\n" % (OUT['plan_md5'], OUT['simulator_md5']))
    c = OUT['counts']
    A('Cases: %d (%s). Errors: %d. Runs not reaching t_end 32 ns: %d. Not connected: %d. One case per process, at '
      'most 6 workers.\n' % (c['cases'], ', '.join('%s %d' % kv for kv in c['per_tag'].items()), c['errors'],
                             c['not_reaching_t_end'], c['not_connected']))
    A('## Findings\n')
    L.extend(findings)
    A('\n## 0. Reproduction and identity checks\n')
    A('Two cases of `d10/sim/sim_final.json`, re-run with this copy and compared sample by sample with the d10 '
      'waveforms:\n')
    A('| case | plan | ball budget new / d10 | die budget new / d10 | ball Vmin new / d10 | same timebase | '
      'max abs dV | agree |')
    A('|---|---|---|---|---|---|---|---|')
    for x in REPRO:
        A('| %s | %s | %.2f %% / %.2f %% | %.2f %% / %.2f %% | %+.4f / %+.4f | %s | %s | %s |' % (
            x['case'], x['plan'] or "today's copper (no R)", x['new']['ball'], x['d10']['ball'], x['new']['die'],
            x['d10']['die'], x['new']['vmin'], x['d10']['vmin'], x['same_timebase'],
            '%.3g V' % x['max_abs_dv'] if x['max_abs_dv'] is not None else '-', 'YES' if x['agree'] else 'NO'))
    A('\nEvery 22-ohm and no-R run of this task that has a counterpart was also compared waveform by waveform '
      '(rx_pin, rx_die, tx_die):\n')
    A('| counterpart | cases compared | identical (0 V) | max abs dV | timebase differs |')
    A('|---|---|---|---|---|')
    for k, s in IDSUM.items():
        A('| %s | %d | %d | %.3g V | %d |' % (k, s['n'], s['identical'], s['max_dv'], s['timebase_differs']))
    A('')
    A('## 1. Bus summary (22 ohm, all 16 nets)\n')
    A('| stack | corner | nets (with R) | READ worst ball (net) | ball fails | worst die (net) | worst ball Vmin (net) | '
      'ringback ball / die V | WRITE U3 pin Vmin / Vmax | U3 die Vmin / Vmax | abs-max | write ringback V | '
      'read delay die ns | write delay die ns |')
    A('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for k, b in BUS.items():
        st, cn = k.split('|')
        A('| %s | %s | %d (%d) | %s (%s) | %s | %.1f %% (%s) | %+.3f (%s) | %.3f / %.3f | %+.3f / %.3f | '
          '%+.3f / %.3f | %s | %.3f | %s | %s |' % (
              st, cn, b['n_nets'], b['n_with_R'], pct(b['ball_worst_pct']), b['ball_worst_net'],
              ', '.join(b['ball_fails']) or 'none', b['die_worst_pct'], b['die_worst_net'], b['ball_vmin_worst'],
              b['ball_vmin_worst_net'], b['ringback_ball_worst_v'], b['ringback_die_worst_v'], b['write_u3pin_vmin'],
              b['write_u3pin_vmax'], b['write_u3die_vmin'], b['write_u3die_vmax'],
              'PASS' if b['write_absmax_all_pass'] else 'FAIL', b['write_ringback_worst_v'],
              rng(b['read_delay_die_ns']), rng(b['write_delay_die_ns'])))
    A('\nRingback 0 means the waveform never re-enters 0.8-2.0 V after its first threshold crossing. Delay = change '
      "of the first 1.4 V crossing at the receiver die against the no-R run on today's copper, min..max over the "
      '8.5 ns fall, 16 ns rise and 23.5 ns fall edges. Settle = last VIH (rise) / VIL (fall) crossing at the '
      'receiver die after the stimulus edge, worst of those three edges.\n')
    sec = 2
    for st in ('fab', 'pcbdoc'):
        for i, cn in enumerate(('max', 'typ')):
            A('## %d%s. Per net, %s stack (%s), %s corner\n' % (
                sec, 'ab'[i], st, '43.4 ohm L3/L4' if st == 'fab' else '49.1 ohm L3/L4', cn))
            per_net_table(A, st, cn)
        sec += 1
    A('## 4. Series-R value on the PcbDoc stack (49.1 ohm): 15 / 22 / 33 ohm on the worst four nets\n')
    A('Worst four at 22 ohm, PcbDoc max corner, ranked by ball budget, then die budget, then ball Vmin: %s. '
      'Same plan copper; only the R value changes (same 0201 package model).\n' % ', '.join(WORST4))
    A('| net | corner | R ohm | ball budget | die budget | ball Vmin / Vmax | die Vmin / Vmax | ringback ball / die V | '
      'read t10-90 die ns | read settle die ns | read delay die ns | write U3 pin Vmin / Vmax | abs-max | '
      'write settle die ns | write delay die ns |')
    A('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for r in SWEEP:
        rd, wr = r['read'], r['write']
        A('| %s | %s | %g | %s | %.1f %% | %+.3f / %.3f | %+.3f / %.3f | %.3f / %.3f | %.2f | %.2f | %s | '
          '%+.3f / %.3f | %s | %.2f | %s |' % (
              r['net'], r['corner'], r['r_ohm'], pct(rd['ball_budget_pct']), rd['die_budget_pct'], rd['ball_vmin'],
              rd['ball_vmax'], rd['die_vmin'], rd['die_vmax'], rd['ringback_ball_v'], rd['ringback_die_v'],
              rd['t10_90_die_ns'], rd['settle_die_ns'], rng(rd['delay_die_ns']), wr['u3pin_vmin'], wr['u3pin_vmax'],
              'PASS' if wr['absmax_pass'] else 'FAIL', wr['settle_die_ns'], rng(wr['delay_die_ns'])))
    A('')
    L.extend(sweep_note)
    A('\n## Method and limits\n')
    A("- **Copper.** board_extract.json with d13/final_plan.json applied by the simulator's plan-JSON reader "
      "(renames = remove + re-add). Each net is split at its R into SDRAM-Dn (U3 pin .. R pad 1) and Dn (R pad 2 .. "
      "U1 ball); each half is netlisted by bus_sim's net_elements(), and both halves are connected in every case.")
    A('- **R model.** R plus 0.5 nH in series, 0.05 pF across, 0.08 pF from each pad to ground (parts.md estimate, '
      'the same as d10/sim).')
    A('- **Stacks.** Fab = the PCBWay construction (L3/L4 at 0.125 mm = 43.4 ohm). PcbDoc = the stack stored in the '
      'PcbDoc (thicker inner dielectrics, 49.1 ohm).')
    A('- **Corners.** IBIS typ and max at 3.3 / 3.465 V; the IBIS slow corner was not run.')
    A('- **Not modelled.** Coupling (including the SDRAM-D13 Top run under U2 and the x 38.5-40.2 Top bundle); plane '
      'openings, including the new L2/L5 voids (planes are ideal); 0201 package uncertainty.')
    open(os.path.join(HERE, 'sim_final.md'), 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    fp = os.path.join(HERE, 'findings.py')
    F, N = [], []
    if os.path.exists(fp):
        spec = importlib.util.spec_from_file_location('findings', fp)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        F, N = mod.findings(OUT), mod.sweep_note(OUT)
    write_md(F, N)
    print('md written')
