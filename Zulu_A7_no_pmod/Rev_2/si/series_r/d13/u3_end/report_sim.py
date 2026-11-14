import json
P = {r['net'] + r['scenario'] + r['corner'] + r['stack']: r for r in json.load(open('sim_final_raw_placed_joint.json'))}
B = {r['net'] + r['scenario'] + r['corner'] + r['stack']: r for r in json.load(open('sim_final_raw_base_d13_15.json'))}
A = {r['net'] + r['scenario'] + r['corner'] + r['stack']: r for r in json.load(open('sim_final_raw_placed_alt_d13.json'))}
rows = []
def dly(p, b):
    out = []
    for e in ('fall@8.5', 'rise@16.0', 'fall@23.5'):
        out.append(p['die']['cross_1v4'][e]['first'] - b['die']['cross_1v4'][e]['first'])
    return min(out), max(out)
print('| net | R | stack | corner | read ball budget no-R -> plan | ball Vmin | die budget | ringback ball/die | read delay die ns | write U3 pin Vmin/Vmax | write delay die ns |')
print('|---|---|---|---|---|---|---|---|---|---|---|')
for src, tag in ((P, 'joint plan'), (A, 'alt plan (R132 alone)')):
    for n in ('D13', 'D14', 'D15'):
        for st in ('fab', 'pcbdoc'):
            for c in ('typ', 'max'):
                k = n + 'read' + c + st
                if k not in src: continue
                p, b = src[k], B[k]
                w, wb = src[n + 'write' + c + st], B[n + 'write' + c + st]
                d1 = dly(p, b); d2 = dly(w, wb)
                print('| %s | %s | %s | %s | %.1f %% -> %.1f %% | %.3f V | %.1f %% | %.3f/%.3f | %+.3f..%+.3f | %.3f / %.3f | %+.3f..%+.3f | %s' % (
                    n, p.get('ref') or '-', st, c, 100 * b['pin']['budget'], 100 * p['pin']['budget'], p['pin']['vmin'], 100 * p['die']['budget'],
                    p['pin']['ringback_into_band'], p['die']['ringback_into_band'], d1[0], d1[1], w['pin']['vmin'], w['pin']['vmax'], d2[0], d2[1], tag))
