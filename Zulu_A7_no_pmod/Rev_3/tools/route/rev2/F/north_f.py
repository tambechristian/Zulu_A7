"""north_f.py <out_step.json> -- strategy F hand routes around the moved X2.10 (36.83, 24.13) and X1's slots, Rev 2.

Under X1's MS1 / MS2 slots and X2.10 every layer already carries one fence track (Top CHAN10 / USB5V0, L3 LED0_R,
L4 CHAN9 / CHAN13, Bottom FPGA-TCK), so the nets that have to cross the band are placed by hand:
  CHAN7     X2.10 -> Top, down between X2.10 / CHAN8's diagonal and USB5V0's 0.45 riser at x 37.25 -> Top>L2>L3 stack
            on top of its own L3 run at (37.5, 21.0); its dead Bottom branch (to X2.10's old spot) and the
            L3>L4>L5>Bottom column at 37.5,21.0 that fed it are removed
  FPGA-TCK  Bottom, arc around X2.10's south-east (r 0.95) between its two cut pieces
  LED0_R    L3, the same arc on L3
  CHAN12    Bottom: from its west piece north past MS1's west side, over MS1 / MS2 / X2.10 at y 25.04 (its old run sat
            at 25.02 and failed X2.10's clearance by 0.0001), L4>L5>Bottom stack at (37.6, 24.94) east of X2.10, L4 down
            X2.10's east side onto its own L4 run end at (37.45, 23.4775); the old orphan run is removed
  CHAN13    Top west end -> Top>L2>L3>L4 column at (26.10, 23.45) west of MS1 -> L4 between CHAN9 (y 22.75) and MS1
            at y 22.92 -> its own L4 piece at (28.6, 23.225); under MS2 its L4 run dips to y 22.88"""
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


cx, cy = 36.83, 24.13
arc = [(cx + 0.95 * math.cos(math.radians(a)), cy + 0.95 * math.sin(math.radians(a))) for a in (-57, -45, -33)]
tracks = (run('CHAN7', 'Top Layer', [(37.25, 23.55), (37.25, 21.25), (37.5, 21.0)]) +
          run('FPGA-TCK', 'Bottom Layer', [(37.2177, 23.3177)] + arc + [(37.6423, 23.7423)]) +
          run('LED0_R', 'L3-SIG', [(37.2177, 23.3177)] + arc + [(37.6423, 23.7423)]) +
          run('CHAN12', 'Bottom Layer', [(26.2868, 23.15), (26.2868, 24.95), (26.3768, 25.04), (37.5, 25.04),
                                         (37.6, 24.94)]) +
          run('CHAN12', 'L4-SIG', [(37.6, 24.94), (37.75, 24.79), (37.75, 23.78), (37.45, 23.4775)]) +
          run('CHAN13', 'Top Layer', [(26.2419, 23.225), (26.10, 23.45)]) +
          run('CHAN13', 'L4-SIG', [(26.10, 23.45), (26.10, 23.183), (26.363, 22.92), (28.2, 22.92), (28.505, 23.225),
                                   (28.6, 23.225)]) +
          run('CHAN13', 'L4-SIG', [(33.3131, 22.9727), (33.40, 22.88), (34.56, 22.88), (34.64, 22.9637)]))
vias = [via('CHAN7', 37.5, 21.0, 'Top Layer', 'L2-GND'), via('CHAN7', 37.5, 21.0, 'L2-GND', 'L3-SIG'),
        via('CHAN12', 37.6, 24.94, 'L4-SIG', 'L5-VCC3V3'), via('CHAN12', 37.6, 24.94, 'L5-VCC3V3', 'Bottom Layer'),
        via('CHAN13', 26.10, 23.45, 'Top Layer', 'L2-GND'), via('CHAN13', 26.10, 23.45, 'L2-GND', 'L3-SIG'),
        via('CHAN13', 26.10, 23.45, 'L3-SIG', 'L4-SIG', 0.27)]
remove = [T('CHAN7', 'Bottom Layer', 31.945, 22.6, 35.9, 22.6), T('CHAN7', 'Bottom Layer', 35.9, 22.6, 37.5, 21.0),
          T('CHAN12', 'Bottom Layer', 27.673, 23.15, 27.95, 23.15), T('CHAN12', 'Bottom Layer', 27.95, 23.15, 28.72, 23.92),
          T('CHAN12', 'Bottom Layer', 28.72, 23.92, 28.72, 24.62), T('CHAN12', 'Bottom Layer', 28.72, 24.62, 29.12, 25.02),
          T('CHAN12', 'Bottom Layer', 29.12, 25.02, 36.6955, 25.02)]
remove_vias = [via('CHAN7', 37.5, 21.0, 'L3-SIG', 'L4-SIG', 0.27), via('CHAN7', 37.5, 21.0, 'L4-SIG', 'L5-VCC3V3'),
               via('CHAN7', 37.5, 21.0, 'L5-VCC3V3', 'Bottom Layer')]
json.dump({'tracks': tracks, 'vias': vias, 'remove': remove, 'remove_vias': remove_vias}, open(sys.argv[1], 'w'),
          indent=0)
print('north: %d tracks %d vias, removes %d tracks %d vias' % (len(tracks), len(vias), len(remove), len(remove_vias)))
