"""hand_ft.py: strategy H hand step for FPGA-TCK in the north band (X1 moved 2.54 west, X2.10 now at 36.83,24.13).
FPGA-TCK's Rev 1 run was Bottom y 22.9 from U10's west side to 36.8 then NE to its L4 via at 38.3,24.4. The router
had put CHAN12 on that line (Bottom y 22.9, 26.35 -> 31.925) because CHAN12's Rev 1 detour round MS1 no longer fits.
  * CHAN12 (router copper) leaves y 22.9: its Bottom y 23.15 run stops at x 26.2 (west of MS1), goes north to the
    board-edge lane y 25.02 (over MS1: 0.118 clear, 0.042 inside the 0.3 edge rule), east to x 31.925, down to a new
    L5>Bottom + L4>L5 laser stack at 31.925,23.6 and on L4 back to its L4 run at 31.925,22.9 (the old stack there
    goes);
  * FPGA-TCK (fixed): from its kept Bottom stub end 19.75,22.05 north to y 22.9, east along y 22.9 to x 35.5 (west of
    CHAN7's X2.10 escape), north to the edge lane y 25.03, east over X2.10 (0.10 clear), down to its L4 via 38.3,24.4.
Writes hand_ft.json {tracks, vias (fixed), drop_seed (router copper replaced)}."""
import json

W = 0.0762


def tr(net, pts, layer='Bottom Layer', w=W):
    return [{'net': net, 'layer': layer, 'w': w, 'x1': a[0], 'y1': a[1], 'x2': b[0], 'y2': b[1]}
            for a, b in zip(pts, pts[1:])]


def V(net, x, y, size, hole, fr, to):
    return {'net': net, 'x': x, 'y': y, 'size': size, 'hole': hole, 'from': fr, 'to': to}


FT = [(19.75, 22.05), (19.75, 22.9), (35.5, 22.9), (35.5, 25.03), (37.9, 25.03), (38.3, 24.63), (38.3, 24.4)]
C12 = [(16.25, 23.15), (26.2, 23.15), (26.2, 25.02), (31.925, 25.02), (31.925, 23.6)]
step = {
    'tracks': tr('FPGA-TCK', FT) + tr('CHAN12', C12) + tr('CHAN12', [(31.925, 23.6), (31.925, 22.9)], 'L4-SIG'),
    'vias': [V('CHAN12', 31.925, 23.6, 0.3, 0.15, 'L4-SIG', 'L5-VCC3V3'),
             V('CHAN12', 31.925, 23.6, 0.3, 0.15, 'L5-VCC3V3', 'Bottom Layer')],
    'remove': [], 'remove_vias': [],
    'drop_seed': {
        'tracks': tr('CHAN12', [(16.25, 23.15), (26.2464, 23.15)]) + tr('CHAN12', [(26.25, 23.15), (26.275, 23.125)]) +
                  tr('CHAN12', [(26.275, 23.125), (26.275, 22.975)]) + tr('CHAN12', [(26.275, 22.975), (26.35, 22.9)]) +
                  tr('CHAN12', [(26.35, 22.9), (31.925, 22.9)]),
        'vias': [V('CHAN12', 31.925, 22.9, 0.3, 0.15, 'L4-SIG', 'L5-VCC3V3'),
                 V('CHAN12', 31.925, 22.9, 0.3, 0.15, 'L5-VCC3V3', 'Bottom Layer')]},
}
json.dump(step, open('hand_ft.json', 'w'), indent=1)
print('hand_ft: %d tracks, %d vias' % (len(step['tracks']), len(step['vias'])))
