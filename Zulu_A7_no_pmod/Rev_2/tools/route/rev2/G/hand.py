"""hand.py <base_moved.json> <usb_plan.json> <out_hand.json>
Strategy G hand copper (hard nets first), on top of rip_g.py's minimal rip:
  VU      X4 moved 2.54 west: south of MP1 (0.3 neck between VBATT and MP1), up the MP1/pad1 gap (0.7), over pads
          1+2 (0.7), down the pad2/MP2 gap (0.4, TDI keeps x 32.2), south of MP2 (0.7) to the kept stub at 34.45,3.366;
          the VCC3V3 through via at 27.93,4.85 in the MP1/pad1 gap becomes an L5>Bottom laser and its Top stub to the
          U2 VCC3V3 bus is removed (the router re-ties the bus).
  TDI     keeps its whole old route; the pad2/MP2 gap Top stub now drops at 32.2,4.0 (Top>L2>L3) onto the kept L3
          piece to 35.1,4.0, then L3 down x 35.7 -> buried via 35.7,2.2 -> L4 under X2.30 along y 0.3 to the kept
          east through via 43.4,1.0 (y 0.34 keeps the 0.30 edge rule; the old y 0.3 run is replaced).
  CHAN20  L4 connector from the new X2.30 land to the kept buried via 37.0,2.475 (the old L4 run west is dead).
  CHAN7   Top from the new X2.10 land, east of USB5V0, to a Top>L2>L3 stack on the kept L3 via point 37.5,21.0 (the old
          Bottom/L4 tail and the L3>L4/L4>L5/L5>Bo column there are dead).
  USB5V0  X1.1 joined to the kept wide Rev 1 route at 34.32,22.5 (north of MH2), 0.4 wide.
  GND     X4 pad 2 to the kept GND via 32.55,2.25.
  FPGA-TCK / LED0_R / CHAN12   re-joined around the new X2.10 land.
  USB pair + CHAN10: B's usb_hand.py (bump 28.75 / 0.195).
"""
import json
import sys

sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools')
import compose_plan as CP  # noqa: E402

STACK = CP.STACK
B = json.load(open(sys.argv[1]))
U = json.load(open(sys.argv[2]))
out = {'tracks': [], 'vias': [], 'remove': [], 'remove_vias': []}
LAY = {'T': 'Top Layer', '3': 'L3-SIG', '4': 'L4-SIG', 'B': 'Bottom Layer'}


def path(net, layer, w, pts):
    if not isinstance(w, (list, tuple)):
        w = [w] * (len(pts) - 1)
    for (a, b), ww in zip(zip(pts, pts[1:]), w):
        out['tracks'].append({'net': net, 'layer': LAY.get(layer, layer), 'w': ww, 'x1': a[0], 'y1': a[1], 'x2': b[0], 'y2': b[1]})


def via(net, x, y, fr, to, size=0.30, hole=0.15):
    out['vias'].append({'net': net, 'x': x, 'y': y, 'size': size, 'hole': hole, 'from': LAY.get(fr, fr), 'to': LAY.get(to, to)})


def rm_track(net, layer, a, b):
    layer = LAY.get(layer, layer)
    hit = [t for t in B['tracks'] if t['net'] == net and t['layer'] == layer and
           {(round(t['x1'], 3), round(t['y1'], 3)), (round(t['x2'], 3), round(t['y2'], 3))} ==
           {(round(a[0], 3), round(a[1], 3)), (round(b[0], 3), round(b[1], 3))}]
    assert len(hit) == 1, (net, layer, a, b, len(hit))
    out['remove'].append(hit[0])


def rm_via(net, x, y, span=None):
    hit = [v for v in B['vias'] if v['net'] == net and abs(v['x'] - x) < 1e-3 and abs(v['y'] - y) < 1e-3 and
           (span is None or (v['span'][0], v['span'][-1]) == span)]
    assert hit, (net, x, y, span)
    out['remove_vias'] += hit


def rm_chain(net, layer, pts):
    for a, b in zip(pts, pts[1:]):
        rm_track(net, layer, a, b)


# ---- USB pair + CHAN10 (B)
out['tracks'] += U['tracks']
out['vias'] += U['vias']
for t in U['remove']:
    rm_track(t['net'], t['layer'], (t['x1'], t['y1']), (t['x2'], t['y2']))
for v in U['remove_vias']:
    rm_via(v['net'], v['x'], v['y'], (v['from'], v['to']))

# ---- VU
path('VU', 'T', [1.5, 0.7, 0.3, 0.3, 0.7, 0.7, 0.7, 0.4, 0.4, 0.7, 0.7],
     [(16.69, 4.9493), (23.4, 4.9493), (24.3, 4.05), (24.8, 3.55), (27.81, 3.55), (27.81, 6.095), (28.06, 6.345),
      (31.75, 6.345), (31.75, 3.6), (32.1, 3.25), (34.3, 3.25), (34.45, 3.366)])
rm_via('VCC3V3', 27.93, 4.85)
via('VCC3V3', 27.93, 4.85, 'L5-VCC3V3', 'B')
rm_chain('VCC3V3', 'T', [(27.93, 4.85), (27.93, 6.5), (27.93, 6.9625), (29.2251, 6.9625)])

# ---- TDI
rm_track('TDI', 'T', (32.2, 4.3), (32.2, 5.7))
path('TDI', 'T', 0.0762, [(32.2, 4.0), (32.2, 5.7)])
via('TDI', 32.2, 4.0, 'T', 'L2-GND')
via('TDI', 32.2, 4.0, 'L2-GND', '3')
path('TDI', '3', 0.0762, [(32.2, 4.0), (32.6, 4.0)])
path('TDI', '3', 0.0762, [(35.1, 4.0), (35.5, 3.6), (35.7, 3.4), (35.7, 2.2)])
via('TDI', 35.7, 2.2, '3', '4', 0.27, 0.15)
path('TDI', '4', 0.0762, [(35.7, 2.2), (35.7, 0.64), (36.0, 0.34), (42.74, 0.34), (43.4, 1.0)])
rm_chain('TDI', '4', [(38.8, 0.3), (42.7, 0.3), (43.4, 1.0)])

# ---- CHAN20
path('CHAN20', '4', 0.0762, [(36.83, 1.27), (37.0, 2.475)])
rm_chain('CHAN20', '4', [(26.67, 1.27), (31.645, 1.27), (32.2, 1.825), (32.375, 1.9), (34.275, 2.325), (37.0, 2.475)])

# ---- CHAN7
path('CHAN7', 'T', 0.0762, [(36.83, 24.13), (37.25, 23.71), (37.25, 21.25), (37.5, 21.0)])
via('CHAN7', 37.5, 21.0, 'T', 'L2-GND')
via('CHAN7', 37.5, 21.0, 'L2-GND', '3')
rm_via('CHAN7', 37.5, 21.0)                       # L3>L4, L4>L5, L5>Bo column: only the dead Bottom tail used it
rm_track('CHAN7', 'B', (35.9, 22.6), (37.5, 21.0))
rm_via('CHAN7', 30.85, 22.6)
rm_chain('CHAN7', '4', [(27.85, 22.95), (28.55, 22.95), (28.6, 22.9), (29.1, 22.9), (29.15, 22.85), (29.2, 22.85),
                        (29.45, 22.6), (30.85, 22.6)])

# ---- USB5V0
path('USB5V0', 'T', 0.4, [(31.78, 21.2585), (31.78, 21.9), (32.18, 22.3), (32.38, 22.5), (34.32, 22.5)])
rm_track('USB5V0', 'T', (34.32, 21.259), (34.32, 22.5))

# ---- GND: X4 pad 2 to the kept via
path('GND', 'T', 0.5, [(31.1, 2.25), (32.55, 2.25)])

# ---- GND: X1 MP1..MP4 linked on Top as in Rev 1 (MP2 / MP3 have no other tie; no via in a pad)
path('GND', 'T', 0.5, [(27.2801, 23.9585), (33.6799, 23.9585)])

# ---- around X2.10
path('FPGA-TCK', 'B', 0.0762, [(36.8, 22.9), (37.9, 22.9), (38.3, 23.3), (38.3, 24.4)])
path('LED0_R', '3', 0.0762, [(36.8, 22.9), (37.8, 22.9), (38.3, 23.4), (38.3, 24.4)])
path('CHAN12', 'B', 0.0762, [(36.83, 25.02), (37.6, 25.02), (37.85, 24.77), (37.85, 23.55)])
via('CHAN12', 37.85, 23.55, 'L5-VCC3V3', 'B')
via('CHAN12', 37.85, 23.55, '4', 'L5-VCC3V3')
path('CHAN12', '4', 0.0762, [(37.85, 23.55), (37.85, 23.15)])

# ---- CHAN13 (X2.16 -> U1): Top along y 23.225 as before to x 25.3, Top>L2>L3>L4 there, L4 between X1's MS/MH rows
#      at y 22.925 to the kept L4 run at 40.325; CHAN9's L4 jog moves 0.35 south to make that lane
path('CHAN13', 'T', 0.0762, [(12.335, 23.225), (25.3, 23.225)])
via('CHAN13', 25.3, 23.225, 'T', 'L2-GND')
via('CHAN13', 25.3, 23.225, 'L2-GND', '3')
via('CHAN13', 25.3, 23.225, '3', '4', 0.27, 0.15)
path('CHAN13', '4', 0.0762, [(25.3, 23.225), (25.6, 22.925), (40.325, 22.925)])
rm_chain('CHAN13', '4', [(28.6, 23.225), (29.075, 23.225), (29.3, 23.0)])
rm_chain('CHAN9', '4', [(22.62, 23.1), (25.9, 23.1), (26.25, 22.75)])
path('CHAN9', '4', 0.0762, [(22.62, 23.1), (22.97, 22.75), (26.25, 22.75)])

# ---- CHAN12 (X2.15 -> U1): Bottom y 23.15 as before to x 25.4, up between X2.11 and MS1, over MS1 along y 25.02 to
#      the kept run at 29.12 (the old jog round MS1's new place is dead)
path('CHAN12', 'B', 0.0762, [(16.25, 23.15), (25.4, 23.15), (25.6, 23.35), (25.6, 24.8), (25.82, 25.02), (29.12, 25.02)])
rm_chain('CHAN12', 'B', [(27.95, 23.15), (28.72, 23.92), (28.72, 24.62), (29.12, 25.02)])

json.dump(out, open(sys.argv[3], 'w'), indent=1)
print('hand: %d tracks, %d vias; remove %d tracks, %d vias' % (len(out['tracks']), len(out['vias']), len(out['remove']),
                                                               len(out['remove_vias'])))
