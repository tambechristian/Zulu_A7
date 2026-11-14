"""Fill the 16-net table of sec7.md.in from ../../sim/sim_final.json and splice it over section 7 of
docs/dq_series_resistors.md.  -> sec7.md here (the spliced text)."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(HERE, '..', '..', 'sim', 'sim_final.json')))
idx = {(r['net'], r['stack'], r['corner']): r for r in S['per_net']}


def f(x):
    return 'off table' if x is None or x >= 1e10 else ('%.1f %%' % x)


def r0(x):
    return 'off table' if x is None or x >= 1e10 else (('%.0f %%' % x) if x >= 1000 else ('%.1f %%' % x))


rows = []
for n in range(16):
    net = 'D%d' % n
    a, b, c, d = (idx[(net, s, k)] for s, k in (('fab', 'max'), ('fab', 'typ'), ('pcbdoc', 'max'), ('pcbdoc', 'typ')))
    new = n in (13, 14, 15)
    row = [('*%s*' % net) if new else net, ('*%s*' % a['ref']) if new else a['ref'],
           r0(a['read']['R0_ball_budget_pct']),
           '%s (%.3f V) / %s' % (f(a['read']['ball_budget_pct']), a['read']['ball_vmin'], f(a['read']['die_budget_pct'])),
           '%s / %s' % (f(b['read']['ball_budget_pct']), f(b['read']['die_budget_pct'])),
           r0(c['read']['R0_ball_budget_pct']),
           '%s (%.3f V) / %s' % (f(c['read']['ball_budget_pct']), c['read']['ball_vmin'], f(c['read']['die_budget_pct'])),
           '%s / %s' % (f(d['read']['ball_budget_pct']), f(d['read']['die_budget_pct']))]
    rows.append('| ' + ' | '.join(row) + ' |')
s = open(os.path.join(HERE, 'sec7.md.in'), encoding='utf-8').read().replace('@@TABLE@@', '\n'.join(rows))
open(os.path.join(HERE, 'sec7.md'), 'w', encoding='utf-8', newline='\n').write(s)
D = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..', '..', 'docs', 'dq_series_resistors.md'))
t = open(D, encoding='utf-8', newline='').read()
i = t.index('## 7. Simulation of the placed resistors\n')
j = t.index('## 8. Implementation sequence')
t = t[:i] + s + t[j:]
open(D, 'w', encoding='utf-8', newline='').write(t)
print('\n'.join(rows))
print('spliced into', D)
