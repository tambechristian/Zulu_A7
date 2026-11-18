"""hand1.py: hand escapes for USB5V0 and VBATT (relative to modelE)."""
import json, os
H = os.path.dirname(os.path.abspath(__file__))
B, L4, L5 = 'Bottom Layer', 'L4-SIG', 'L5-VCC3V3'
T, V = [], []
def tr(net, layer, w, pts):
    for (a, b), (c, d) in zip(pts, pts[1:]):
        T.append({'net': net, 'layer': layer, 'w': w, 'x1': a, 'y1': b, 'x2': c, 'y2': d})
def stack(net, x, y, size=0.3, hole=0.15):
    V.append({'net': net, 'x': x, 'y': y, 'size': size, 'hole': hole, 'from': L4, 'to': L5})
    V.append({'net': net, 'x': x, 'y': y, 'size': size, 'hole': hole, 'from': L5, 'to': B})
# USB5V0: pin 25 -> Bottom corridor -> stack -> L4 -> C150-2
UV = (10.925, 13.165)
tr('USB5V0', B, 0.2, [(10.75, 14.6), (10.925, 14.425), UV])
stack('USB5V0', *UV)
CV = (11.0, 11.95)
tr('USB5V0', L4, 0.25, [UV, CV])
stack('USB5V0', *CV)
# VBATT: pin 23 via-in-pad (small laser) -> L4 west around the USB stack -> north -> east to C151-2
PV = (11.75, 14.75)
stack('VBATT', *PV, size=0.25, hole=0.10)
C1 = (12.2, 11.25)
tr('VBATT', L4, 0.25, [PV, (11.0, 14.0), (10.55, 13.55), (10.5, 13.0), (10.5, 11.75), (10.85, 11.4), (12.05, 11.4), C1])
stack('VBATT', *C1)
json.dump({'tracks': T, 'vias': V}, open(os.path.join(H, 'hand1.json'), 'w'), indent=0)
