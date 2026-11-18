"""Stage 2 hand copper on top of hand.json (+ the router's PWR_FB2 piece):
USB5V0 via-in-pad at U8-25 (B>L5>L4, 0.25/0.10), L4 run to a via in C150-2;
VBATT via-in-pad stack at U8-23 up to Top (0.25/0.10 x5), Top run to X4-1;
PWR_PGOODALL's inner-layer middle (under U8-23) ripped for re-route."""
import json, sys
base = json.load(open(sys.argv[1]))      # placed.json (input model for the plan)
hand = json.load(open(sys.argv[2]))      # hand.json
fb2 = json.load(open(sys.argv[3]))       # r1a.partial.json (PWR_FB2 only)
out = sys.argv[4]
B, L5, L4, L3, L2, TOP = 'Bottom Layer', 'L5-VCC3V3', 'L4-SIG', 'L3-SIG', 'L2-GND', 'Top Layer'
def T(net, w, x1, y1, x2, y2, L):
    return {'net': net, 'layer': L, 'w': w, 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2}
def V(net, x, y, a, b, s=0.25, h=0.10):
    return {'net': net, 'x': x, 'y': y, 'size': s, 'hole': h, 'from': a, 'to': b}
tracks = list(hand['tracks']) + [t for t in fb2['tracks'] if t['net'] == 'PWR_FB2']
vias = [v for v in fb2['vias'] if v['net'] == 'PWR_FB2']
# USB5V0
ux, uy = 10.75, 14.8
vias += [V('USB5V0', ux, uy, B, L5), V('USB5V0', ux, uy, L5, L4)]
cx, cy = 11.375, 11.65
vias += [V('USB5V0', cx, cy, B, L5, 0.3, 0.15), V('USB5V0', cx, cy, L5, L4, 0.3, 0.15)]
tracks += [T('USB5V0', 0.25, ux, uy, ux, 12.275, L4), T('USB5V0', 0.25, ux, 12.275, cx, cy, L4)]
# VBATT
bx, by = 11.75, 14.7
for a, b in ((B, L5), (L5, L4), (L4, L3), (L3, L2), (L2, TOP)):
    vias.append(V('VBATT', bx, by, a, b))
tracks += [T('VBATT', 0.3, bx, by, 10.25, by, TOP), T('VBATT', 0.3, 10.25, by, 10.1, 15.15, TOP)]
rm = list(hand['remove'])
# PWR_PGOODALL middle
def on(t, pts):
    return (round(t['x1'], 3), round(t['y1'], 3), round(t['x2'], 3), round(t['y2'], 3)) in pts
pg = {(8.75, 11.2, 9.85, 12.3), (9.85, 12.3, 9.85, 12.625), (9.85, 12.625, 11.325, 14.1), (11.325, 14.1, 11.8, 14.875),
      (11.8, 14.875, 11.85, 15.5), (11.85, 15.5, 11.825, 15.8), (11.825, 15.8, 11.825, 18.275),
      (11.825, 18.275, 11.775, 18.325), (11.775, 18.325, 11.775, 18.625), (11.775, 18.625, 12.125, 18.975)}
hit = [t for t in base['tracks'] if t['net'] == 'PWR_PGOODALL' and on(t, pg)]
assert len(hit) == len(pg), len(hit)
rm += hit
rmv = [v for v in base['vias'] if v['net'] == 'PWR_PGOODALL' and (round(v['x'], 3), round(v['y'], 3)) in {(11.8, 14.875), (11.85, 15.5)}]
assert len(rmv) == 2
json.dump({'tracks': tracks, 'vias': vias, 'remove': rm, 'remove_vias': rmv}, open(out, 'w'), indent=1)
print('tracks', len(tracks), 'vias', len(vias), 'remove', len(rm), 'remove_vias', len(rmv))
