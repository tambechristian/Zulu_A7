"""hand_vu.py: strategy H hand step for VU around the moved X4 (LiPo JST, 2.54 mm west). Writes hand_vu.json
{tracks, vias, remove, remove_vias}: tracks/vias are FIXED copper (the router cannot rip them); remove/remove_vias
are base-board copper (prep/base_moved.json) taken out. Same idea as F/vu_hand.py and D/vu.py (old prep), re-derived
on the new base:
  * (hand_vu2.json, 2026-11-11 late: width 0.5 and the east gap run at x 31.715, so TDI's Top hop fits beside it)
  * VU threads X4 on Top as Rev 1 did, 2.54 mm further west: from the kept 1.5 mm west run (16.69 -> 24.699, y 4.9493)
    south, east under MP1 (y 3.4), north up the MP1 / pad 1 gap (x 27.81), east over pads 1-2 (y 6.3), south down the
    pad 2 / MP2 gap (x 31.91), east under MP2 (y 3.4) to the kept 0.7 stub end at 34.45,3.366. Width 0.6.
  * VBATT's west run (router seed copper: VBATT is a moved pad's net) drops from y 3.0 to 2.8 before x 24.5 so VU
    passes above it under MP1, then rejoins the 0.6 run at 26.5,2.5 -> 27.7,2.5 -> 28.45,1.55 -> X4 pad 1.
  * the VCC3V3 through via at 27.93,4.85 (Bottom decap hub + Top stub to U2.20, now in the MP1 / pad 1 gap) becomes an
    L5>Bottom microvia at the same spot; its Top stub goes (U2.20 stays on U2.31 along y 6.9625; the router re-ties
    that Top island to the plane).
  * TDI's dead Top hop at x 32.2 (in the pad 2 / MP2 gap) goes; TDI is re-routed by the router from its L3 run."""
import json
import sys

STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
W = float(sys.argv[1]) if len(sys.argv) > 1 else 0.6          # hand_vu.py [width] [east gap x] [out]
XE = float(sys.argv[2]) if len(sys.argv) > 2 else 31.91
OUT = sys.argv[3] if len(sys.argv) > 3 else 'hand_vu.json'
h = 0.3
VU = [(24.699, 4.9493), (24.699, 3.7), (24.699 + h, 3.4), (27.81 - h, 3.4), (27.81, 3.4 + h), (27.81, 6.3 - h),
      (27.81 + h, 6.3), (XE - h, 6.3), (XE, 6.3 - h), (XE, 3.4 + h), (XE + h, 3.4), (34.45, 3.366)]


def tr(net, pts, w, layer='Top Layer'):
    return [{'net': net, 'layer': layer, 'w': w, 'x1': a[0], 'y1': a[1], 'x2': b[0], 'y2': b[1]}
            for a, b in zip(pts, pts[1:])]


def T(net, x1, y1, x2, y2, w, layer='Top Layer'):
    return {'net': net, 'layer': layer, 'w': w, 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2}


def V(net, x, y, size, hole, fr, to):
    return {'net': net, 'x': x, 'y': y, 'size': size, 'hole': hole, 'from': fr, 'to': to}


step = {
    'tracks': [T('VU', 16.69, 4.9493, 24.699, 4.9493, 1.5)] + tr('VU', VU, W) +
              tr('VBATT', [(17.075, 3.0), (24.3, 3.0), (24.5, 2.8), (26.2, 2.8), (26.5, 2.5)], 0.4) +
              tr('VBATT', [(26.5, 2.5), (27.7, 2.5), (28.45, 1.55)], 0.6) +
              [T('VBATT', 28.45, 1.55, 28.86, 1.55, 1.2),
               T('VCC3V3', 29.2251, 6.9625, 34.7249, 6.9625, 0.145)],
    'vias': [V('VCC3V3', 27.93, 4.85, 0.3, 0.15, 'L5-VCC3V3', 'Bottom Layer'),
             V('VBATT', 17.075, 3.0, 0.35, 0.2, 'Top Layer', 'Bottom Layer')],
    'remove': [T('VCC3V3', 27.93, 4.85, 27.93, 6.5, 0.3), T('VCC3V3', 27.93, 6.5, 27.93, 6.9625, 0.145),
               T('VCC3V3', 27.93, 6.9625, 29.2251, 6.9625, 0.145), T('TDI', 32.2, 4.3, 32.2, 5.7, 0.0762)],
    'remove_vias': [dict(V('VCC3V3', 27.93, 4.85, 0.35, 0.2, 'Top Layer', 'Bottom Layer'), span=STACK)],
}
# seed copper these replace or clear (dropped from any seed plan used with hand_vu)
step['drop_seed'] = {
    'tracks': [T('VBATT', 17.075, 3.0, 25.5, 3.0, 0.4), T('VBATT', 25.5, 3.0, 26.5, 2.5, 0.6),
               T('VBATT', 26.5, 2.5, 27.7, 2.5, 0.6), T('VBATT', 27.7, 2.5, 28.45, 1.55, 0.6),
               T('VBATT', 28.45, 1.55, 29.6, 1.55, 1.2), T('VU', 16.69, 4.9493, 24.699, 4.9493, 1.5),
               T('VCC3V3', 29.2251, 6.9625, 34.7249, 6.9625, 0.145)],
    'vias': [V('VBATT', 17.075, 3.0, 0.35, 0.2, 'Top Layer', 'Bottom Layer'),
             V('TDI', 32.2, 5.7, 0.3, 0.15, 'Top Layer', 'L2-GND'), V('TDI', 32.2, 5.7, 0.3, 0.15, 'L2-GND', 'L3-SIG')]}
json.dump(step, open(OUT, 'w'), indent=1)
print('hand_vu: %d tracks, %d vias, remove %d tracks + %d vias' % (len(step['tracks']), len(step['vias']),
                                                                   len(step['remove']), len(step['remove_vias'])))
