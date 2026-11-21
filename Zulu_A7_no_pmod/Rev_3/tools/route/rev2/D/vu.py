"""Strategy D hand VU (X4 moved 2.54 mm west): Rev 1 VU threaded X4 MP1/pad1/pad2; now the MP1-pad1 gap holds the
VCC3V3 through via at 27.93,4.85, so that via becomes an L5->Bottom laser (Bottom ties to U3 kept, Top tracks to the
U2 pin removed -> the router re-ties that pin to the plane), the dead TDI stubs between pad2 and MP2 are ripped, and VU
runs: west 1.5 run -> under MP1 -> up the MP1/pad1 gap -> over pads 1+2 -> down the pad2/MP2 gap -> under MP2 -> the
kept 0.7 stub at 34.45,3.366.  Writes vu.json {tracks, vias, remove, remove_vias}."""
import json
STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
def tr(net, w, a, b, layer='Top Layer'): return dict(net=net, layer=layer, w=w, x1=a[0], y1=a[1], x2=b[0], y2=b[1])
P = [(16.69, 4.9493), (23.06, 4.9493), (24.76, 4.1), (25.06, 3.3), (27.81, 3.3), (27.81, 6.0), (28.06, 6.25),
     (31.66, 6.25), (31.91, 6.0), (31.91, 3.25), (34.3, 3.25), (34.45, 3.366)]
W = [1.5, 1.4] + [0.7] * 9
out = {'tracks': [tr('VU', w, a, b) for w, a, b in zip(W, P, P[1:])],
       'vias': [dict(net='VCC3V3', x=27.93, y=4.85, size=0.3, hole=0.15, span=['L5-VCC3V3', 'Bottom Layer'])],
       'remove': [tr('VCC3V3', 0.3, (27.93, 4.85), (27.93, 6.5)), tr('VCC3V3', 0.145, (27.93, 6.5), (27.93, 6.9625)),
                  tr('VCC3V3', 0.145, (27.93, 6.9625), (29.2251, 6.9625)),
                  tr('TDI', 0.0762, (32.2, 4.3), (32.2, 5.7)), tr('TDI', 0.0762, (27.6, 6.8), (32.2, 5.7), 'L3-SIG'),
                  tr('TDI', 0.0762, (32.6, 4.0), (35.1, 4.0), 'L3-SIG')],
       'remove_vias': [dict(net='VCC3V3', x=27.93, y=4.85, size=0.35, hole=0.2, span=STACK)]}
json.dump(out, open('vu.json', 'w'), indent=1)
