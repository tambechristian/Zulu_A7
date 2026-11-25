"""south_hand.py <model.json> <out_plan.json> -- hand routes around the moved X2.30 (36.83, 1.27), Rev 2.

X2.30 (a 1.524 mm through-hole land) now sits on the old CHAN25 / TDO / SD-CMD / TDI runs. Below the land there is
room for exactly one 3 mil track per layer (y 0.338-0.380); Bottom and L3 already use theirs (ANALOG-IO1,
ANALOG-IO0), so
  CHAN25  L3 west end -> Top>L2>L3 stack at (35.80, 1.00) -> Top under X2.30 at y 0.36 -> onto its own Top
          diagonal at (38.84, 0.36) (the old L3 east piece and its stack at 38.2,1.0 become dead and are pruned);
  TDO     Bottom west run -> L4>L5>Bottom stack at (35.75, 0.65) -> L4 under X2.30 at y 0.36 -> its L4 stack at
          (38.15, 1.35) (the old Bottom east piece is pruned); TDI's dangling L4 stub (37.72,1.38)-(38.8,0.3), in the
          way, is removed (TDI is routed by the router onto its L4 run further east);
  SD-CMD  Bottom, threads between X2.30 and C7.2's VCC3V3 tie, which moves from (36.15, 2.05) to (36.143, 2.40)
          (L5>Bottom microvia on the C7.2 feed).
"""
import json
import sys

M = json.load(open(sys.argv[1]))


def find_t(net, layer, a, b):
    pts = {(round(a[0], 3), round(a[1], 3)), (round(b[0], 3), round(b[1], 3))}
    out = [t for t in M['tracks'] if t['net'] == net and t['layer'] == layer and
           {(round(t['x1'], 3), round(t['y1'], 3)), (round(t['x2'], 3), round(t['y2'], 3))} == pts]
    assert len(out) == 1, (net, layer, pts, len(out))
    return {k: v for k, v in out[0].items()}


def find_v(net, x, y):
    out = [v for v in M['vias'] if v['net'] == net and abs(v['x'] - x) < 1e-3 and abs(v['y'] - y) < 1e-3]
    assert out, (net, x, y)
    return [{'net': v['net'], 'x': v['x'], 'y': v['y'], 'size': v['size'], 'hole': v['hole'], 'from': v['span'][0],
             'to': v['span'][-1]} for v in out]


def run(net, layer, pts, w=0.0762):
    return [{'net': net, 'layer': layer, 'w': w, 'x1': a[0], 'y1': a[1], 'x2': b[0], 'y2': b[1]}
            for a, b in zip(pts, pts[1:])]


def via(net, x, y, fr, to, size=0.3):
    return {'net': net, 'x': x, 'y': y, 'size': size, 'hole': 0.15, 'from': fr, 'to': to}


tracks, vias = [], []
# CHAN25
vias += [via('CHAN25', 35.80, 1.00, 'Top Layer', 'L2-GND'), via('CHAN25', 35.80, 1.00, 'L2-GND', 'L3-SIG')]
tracks += run('CHAN25', 'Top Layer', [(35.80, 1.00), (36.15, 0.36), (38.84, 0.36)])
# TDO
vias += [via('TDO', 35.75, 0.65, 'L4-SIG', 'L5-VCC3V3'), via('TDO', 35.75, 0.65, 'L5-VCC3V3', 'Bottom Layer')]
tracks += run('TDO', 'L4-SIG', [(35.75, 0.65), (36.05, 0.36), (37.45, 0.36), (38.15, 1.35)])
# SD-CMD + the C7.2 VCC3V3 tie moved out of its way
tracks += run('SD-CMD', 'Bottom Layer', [(35.9344, 1.3344), (35.95, 1.72), (36.327, 2.097), (36.65, 2.15)])
vias += [via('VCC3V3', 36.143, 2.40, 'L5-VCC3V3', 'Bottom Layer')]
tracks += run('VCC3V3', 'Bottom Layer', [(36.143, 2.40), (36.1502, 3.05)], w=0.2)
remove = [find_t('TDI', 'L4-SIG', (38.8, 0.3), (37.7217, 1.3783)),
          find_t('VCC3V3', 'Bottom Layer', (36.14, 1.98), (36.1502, 3.05)),
          find_t('VCC3V3', 'Bottom Layer', (36.15, 2.05), (36.1407, 2.0501))]
remove_vias = find_v('VCC3V3', 36.15, 2.05)
json.dump({'tracks': tracks, 'vias': vias, 'remove': remove, 'remove_vias': remove_vias}, open(sys.argv[2], 'w'),
          indent=1)
print('south hand: %d tracks, %d vias; removes %d tracks, %d vias' % (len(tracks), len(vias), len(remove),
                                                                     len(remove_vias)))
