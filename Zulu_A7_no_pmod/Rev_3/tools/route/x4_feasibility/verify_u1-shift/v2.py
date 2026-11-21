exec(open('v1.py').read().split("def key")[0])
def worst(res):
    w = {}
    for r in res:
        k = r[:4]
        if k not in w or r[5] < w[k][5]: w[k] = r
    return w
for g in (0.10, 0.20):
    wa = worst(bc.check(bc.build(M, D), None, g)); wb = worst(bc.check(bc.build(M2, D2), None, g))
    print('gap', g, 'base', len(wa), 'cand', len(wb))
    for k in sorted(wb):
        if k not in wa: print('  NEW', wb[k])
        elif wb[k][5] < wa[k][5]-1e-6: print('  WORSE', wa[k], '->', wb[k])
    for k in sorted(wa):
        if k not in wb: print('  gone', wa[k])
print([p for p in M['pads'] if p['ref']=='X4'])
print([p for p in M2['pads'] if p['ref']=='X4'])
