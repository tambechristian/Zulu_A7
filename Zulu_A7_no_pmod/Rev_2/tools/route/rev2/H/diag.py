"""diag.py <tag> NET[,NET]: copper of NET present in the router view (base - rip + plus) but gone from board_<tag>"""
import json, sys
H = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools/route/rev2/H/'
sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools')
import compose_plan as CP
tag = sys.argv[1]; nets = set(sys.argv[2].split(','))
base = json.load(open(H + '../prep/base_moved.json'))
rip = json.load(open(H + 'rip_%s.json' % tag)); plus = json.load(open(H + 'plus_%s.json' % tag))
M0 = CP.apply(base, {'remove': rip['remove'], 'remove_vias': rip['remove_vias'], 'tracks': plus['tracks'], 'vias': plus['vias']})
M1 = json.load(open(H + 'board_%s.json' % tag))
k1 = {CP.tkey(t) for t in M1['tracks']}; v1 = {CP.vkey(v) for v in M1['vias']}
for t in M0['tracks']:
    if t['net'] in nets and CP.tkey(t) not in k1:
        print('GONE track', t['net'], t['layer'], t['w'], t['x1'], t['y1'], t['x2'], t['y2'])
for v in M0['vias']:
    if v['net'] in nets and CP.vkey(v) not in v1:
        print('GONE via', v['net'], v['x'], v['y'], v['span'][0], v['span'][-1])
for t in M1['tracks']:
    if t['net'] in nets and CP.tkey(t) not in {CP.tkey(x) for x in M0['tracks']}:
        print('NEW track', t['net'], t['layer'], t['w'], t['x1'], t['y1'], t['x2'], t['y2'])
