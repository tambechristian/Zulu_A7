"""hand_c20.py: strategy H hand step for CHAN20 from its moved pad X2.30 (36.83,1.27) to U1.V15.
Rev 1 CHAN20 came along L4 y 1.27 from the old pad (26.67), climbed to 37.0,2.475, L3 to 38.825,2.475 and NE to a
Top>L2>L3 stack at 40.075,3.725, then Top y 4.075 to 46.05,4.4 (kept from there to the ball). With hand_tdi's TDI
hook (L3 over X2.30, down the X2.30 / X2.29 gap at x 37.95) CHAN20 leaves the pad on L4 under that hook:
  * L4 from inside the pad 37.4,1.6 to an L3>L4 buried via at 38.5,1.85 (between TDI's buried via and TDO's L4 run);
  * L3 38.5,1.85 -> 38.825,2.475 -> 40.075,3.725 (the Rev 1 line, 0.28 from ANALOG-IO1's parallel L3 run),
    Top>L2>L3 stack at 40.075,3.725, Top 40.075,3.725 -> 40.6,4.075 -> 45.725,4.075 -> 46.05,4.4 (Rev 1).
Writes hand_c20.json {tracks, vias (fixed)}."""
import json

W = 0.0762


def tr(net, pts, layer, w=W):
    return [{'net': net, 'layer': layer, 'w': w, 'x1': a[0], 'y1': a[1], 'x2': b[0], 'y2': b[1]}
            for a, b in zip(pts, pts[1:])]


def V(net, x, y, size, hole, fr, to):
    return {'net': net, 'x': x, 'y': y, 'size': size, 'hole': hole, 'from': fr, 'to': to}


step = {
    'tracks': tr('CHAN20', [(37.4, 1.6), (38.5, 1.85)], 'L4-SIG') +
              tr('CHAN20', [(38.5, 1.85), (38.825, 2.475), (40.075, 3.725)], 'L3-SIG') +
              tr('CHAN20', [(40.075, 3.725), (40.6, 4.075), (45.725, 4.075), (46.05, 4.4)], 'Top Layer'),
    'vias': [V('CHAN20', 38.5, 1.85, 0.27, 0.15, 'L3-SIG', 'L4-SIG'),
             V('CHAN20', 40.075, 3.725, 0.3, 0.15, 'Top Layer', 'L2-GND'),
             V('CHAN20', 40.075, 3.725, 0.3, 0.15, 'L2-GND', 'L3-SIG')],
    'remove': [], 'remove_vias': [],
}
json.dump(step, open('hand_c20.json', 'w'), indent=1)
print('hand_c20: %d tracks, %d vias' % (len(step['tracks']), len(step['vias'])))
