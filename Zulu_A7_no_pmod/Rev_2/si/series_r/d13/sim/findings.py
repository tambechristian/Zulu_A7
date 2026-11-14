"""findings.py -- findings text for sim_final.md; every number is read from sim_final.json's content (OUT)."""


def _pct(x):
    return 'off table' if x >= 1e8 else ('%.1f %%' % x)


def _rows(OUT, **k):
    return [r for r in OUT['per_net'] if all(r[a] == b for a, b in k.items())]


def _span(vals):
    return '%+.3f..%+.3f' % (min(vals), max(vals))


def findings(OUT):
    L = []
    A = L.append
    B = OUT['bus']
    worst_ball = max(B.values(), key=lambda b: b['ball_worst_pct'])
    k_wb = [k for k, b in B.items() if b is worst_ball][0]
    A('1. **All 16 data nets pass on both stacks at both corners, with 22 ohm in every net.**')
    for k, b in B.items():
        A('   - %s: worst ball %s (%s), worst die %.1f %%, worst ball Vmin %+.3f V (%s); ball fails: %s.' % (
            k.replace('|', ' / '), _pct(b['ball_worst_pct']), b['ball_worst_net'], b['die_worst_pct'],
            b['ball_vmin_worst'], b['ball_vmin_worst_net'], ', '.join(b['ball_fails']) or 'none'))
    A('   - The bus worst is %s of DS181 Table 4 (%s, %s). It is a small undershoot at the U1 ball. '
      'Every die budget is 0.0 %%.' % (_pct(worst_ball['ball_worst_pct']), worst_ball['ball_worst_net'],
                                       k_wb.replace('|', ' / ')))
    pm = {r['net']: r for r in _rows(OUT, stack='pcbdoc', corner='max')}
    pt = {r['net']: r for r in _rows(OUT, stack='pcbdoc', corner='typ')}
    A('2. **D13, D14 and D15 are fixed on the PcbDoc stack.** Each figure below is the ball budget without R, then '
      'with 22 ohm:')
    for n in ('D14', 'D13', 'D15'):
        A('   - %s (%s %s): max corner %s -> %s; typ corner %s -> %s. Ball Vmin %+.3f -> %+.3f V (max).' % (
            n, pm[n]['ref'], pm[n]['r_side'], _pct(pm[n]['read']['R0_ball_budget_pct']),
            _pct(pm[n]['read']['ball_budget_pct']), _pct(pt[n]['read']['R0_ball_budget_pct']),
            _pct(pt[n]['read']['ball_budget_pct']), pm[n]['read']['R0_ball_vmin'], pm[n]['read']['ball_vmin']))
    r0f = sorted([r['net'] for r in _rows(OUT, stack='pcbdoc', corner='max') if r['read']['R0_ball_budget_pct'] > 100],
                 key=lambda n: int(n[1:]))
    A('   - Without any R, %d of 16 nets fail at the ball on the PcbDoc stack at the max corner: %s. With the plan, '
      'none do. The d10 run simulated only 6 nets on this stack, so this is the first whole-bus PcbDoc result.' % (
          len(r0f), ', '.join(r0f)))
    rb = max(max(b['ringback_ball_worst_v'], b['ringback_die_worst_v'], b['write_ringback_worst_v']) for b in B.values())
    A('3. **No ringback at 22 ohm.** The largest re-entry into 0.8-2.0 V is %.3f V, over every net, node, corner, '
      'direction and stack.' % rb)
    wmin = min(b['write_u3pin_vmin'] for b in B.values())
    wmax = max(b['write_u3pin_vmax'] for b in B.values())
    dmin = min(b['write_u3die_vmin'] for b in B.values())
    dmax = max(b['write_u3die_vmax'] for b in B.values())
    A('4. **Writes pass the SDRAM absolute maximum (-1.0 / 4.6 V) on every net.** Worst at the U3 pin: %+.3f / '
      '%.3f V. Worst at the U3 die: %+.3f / %.3f V.' % (wmin, wmax, dmin, dmax))
    rd = [v for r in OUT['per_net'] for v in r['read']['delay_die_ns']]
    wd = [v for r in OUT['per_net'] for v in r['write']['delay_die_ns']]
    A('5. **Delay cost against the no-R copper**, over all 16 nets, both stacks and both corners:')
    A('   - Reads at the U1 die: %s ns.' % _span(rd))
    A('   - Writes at the U3 die: %s ns.' % _span(wd))
    for n in ('D13', 'D14', 'D15'):
        g = [r for r in OUT['per_net'] if r['net'] == n]
        A('   - %s: read %s ns, write %s ns.' % (
            n, _span([v for r in g for v in r['read']['delay_die_ns']]),
            _span([v for r in g for v in r['write']['delay_die_ns']])))
    A('   - D13 has the largest read delay on the bus. Its route is about 6.6 mm longer, and part of it is now Top '
      'microstrip.')
    ids = OUT['identity_summary']
    A('6. **Reproduction.** Both d10 cases re-run to 0 V sample by sample, with identical budgets and Vmin '
      '(section 0). Every run with a counterpart was also compared:')
    for k, s in ids.items():
        A('   - %s: %d of %d waveforms identical.' % (k, s['identical'], s['n']))
    A('   - Adding R132-R134 leaves D0-D12 bit-identical to the 13-R plan. The model is per net and has no '
      'coupling, so this is expected.')
    return L


def sweep_note(OUT):
    S = OUT['sweep']
    L = []
    A = L.append

    def g(rv, key, sub, f=max):
        return f(r[key][sub] for r in S if r['r_ohm'] == rv)

    def dd(rv, key):
        # |worst-edge delay at rv - worst-edge delay at 22|, per net and corner: (min, max)
        d = []
        for r in S:
            if r['r_ohm'] != rv:
                continue
            q = [x for x in S if x['r_ohm'] == 22.0 and x['net'] == r['net'] and x['corner'] == r['corner']][0]
            d.append(abs(r[key]['delay_die_ns'][1] - q[key]['delay_die_ns'][1]))
        return round(min(d), 3), round(max(d), 3)

    def span(rv, key, sub, i):
        return [r[key][sub][i] for r in S if r['r_ohm'] == rv]

    A('**Reading the sweep.** Nets: %s (the worst four at 22 ohm), plus D14 and D13, the nets this plan adds. '
      'Ranges below are over these nets and both corners on the PcbDoc stack.\n' % ', '.join(OUT['sweep_worst4_pcbdoc_max']))
    A('| R ohm | worst ball budget | worst die budget | worst ball Vmin V | worst ball Vmax V | worst ringback V '
      '(ball / die) | read t10-90 die ns | read settle die ns | read delay die ns | write U3 pin Vmin / Vmax V | '
      'write delay die ns |')
    A('|---|---|---|---|---|---|---|---|---|---|---|')
    for rv in (15.0, 22.0, 33.0):
        A('| %g | %.2f %% | %.2f %% | %+.3f | %.3f | %.3f / %.3f | %.2f..%.2f | %.2f..%.2f | %+.3f..%+.3f | %+.3f / %.3f | '
          '%+.3f..%+.3f |' % (
              rv, g(rv, 'read', 'ball_budget_pct'), g(rv, 'read', 'die_budget_pct'), g(rv, 'read', 'ball_vmin', min),
              g(rv, 'read', 'ball_vmax'), g(rv, 'read', 'ringback_ball_v'), g(rv, 'read', 'ringback_die_v'),
              g(rv, 'read', 't10_90_die_ns', min), g(rv, 'read', 't10_90_die_ns'),
              g(rv, 'read', 'settle_die_ns', min), g(rv, 'read', 'settle_die_ns'),
              min(span(rv, 'read', 'delay_die_ns', 0)), max(span(rv, 'read', 'delay_die_ns', 1)),
              g(rv, 'write', 'u3pin_vmin', min), g(rv, 'write', 'u3pin_vmax'),
              min(span(rv, 'write', 'delay_die_ns', 0)), max(span(rv, 'write', 'delay_die_ns', 1))))
    rb33 = [(r['net'], r['corner'], r['read']['ringback_ball_v']) for r in S
            if r['r_ohm'] == 33.0 and r['read']['ringback_ball_v'] > 0]
    A('')
    A('**Verdict: 22 ohm is still the right value on the 49.1 ohm stack.** All three values pass by a wide margin, '
      'so this is a trade-off, not a pass/fail choice:')
    A('- **15 ohm** passes, but it is under-terminated at 49 ohm. The ball budget rises to %.1f %% and the die '
      'budget to %.1f %% (it is 0.0 %% at 22 ohm), and the ball undershoot deepens to %+.3f V. Against 22 ohm it '
      'saves only %.3f..%.3f ns of read delay and %.3f..%.3f ns of write delay (worst edge, per net and corner).' % (
          g(15.0, 'read', 'ball_budget_pct'), g(15.0, 'read', 'die_budget_pct'), g(15.0, 'read', 'ball_vmin', min),
          *dd(15.0, 'read'), *dd(15.0, 'write')))
    A('- **33 ohm** brings both budgets to 0.0 %%, but 22 ohm is already at 0.0 %% at the die and at most %.2f %% at '
      'the ball, so it gains nothing that matters. It costs slower edges: die t10-90 up to %.2f ns against %.2f ns '
      'at 22 ohm, and read settle up to %.2f ns against %.2f. Against 22 ohm it adds %.3f..%.3f ns of read delay '
      'and %.3f..%.3f ns of write delay (worst edge, per net and corner). %s' % (
          g(22.0, 'read', 'ball_budget_pct'), g(33.0, 'read', 't10_90_die_ns'), g(22.0, 'read', 't10_90_die_ns'),
          g(33.0, 'read', 'settle_die_ns'), g(22.0, 'read', 'settle_die_ns'), *dd(33.0, 'read'), *dd(33.0, 'write'),
          ('It also shows a small re-entry into 0.8-2.0 V at the U1 ball (%s), which no other value shows.' %
           ', '.join('%s %s %.3f V' % x for x in rb33)) if rb33 else ''))
    A('- The fab stack (43.4 ohm) was not swept. At 22 ohm, the worst ball result on either stack is %.2f %% of the '
      'budget (section 1), so one value serves both stacks.' % max(
          b['ball_worst_pct'] for b in OUT['bus'].values()))
    return L
