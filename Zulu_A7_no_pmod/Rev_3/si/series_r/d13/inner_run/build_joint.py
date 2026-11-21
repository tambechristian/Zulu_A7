import json, sys
import plan_tools as PT
sel = {}
for a in sys.argv[1].split(','):
    n, i = a.split('#'); sel[n] = int(i)
out = sys.argv[2]
base = json.load(open('base_plan_13.json'))
deltas = []
note = []
for n, i in sel.items():
    c = json.load(open('ranked_%s.json' % n))[i]
    assert c['i'] == i
    deltas.append(PT.delta(c))
    note.append('%s %s on %s (%.3f,%.3f) rot %d, inner-run columns' % (PT.REF[n], n, c['side'], c['cx'], c['cy'], c['rot']))
P = PT.merge(base, deltas, '; '.join(note) + ' (strategy inner_run)')
json.dump(P, open(out, 'w'), indent=1)
print(out, {k: len(v) for k, v in P.items() if isinstance(v, list)})
