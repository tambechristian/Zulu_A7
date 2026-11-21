"""south_f.py <out_step.json> -- strategy F hand routes around the moved X2.30 (36.83, 1.27), Rev 2.

X2.30 (1.524 mm through-hole land) blocks y 0.38-2.16 on every layer; under it there is room for one 3 mil track
per layer (y 0.338-0.380): L3 and Bottom already carry ANALOG-IO0 / ANALOG-IO1 there, Top and L4 are free.
  CHAN25  its L3 west end -> Top>L2>L3 stack at (35.80, 1.00) -> Top under X2.30, X2.29, X2.28 at y 0.36 (its old
          run there sat at y 0.30, 0.04 inside route_check's 0.30 edge rule for new copper) -> its via column at
          (42.9, 1.0); its L3 east piece, the stack at 38.2,1.0 and the old Top run 38.2,1.0 -> 42.9,1.0 are removed
  TDO     its Bottom west run -> L4>L5>Bottom stack at (35.75, 0.65) -> L4 under X2.30 at y 0.36 -> its L4 run at
          (38.15, 1.35); the Bottom east piece and the L4>L5>Bottom stack at 38.15,1.35 are removed
  TDI     its L3 orphan run (from 35.1,4.0) -> L3 around X2.30's north-east at radius >= 0.93 -> buried L3>L4 via at
          (38.30, 0.90) between X2.30 and X2.29 -> L4 at y 0.36 under X2.29 / X2.28 to its through via at
          (43.4, 1.0); the old L4 stub (37.72,1.38)-(38.8,0.3) and run (38.8,0.3)-(43.4,1.0) are removed
  SD-CMD  Bottom, threads between X2.30 and FT-VPLL to its north piece at (36.65, 2.152); C7.2's VCC3V3 feed moves
          its L5>Bottom tie from (36.14, 1.98) (removed with X2.30's move) to a microvia at (36.143, 2.40)"""
import json
import math
import sys

W = 0.0762


def run(net, layer, pts, w=W):
    return [{'net': net, 'layer': layer, 'w': w, 'x1': round(a[0], 4), 'y1': round(a[1], 4), 'x2': round(b[0], 4),
             'y2': round(b[1], 4)} for a, b in zip(pts, pts[1:])]


def via(net, x, y, fr, to, size=0.3, hole=0.15):
    return {'net': net, 'x': x, 'y': y, 'size': size, 'hole': hole, 'from': fr, 'to': to}


def T(net, layer, x1, y1, x2, y2, w=W):
    return {'net': net, 'layer': layer, 'w': w, 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2}


cx, cy, R = 36.83, 1.27, 0.95
arc = [(cx + R * math.cos(math.radians(a)), cy + R * math.sin(math.radians(a))) for a in (62, 36, 12)]
tracks = (run('CHAN25', 'Top Layer', [(35.80, 1.00), (36.44, 0.36), (42.26, 0.36), (42.9, 1.0)]) +
          run('TDO', 'L4-SIG', [(35.75, 0.65), (36.04, 0.36), (37.45, 0.36), (38.15, 1.35)]) +
          run('TDI', 'L3-SIG', [(36.9362, 2.1638)] + arc + [(38.30, 0.90)]) +
          run('TDI', 'L4-SIG', [(38.30, 0.90), (38.84, 0.36), (42.76, 0.36), (43.4, 1.0)]) +
          run('SD-CMD', 'Bottom Layer', [(35.932, 1.332), (35.95, 1.72), (36.327, 2.097), (36.65, 2.1519)]) +
          run('VCC3V3', 'Bottom Layer', [(36.143, 2.40), (36.1502, 3.05)], w=0.2))
vias = [via('CHAN25', 35.80, 1.00, 'Top Layer', 'L2-GND'), via('CHAN25', 35.80, 1.00, 'L2-GND', 'L3-SIG'),
        via('TDO', 35.75, 0.65, 'L4-SIG', 'L5-VCC3V3'), via('TDO', 35.75, 0.65, 'L5-VCC3V3', 'Bottom Layer'),
        via('TDI', 38.30, 0.90, 'L3-SIG', 'L4-SIG', 0.27),
        via('VCC3V3', 36.143, 2.40, 'L5-VCC3V3', 'Bottom Layer')]
remove = [T('CHAN25', 'L3-SIG', 37.6887, 1.0, 38.2, 1.0), T('CHAN25', 'Top Layer', 38.2, 1.0, 38.9, 0.3),
          T('CHAN25', 'Top Layer', 38.9, 0.3, 42.2, 0.3), T('CHAN25', 'Top Layer', 42.2, 0.3, 42.9, 1.0),
          T('TDI', 'L4-SIG', 38.8, 0.3, 42.7, 0.3), T('TDI', 'L4-SIG', 42.7, 0.3, 43.4, 1.0),
          T('TDO', 'Bottom Layer', 37.5938, 0.7938, 38.15, 1.35),
          T('TDI', 'L4-SIG', 37.7238, 1.3762, 38.8, 0.3),
          T('VCC3V3', 'Bottom Layer', 36.14, 1.98, 36.1502, 3.05, 0.2)]
remove_vias = [via('CHAN25', 38.2, 1.0, 'Top Layer', 'L2-GND'), via('CHAN25', 38.2, 1.0, 'L2-GND', 'L3-SIG'),
               via('TDO', 38.15, 1.35, 'L4-SIG', 'L5-VCC3V3'), via('TDO', 38.15, 1.35, 'L5-VCC3V3', 'Bottom Layer')]
json.dump({'tracks': tracks, 'vias': vias, 'remove': remove, 'remove_vias': remove_vias}, open(sys.argv[1], 'w'),
          indent=0)
print('south: %d tracks %d vias, removes %d tracks %d vias' % (len(tracks), len(vias), len(remove), len(remove_vias)))
