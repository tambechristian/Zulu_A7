"""Stage 3 hand copper = hand2 (minus its USB5V0 L4 run) + router PGOODALL (r2a) + hand USB5V0 west/L4,
VU->R108 on L4, VBATT C151 on L4, PWR_PROG L4 detour east of the VBATT run."""
import json, sys
base = json.load(open(sys.argv[1]))      # placed.json
h2 = json.load(open(sys.argv[2]))        # hand2.json
pg = json.load(open(sys.argv[3]))        # r2a.json (PWR_PGOODALL)
out = sys.argv[4]
B, L5, L4, L3, L2, TOP = 'Bottom Layer', 'L5-VCC3V3', 'L4-SIG', 'L3-SIG', 'L2-GND', 'Top Layer'
def T(net, w, x1, y1, x2, y2, L):
    return {'net': net, 'layer': L, 'w': w, 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2}
def V(net, x, y, a, b, s=0.25, h=0.10):
    return {'net': net, 'x': x, 'y': y, 'size': s, 'hole': h, 'from': a, 'to': b}
tracks = [t for t in h2['tracks'] if not (t['net'] == 'USB5V0' and t['layer'] == L4)]
tracks += [t for t in pg['tracks'] if t['net'] == 'PWR_PGOODALL']
vias = list(h2['vias']) + [v for v in pg['vias'] if v['net'] == 'PWR_PGOODALL']
# USB5V0: U8-25 stack (10.75,14.8) -> C150-2 via (11.375,11.65) on L4, east of the VU run
tracks += [T('USB5V0', 0.25, 10.75, 14.8, 11.25, 14.3, L4), T('USB5V0', 0.25, 11.25, 14.3, 11.25, 11.775, L4),
           T('USB5V0', 0.25, 11.25, 11.775, 11.375, 11.65, L4)]
# C150-2 -> west along y 10.2 (north of R108's via) to both X1-1 pads
tracks += [T('USB5V0', 0.25, 11.375, 11.65, 11.375, 10.575, L4), T('USB5V0', 0.25, 11.375, 10.575, 11.0, 10.2, L4),
           T('USB5V0', 0.25, 11.0, 10.2, 7.9, 10.2, L4),
           T('USB5V0', 0.25, 7.9, 10.2, 7.9, 13.88, L4),
           T('USB5V0', 0.25, 8.29, 10.2, 8.29, 8.98, L4)]
for (x, y) in ((7.9, 13.88), (8.29, 8.98)):
    for a, b in ((TOP, L2), (L2, L3), (L3, L4)):
        vias.append(V('USB5V0', x, y, a, b))
# VU: R108-1 via-in-pad -> L4 -> via in C167-2
vias += [V('VU', 10.625, 10.6, B, L5, 0.3, 0.15), V('VU', 10.625, 10.6, L5, L4, 0.3, 0.15),
         V('VU', 10.8, 13.6, B, L5, 0.3, 0.15), V('VU', 10.8, 13.6, L5, L4, 0.3, 0.15)]
tracks += [T('VU', 0.3, 10.625, 10.6, 10.625, 13.425, L4), T('VU', 0.3, 10.625, 13.425, 10.8, 13.6, L4)]
# VBATT: C151-2 via -> L4 -> the U8-23 stack
vias += [V('VBATT', 12.5, 11.0, B, L5, 0.3, 0.15), V('VBATT', 12.5, 11.0, L5, L4, 0.3, 0.15)]
tracks += [T('VBATT', 0.3, 12.5, 11.0, 12.2, 11.3, L4), T('VBATT', 0.3, 12.2, 11.3, 12.2, 14.25, L4),
           T('VBATT', 0.3, 12.2, 14.25, 11.75, 14.7, L4)]
# PWR_PROG: L4 detour east
tracks += [T('PWR_PROG', 0.0762, 12.35, 10.025, 12.75, 10.425, L4), T('PWR_PROG', 0.0762, 12.75, 10.425, 13.35, 10.425, L4),
           T('PWR_PROG', 0.0762, 13.35, 10.425, 13.35, 14.9, L4), T('PWR_PROG', 0.0762, 13.35, 14.9, 12.7, 14.95, L4)]
rm = list(h2['remove'])
def find(net, L, x1, y1, x2, y2):
    h = [t for t in base['tracks'] if t['net'] == net and t['layer'] == L and
         {(round(t['x1'], 3), round(t['y1'], 3)), (round(t['x2'], 3), round(t['y2'], 3))} == {(x1, y1), (x2, y2)}]
    assert len(h) == 1, (net, x1, y1)
    return h[0]
rm += [find('PWR_PROG', L4, 12.35, 10.025, 12.7, 12.3), find('PWR_PROG', L4, 12.7, 12.3, 12.7, 14.95)]
ST = [TOP, L2, L3, L4, L5, B]
for v in vias:
    if ST.index(v['from']) > ST.index(v['to']):
        v['from'], v['to'] = v['to'], v['from']
json.dump({'tracks': tracks, 'vias': vias, 'remove': rm, 'remove_vias': h2['remove_vias']}, open(out, 'w'), indent=1)
print('tracks', len(tracks), 'vias', len(vias), 'remove', len(rm))
