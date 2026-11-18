"""Build the removal list + hand-routed core copper for the wf_place placement (pl_try4)."""
import json
M = json.load(open('../model_frozenC.json'))
RM_T = [4339, 4348, 4610, 4611, 4612] + list(range(4776, 4785)) + [4837, 4838] + list(range(4706, 4712)) + \
       [4346, 4509, 4510]
RM_V = [('GND', 14.75, 12.675), ('GND', 13.075, 9.8), ('PWR_PROG', 12.35, 10.025), ('LD4_A', 10.275, 9.025)]
rem = [M['tracks'][i] for i in RM_T]
remv = [v for v in M['vias'] if any(v['net'] == n and abs(v['x'] - x) < 1e-3 and abs(v['y'] - y) < 1e-3 for n, x, y in RM_V)]
print('remove %d tracks %d vias' % (len(rem), len(remv)))
B = 'Bottom Layer'


def T(net, w, pts):
    return [{'net': net, 'layer': B, 'w': w, 'x1': a[0], 'y1': a[1], 'x2': b[0], 'y2': b[1]} for a, b in zip(pts, pts[1:])]


tr = []
# PWR_SW: U8-26 (10.25,14.9) straight down into L8-1 (10.975,11.75; x 10.45-11.5, top 12.9)
tr += T('PWR_SW', 0.25, [(10.25, 14.8), (10.35, 14.35)])
tr += T('PWR_SW', 0.4, [(10.35, 14.35), (10.75, 12.75)])
tr += T('PWR_SW', 0.6, [(10.75, 12.75), (10.85, 12.3)])
# USB5V0: U8-25 (10.75,14.9) over L8-1, down the gap between the L8 pads into C150-2 (12.55,9.9)
tr += T('USB5V0', 0.25, [(10.75, 14.8), (10.85, 14.3)])
tr += T('USB5V0', 0.3, [(10.85, 14.3), (11.45, 13.2), (12.125, 13.2), (12.125, 12.8)])
tr += T('USB5V0', 0.4, [(12.125, 12.8), (12.125, 10.2)])
# VU: U8-24 (11.25,14.9) -> L8-2 (13.325,11.75; x 12.8-13.85 top 12.9) -> C147-2 (14.55,13.1) -> VU via (15.55,14.225)
tr += T('VU', 0.25, [(11.25, 14.8), (11.3, 14.4)])
tr += T('VU', 0.3, [(11.3, 14.4), (11.75, 13.62)])
tr += T('VU', 0.35, [(11.75, 13.62), (12.95, 13.62), (13.15, 12.7)])
tr += T('VU', 0.5, [(13.5, 12.6), (14.4, 12.9)])
tr += T('VU', 0.4, [(14.75, 13.35), (15.55, 14.225)])
# VBATT: U8-23 (11.75,14.9) sideways into C151-2 (12.625,14.45)
tr += T('VBATT', 0.3, [(11.75, 14.85), (12.35, 14.6)])
plan = {'tracks': tr, 'vias': [], 'remove': rem, 'remove_vias': remv}
json.dump(plan, open('manual.json', 'w'), indent=0)
