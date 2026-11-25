import json, math, re, sys, collections
T = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_4/tools'
sys.path.insert(0, T)
import route_conn as C
import body_check as BC
KI = 'C:/Program Files/KiCad/10.0/share/kicad/footprints/'
M0 = json.load(open(T + '/route/bodies/base.json'))
D0 = json.load(open(T + '/route/bodies/comps.json'))
NP = json.load(open('newpads_14.675_30.375_31.39_0.0.json'))

def kpads(f):
    s = open(KI + f).read()
    out = []
    for m in re.finditer(r'\(pad "([^"]*)" smd (\w+)\s*\(at ([-\d.]+) ([-\d.]+)(?: [-\d.]+)?\)\s*\(size ([-\d.]+) ([-\d.]+)\)', s):
        out.append((m.group(1), float(m.group(3)), float(m.group(4)), float(m.group(5)), float(m.group(6))))
    return out

# ---- old LQFP orientation ----
u2old = {p['pad']: p for p in M0['pads'] if p['ref'] == 'U2'}
print('old U2 pin1', u2old['1']['x'], u2old['1']['y'], 'pin17', u2old['17']['x'], u2old['17']['y'], 'pin49', u2old['49']['x'], u2old['49']['y'])
# ---- QFN from KiCad, y-down -> y-up ----
XC, YC = 30.375, 14.675
q = {}
for n, x, y, w, h in kpads('Package_DFN_QFN.pretty/QFN-64-1EP_9x9mm_P0.5mm_EP4.35x4.35mm.kicad_mod'):
    if n and n != '65':
        q[n] = (XC + x, YC - y, w, h)
cand_u2 = {p['pad']: p for p in NP['u2']}
mx = max(abs(q[n][0] - cand_u2[n]['x']) + abs(q[n][1] - cand_u2[n]['y']) for n in q)
print('QFN pads vs candidate: max |d| %.4f' % mx, 'nets same as LQFP:', all(cand_u2[n]['net'] == u2old[n]['net'] for n in q))
# ---- S2B correct orientation: KiCad rot 0 = mating face (+y KiCad = down) toward board y=0 ----
CX, CY = 31.39, 4.9
s2b = kpads('Connector_JST.pretty/JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal.kicad_mod')
print('S2B kicad pads', s2b)
corr = [(n, CX + x, CY - y) for n, x, y, w, h in s2b]
print('correct S2B (y-up, MP toward y=0):', corr)
print('candidate S2B:', [(p['pad'], p['x'], p['y'], p['net']) for p in NP['x4']])
# KiCad B2B sanity (same convention as the released board X4)
b2b = kpads('Connector_JST.pretty/JST_PH_B2B-PH-SM4-TB_1x02-1MP_P2.00mm_Vertical.kicad_mod')
print('KiCad B2B', b2b, ' board X4', [(p['pad'], p['x'], p['y']) for p in M0['pads'] if p['ref'] == 'X4'])
