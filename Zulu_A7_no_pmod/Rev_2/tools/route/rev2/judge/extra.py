import json, math, sys
from collections import Counter
sys.path.insert(0, '.')
from judge import tkey, vkey, tlen, span
T = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools/route/rev2/'
B = json.load(open(T + 'prep/base_moved.json'))
B0 = json.load(open(T + 'model_base.json'))
bd = Counter(tkey(t) for t in B['tracks'])
print('base dup tracks', sum(c - 1 for c in bd.values() if c > 1))
PL = {'E': 'E/plan_E8.json', 'F': 'F/plan_F.json', 'G': 'G/final_G2.json', 'H': 'H/plan_H_final.json'}
PW = ['VU', 'VBATT', 'USB5V0', 'VCC3V3', 'GND', 'VCC1V0', 'VCC1V8', 'NetL1_1', 'NetL2_1', 'NetL3_1']
for k, p in PL.items():
    P = json.load(open(T + p))
    Rz = json.load(open(k + '/result.json'))
    rc = Counter(tkey(t) for t in Rz['tracks'])
    newdup = [kk for kk, c in rc.items() if c > 1 and c > bd.get(kk, 0) + (0)]
    # plan tracks duplicating a track that stays on the board
    print('==', k, 'result dup tracks', sum(c - 1 for c in rc.values() if c > 1), 'dups not in base', len([kk for kk, c in rc.items() if c > max(1, bd.get(kk, 1))]))
    for kk in [kk for kk, c in rc.items() if c > max(1, bd.get(kk, 1))][:6]:
        print('   dup', kk)
    # power nets: added track widths
    for n in ['VU', 'VBATT', 'USB5V0', 'VCC3V3']:
        ts = [t for t in P['tracks'] if t['net'] == n]
        rs = [t for t in P['remove'] if t['net'] == n]
        if not ts and not rs:
            continue
        wl = Counter()
        for t in ts:
            wl[round(t['w'], 3)] += tlen(t)
        rl = Counter()
        for t in rs:
            rl[round(t['w'], 3)] += tlen(t)
        print('   %-7s added w->mm %s | removed %s' % (n, {w: round(l, 2) for w, l in sorted(wl.items())}, {w: round(l, 2) for w, l in sorted(rl.items())}))
    # plane web: vias of other nets on L2 / L5 added minus removed
    for lay, net in (('L2-GND', 'GND'), ('L5-VCC3V3', 'VCC3V3')):
        a = sum(1 for v in P['vias'] if lay in span(v) and v['net'] != net)
        r = sum(1 for v in P['remove_vias'] if lay in span(v) and v['net'] != net)
        print('   %s: other-net via objects on it +%d -%d' % (lay, a, r))
