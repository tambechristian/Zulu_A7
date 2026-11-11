"""mk.py <placed model> <out plan> : wf_vip2 hand copper, relative to the placed model (frozenC + placement2)."""
import json, sys
base = json.load(open(sys.argv[1]))
pv = json.load(open('../wf_vip/plan_vip.json'))
B, L5, L4, L3, L2, TOP = 'Bottom Layer', 'L5-VCC3V3', 'L4-SIG', 'L3-SIG', 'L2-GND', 'Top Layer'
ST = [TOP, L2, L3, L4, L5, B]
def T(net, w, x1, y1, x2, y2, L): return {'net': net, 'layer': L, 'w': w, 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2}
def V(net, x, y, a, b, s=0.30, h=0.15): return {'net': net, 'x': x, 'y': y, 'size': s, 'hole': h, 'from': a, 'to': b}
def stack(net, x, y, a, b, s=0.30, h=0.15):
    i, j = sorted((ST.index(a), ST.index(b)))
    return [V(net, x, y, ST[k], ST[k + 1], s, h) for k in range(i, j)]
def path(net, w, L, pts): return [T(net, w, p[0], p[1], q[0], q[1], L) for p, q in zip(pts, pts[1:])]
def k3(x): return round(x, 3)
# ---- keep from plan_vip
drop_t = set()
tracks, vias = [], []
for t in pv['tracks']:
    n = t['net']
    if n in ('VBATT', 'PWR_SW', 'VU', 'GND'): continue
    if n == 'USB5V0' and t['layer'] == L4 and (k3(t['x1']), k3(t['y1'])) in {(10.75, 14.8), (11.25, 14.3), (11.25, 11.775), (11.375, 11.65), (11.375, 10.575)}: continue
    if n == 'USB5V0' and t['layer'] == L4 and (k3(t['x1']), k3(t['y1'])) in {(14.3, 15.8), (14.3, 11.2), (13.85, 10.4), (12.85, 10.28), (12.69, 9.911), (12.69, 9.4), (11.5, 9.4), (11.0, 9.9), (11.0, 10.2)}: continue
    if n == 'PWR_FB2' and (t['layer'] == B or (k3(t['x1']), k3(t['y1'])) == (9.525, 13.95)): continue
    if n == 'PWR_PROG' and (k3(t['x1']), k3(t['y1'])) in {(13.35, 10.7), (13.35, 14.9)}: continue
    if n == 'USB5V0' and t['layer'] in (L3, L4) and t['w'] < 0.25: t = dict(t, w=0.25)
    tracks.append(t)
for v in pv['vias']:
    n = v['net']
    if n in ('VBATT',): continue
    if n == 'VU' and (k3(v['x']), k3(v['y'])) == (10.8, 13.6): continue
    if n == 'USB5V0' and (k3(v['x']), k3(v['y'])) in {(10.75, 14.8), (11.375, 11.65)}: continue
    if n == 'PWR_FB2' and (k3(v['x']), k3(v['y'])) == (9.025, 13.3): continue
    vias.append(v)
# ---- PWR_SW: U8-26 -> between C150's pads -> L8-1 west face, Bottom only, no vias
tracks += path('PWR_SW', 0.3, B, [(10.25, 14.9), (10.3, 14.55), (10.3, 13.0), (10.6, 12.7)])
tracks += path('PWR_SW', 0.5, B, [(10.6, 12.7), (11.3, 12.7), (12.35, 11.65), (12.35, 11.35)])
# ---- C167 (VIN1 cap, loose): C167-2 onto R108-1 (VU), C167-1 sits on the GND via at (9.4,11.25)
tracks += [T('VU', 0.3, 10.95, 11.3, 10.85, 10.8, B)]
# ---- C150 (VBUS bypass): U8-25 -> C150-2, U8-27 -> C150-1 (direct Bottom)
tracks += [T('USB5V0', 0.25, 10.75, 14.9, 10.75, 13.9, B), T('GND', 0.25, 9.75, 14.9, 9.75, 13.9, B)]
for y in (13.3, 13.75):
    vias += stack('USB5V0', 11.35, y, B, L4)
tracks += path('USB5V0', 0.25, L4, [(11.35, 13.75), (11.35, 13.3), (10.25, 12.2), (10.25, 10.2), (7.9, 10.2)])
tracks += path('USB5V0', 0.25, L4, [(14.3, 15.8), (14.3, 13.9), (11.5, 13.9), (11.35, 13.75)])
# ---- VU: U8-24 -> over C150-2 -> L8-2; L8-2 -> C147-2 -> through via (15.55,14.225)
tracks += path('VU', 0.25, B, [(11.25, 14.9), (11.25, 14.3), (11.95, 14.3)])
tracks += path('VU', 0.3, B, [(11.95, 14.3), (11.95, 13.5)])
tracks += [T('VU', 0.8, 13.9, 13.2, 14.6, 13.2, B), T('VU', 0.4, 15.2, 13.5, 15.55, 14.225, B)]
vias += stack('VU', 12.25, 12.95, B, L4)
tracks += path('VU', 0.3, L4, [(12.25, 12.95), (11.75, 12.45), (11.75, 11.0), (11.35, 10.6), (10.625, 10.6)])
# ---- VBATT: U8-23 -> C151-2 (Bottom), two parallel 0.30/0.15 stacks Bottom..Top, Top run to X4-1
tracks += [T('VBATT', 0.4, 11.75, 14.9, 12.75, 14.9, B)]
for x in (12.05, 12.45):
    vias += stack('VBATT', x, 14.9, B, L4)
tracks += path('VBATT', 0.35, L4, [(11.15, 14.725), (11.6, 14.725), (12.05, 14.9), (12.45, 14.9)])
for x in (11.15, 11.6):
    vias += stack('VBATT', x, 14.725, L4, TOP)
tracks += path('VBATT', 0.35, TOP, [(11.6, 14.725), (10.25, 14.725), (10.25, 15.3)])
# ---- GND: C151-1 and C147-1
vias += stack('GND', 14.75, 14.6, B, L2)
vias += stack('GND', 15.15, 11.25, B, L2)
tracks += [T('GND', 0.4, 14.775, 10.4, 14.775, 11.2, B)]
# ---- PWR_PROG: L4 up x 13.35 to a new L3-L4 via at (13.35,15.55), L3 to the through via
vias += [V('PWR_PROG', 13.35, 10.7, L3, L4, 0.27, 0.15)]
tracks += path('PWR_PROG', 0.0762, L3, [(13.35, 10.7), (13.35, 14.95), (13.45, 15.15), (13.45, 15.55)])
tracks += [T('PWR_PROG', 0.0762, 13.45, 15.55, 12.675, 16.475, L3)]
# ---- removals
rm = list(pv['remove'])
def find(net, L, x1, y1, x2, y2):
    h = [t for t in base['tracks'] if t['net'] == net and t['layer'] == L and
         {(k3(t['x1']), k3(t['y1'])), (k3(t['x2']), k3(t['y2']))} == {(x1, y1), (x2, y2)}]
    assert len(h) == 1, (net, x1, y1, len(h))
    return h[0]
rm += [find('VU', B, 14.2, 13.975, 14.775, 13.975), find('VU', B, 15.55, 14.225, 14.2, 14.225),
       find('GND', B, 14.775, 12.675, 14.75, 12.675), find('PWR_PROG', L3, 12.7, 14.95, 12.675, 16.475)]
rv = list(pv['remove_vias'])
for v in base['vias']:
    if (v['net'], k3(v['x']), k3(v['y'])) in {('GND', 14.75, 12.675), ('PWR_PROG', 12.7, 14.95)}:
        rv.append(v)
for v in vias:
    if ST.index(v['from']) > ST.index(v['to']): v['from'], v['to'] = v['to'], v['from']
json.dump({'tracks': tracks, 'vias': vias, 'remove': rm, 'remove_vias': rv}, open(sys.argv[2], 'w'), indent=1)
print('tracks', len(tracks), 'vias', len(vias), 'remove', len(rm), 'remove_vias', len(rv))
# ---- merge router legs (relative to the same placed model: they only add copper)
import os
P = json.load(open(sys.argv[2]))
for f in ('rfb2.json', 'r167.json'):
    if os.path.exists(f):
        R = json.load(open(f)); assert not R.get('remove')
        P['tracks'] += R['tracks']; P['vias'] += R['vias']
json.dump(P, open(sys.argv[2], 'w'), indent=1)
print('merged; tracks', len(P['tracks']), 'vias', len(P['vias']))
