"""mk_d.py: delta plan relative to ../wf_place/final_model.json -> d1.json
VBATT: drop the in-pad part (L4-L5, L5-Bottom) of the U8-23 stack; three Top->L4 stacks on the Top VBATT track
(10.55, 11.05, 11.75 @ y 14.75), an L4 bus to two Bottom<-L5<-L4 stacks in C151-2.
USB5V0: Bottom trunk moved to the L8-2 (VU, quiet) side of the L8 gap (x 12.125 -> 12.5)."""
import json
M = json.load(open('../wf_place/final_model.json'))
T, B, L3, L4 = 'Top Layer', 'Bottom Layer', 'L3-SIG', 'L4-SIG'


def tr(net, layer, w, pts):
    return [dict(net=net, layer=layer, w=w, x1=a[0], y1=a[1], x2=b[0], y2=b[1]) for a, b in zip(pts, pts[1:])]


def via(net, x, y, a, b, size, hole):
    return {'net': net, 'x': x, 'y': y, 'size': size, 'hole': hole, 'from': a, 'to': b}


def find_t(net, layer, p1, p2):
    out = [t for t in M['tracks'] if t['net'] == net and t['layer'] == layer and
           {(round(t['x1'], 3), round(t['y1'], 3)), (round(t['x2'], 3), round(t['y2'], 3))} == {p1, p2}]
    assert len(out) == 1, (net, p1, p2, out)
    return out[0]


rem, remv, tracks, vias = [], [], [], []
# ---- USB5V0 trunk
rem += [find_t('USB5V0', B, (11.45, 13.2), (12.125, 13.2)), find_t('USB5V0', B, (12.125, 13.2), (12.125, 12.8)),
        find_t('USB5V0', B, (12.125, 12.8), (12.125, 10.2))]
tracks += tr('USB5V0', B, 0.3, [(11.45, 13.2), (12.5, 13.2), (12.5, 12.9)]) + tr('USB5V0', B, 0.4, [(12.5, 12.9), (12.5, 10.2)])
# ---- VBATT
remv += [v for v in M['vias'] if v['net'] == 'VBATT' and abs(v['x'] - 11.75) < 1e-3 and abs(v['y'] - 14.75) < 1e-3]
Y = 14.75
for X in (10.22, 11.05, 11.75):
    vias += [via('VBATT', X, Y, T, 'L2-GND', 0.30, 0.15), via('VBATT', X, Y, 'L2-GND', L3, 0.30, 0.15),
             via('VBATT', X, Y, L3, L4, 0.27, 0.15)]
CX = 12.3
for CY in (14.15, 14.7):
    vias += [via('VBATT', CX, CY, L4, 'L5-VCC3V3', 0.30, 0.15), via('VBATT', CX, CY, 'L5-VCC3V3', B, 0.30, 0.15)]
tracks += tr('VBATT', L4, 0.4, [(10.22, Y), (CX, 14.7), (CX, 14.15)])
json.dump({'tracks': tracks, 'vias': vias, 'remove': rem, 'remove_vias': remv}, open('d1.json', 'w'), indent=0)
print(len(tracks), len(vias), len(rem), len(remv))
