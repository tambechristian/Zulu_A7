"""mk_d2.py: USB5V0 X1 leg by hand, relative to m1.json -> d2.json
C150-2: two Bottom->L5->L4 stacks in-pad; L4 bus west at y 9.8 to x 8.1, then to the two X1-1 pads (Top) through
Top->L2->L3->L4 stacks in-pad (two in the north pad, one in the south pad)."""
import json
T, B, L3, L4 = 'Top Layer', 'Bottom Layer', 'L3-SIG', 'L4-SIG'


def tr(net, layer, w, pts):
    return [dict(net=net, layer=layer, w=w, x1=a[0], y1=a[1], x2=b[0], y2=b[1]) for a, b in zip(pts, pts[1:])]


def via(net, x, y, a, b, size, hole):
    return {'net': net, 'x': x, 'y': y, 'size': size, 'hole': hole, 'from': a, 'to': b}


def top_stack(x, y):
    return [via('USB5V0', x, y, T, 'L2-GND', 0.30, 0.15), via('USB5V0', x, y, 'L2-GND', L3, 0.30, 0.15),
            via('USB5V0', x, y, L3, L4, 0.27, 0.15)]


def bot_stack(x, y):
    return [via('USB5V0', x, y, L4, 'L5-VCC3V3', 0.30, 0.15), via('USB5V0', x, y, 'L5-VCC3V3', B, 0.30, 0.15)]


N = 'USB5V0'
CY = float(__import__('os').environ.get('CY', '9.65'))
YB = float(__import__('os').environ.get('YB', '9.8'))
vias = bot_stack(12.3, CY) + bot_stack(12.8, CY) + top_stack(7.25, 13.88) + top_stack(7.8, 13.88) + top_stack(7.2, 8.9)
tracks = tr(N, L4, 0.25, [(12.8, CY), (12.3, CY), (12.3, YB), (8.1, YB)])
tracks += tr(N, L4, 0.25, [(7.2, 8.9), (8.1, 8.9)]) + tr(N, L4, 0.3, [(8.1, 8.9), (8.1, YB), (7.5, 10.4), (7.5, 13.88)])
tracks += tr(N, L4, 0.3, [(7.25, 13.88), (7.8, 13.88)])
json.dump({'tracks': tracks, 'vias': vias, 'remove': [], 'remove_vias': []}, open('d2.json', 'w'), indent=0)
print(len(tracks), len(vias))
