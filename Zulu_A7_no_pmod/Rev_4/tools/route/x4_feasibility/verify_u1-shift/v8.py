exec(open('v7.py').read().split("refs = sorted")[0])
for r in ['C116','C117','C118','C120','C8','C100','C101','C102','C103','C104','L6','R133','R13','R15','R17','R21','R22','R11']:
    ps = [p for p in M['pads'] if p['ref']==r]
    out = []
    for p in ps:
        cand = [q for q in u1o.values() if q['net']==p['net']]
        if p['net']=='GND' or not cand: out.append((p['pad'], p['net'], round(p['x'],2), round(p['y'],2))); continue
        do = min(math.hypot(p['x']-q['x'], p['y']-q['y']) for q in cand); dn = min(math.hypot(p['x']-u1n[q['pad']]['x'], p['y']-u1n[q['pad']]['y']) for q in cand)
        out.append((p['pad'], p['net'], round(p['x'],2), round(p['y'],2), 'U1 nearest', round(do,2), '->', round(dn,2)))
    print(r, Cs[r]['layer'], out)
print('U1 body old', min(q['x'] for q in u1o.values()), max(q['x'] for q in u1o.values()), min(q['y'] for q in u1o.values()), max(q['y'] for q in u1o.values()))
