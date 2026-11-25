import json, math, sys, copy, subprocess, collections
T = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_4/tools'
sys.path.insert(0, T)
import route_conn as C
import body_check as BC
M0 = json.load(open(T + '/route/bodies/base.json'))
MM = json.load(open('model_14.675_30.375_31.39_0.0.json'))
L = lambda t: math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1'])
print('base tracks %d len %.1f vias %d' % (len(M0['tracks']), sum(map(L, M0['tracks'])), len(M0['vias'])))
print('model tracks %d len %.1f vias %d' % (len(MM['tracks']), sum(map(L, MM['tracks'])), len(MM['vias'])))
oc = C.open_count(C.islands(MM)); oc = {k: v for k, v in oc.items() if v}
print('open in rip model: %d on %d nets' % (sum(oc.values()), len(oc)), sorted(oc))
# ---- body check on the final board, candidate comps ----
D = json.load(open('comps_14.675_30.375_31.39_0.0.json'))
BC.BODY['FT2232HQ-QFN64'] = (9.0, 9.0, 9.1, 9.1)
F = json.load(open('final_vu.json'))
parts = BC.build(F, D)
r = BC.check(parts, {'U2', 'X4'}, 0.10)
print('body_check U2/X4 findings:', r)
print('X4 body', parts['Top']['X4']['body'], 'U2 body', parts['Top']['U2']['body'])
allf = BC.check(parts, None, 0.10)
base = BC.check(BC.build(M0, json.load(open(T + '/route/bodies/comps.json'))), None, 0.10)
key = lambda f: json.dumps(f, sort_keys=True, default=str)[:120]
print('all findings final %d base %d' % (len(allf), len(base)))
bs = {key(f) for f in base}
print('NEW vs base:', [f for f in allf if key(f) not in bs][:10])
# ---- mirrored S2B: swap X4 pad nets to the true footprint and recheck ----
S = copy.deepcopy(json.load(open('modelA_d6_vu.json')))
for p in S['pads']:
    if p['ref'] == 'X4' and p['pad'] in ('1', '2'):
        p['net'] = {'1': 'GND', '2': 'VBATT'}[p['pad']]   # real pin 1 (VBATT) sits at x 30.39, pin 2 (GND) at 32.39
print('swapped X4', [(p['pad'], p['x'], p['net']) for p in S['pads'] if p['ref'] == 'X4'])
json.dump(S, open('modelA_d6_vu_swapped.json', 'w'))
