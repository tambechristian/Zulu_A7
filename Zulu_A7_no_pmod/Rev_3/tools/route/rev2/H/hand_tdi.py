"""hand_tdi.py: strategy H hand step for TDI (and the TDO dip it needs) round the moved X2.30 (36.83,1.27).
Rev 1 TDI: U2.17 -> L3 diagonal (27.6,6.8)-(32.2,5.7) -> Top hop at x 32.2 down to 4.3 -> L3 y 4.0 to 35.1 -> L3
diagonal to 37.7,1.4 -> L4 to the edge lane y 0.3 -> L4 lane east to 42.7 -> through via 43.4,1.0 -> Top lane to JP4.
X2.30 now sits on the L3 diagonal and the buried via, and VU uses the pad 2 / MP2 gap of X4. With hand_vu2 (VU 0.5 at
x 31.715 in that gap) TDI's Top hop fits beside VU at x 32.215:
  * L3 32.2,5.7 -> 32.215,5.7, Top>L2>L3 stack, Top down to 32.215,4.0, Top>L2>L3 stack, L3 to the kept Rev 1 run
    (32.6,4.0)-(35.1,4.0);
  * L3 35.1,4.0 -> 36.45,2.65 -> 37.6,2.65 (over X2.30) -> 37.95,2.3 -> 37.95,1.4 (X2.30 / X2.29 gap), L3>L4 buried
    via, L4 down to the lane y 0.36 (X2.29 / X2.28 0.11 clear, edge 0.022 clear) and east to the Rev 1 L4 diagonal
    (42.7,0.3)-(43.4,1.0) at 42.76,0.36; the Rev 1 lane (38.8,0.3)-(42.7,0.3)-(43.4,1.0) is replaced by the new
    lane and the diagonal's upper part (42.76,0.36)-(43.4,1.0) (new copper keeps 0.3 from the board edge);
  * TDO (router copper) dipped into that gap to its Rev 1 via 38.15,1.35: it now runs straight over X2.29's corner,
    L4 37.075,2.175 -> 39.0,2.2; the via column 38.15,1.35, L4 (38.15,1.35)-(39.0,2.2) and the dead Bottom stub go.
Writes hand_tdi.json {tracks, vias (fixed), remove, remove_vias (board), drop_seed (router copper)}."""
import json

STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
W = 0.0762


def tr(net, pts, layer, w=W):
    return [{'net': net, 'layer': layer, 'w': w, 'x1': a[0], 'y1': a[1], 'x2': b[0], 'y2': b[1]}
            for a, b in zip(pts, pts[1:])]


def V(net, x, y, size, hole, fr, to):
    return {'net': net, 'x': x, 'y': y, 'size': size, 'hole': hole, 'from': fr, 'to': to}


def stack_top(net, x, y):
    return [V(net, x, y, 0.3, 0.15, 'Top Layer', 'L2-GND'), V(net, x, y, 0.3, 0.15, 'L2-GND', 'L3-SIG')]


XH = 32.215
step = {
    'tracks': tr('TDI', [(32.2, 5.7), (XH, 5.7)], 'L3-SIG') + tr('TDI', [(XH, 5.7), (XH, 4.0)], 'Top Layer') +
              tr('TDI', [(XH, 4.0), (32.6, 4.0)], 'L3-SIG') +
              tr('TDI', [(35.1, 4.0), (36.45, 2.65), (37.6, 2.65), (37.95, 2.3), (37.95, 1.4)], 'L3-SIG') +
              tr('TDI', [(37.95, 1.4), (38.99, 0.36), (42.76, 0.36), (43.4, 1.0)], 'L4-SIG') +
              tr('TDO', [(37.075, 2.175), (39.0, 2.2)], 'L4-SIG'),
    'vias': stack_top('TDI', XH, 5.7) + stack_top('TDI', XH, 4.0) + [V('TDI', 37.95, 1.4, 0.27, 0.15, 'L3-SIG', 'L4-SIG')],
    'remove': tr('TDO', [(38.15, 1.35), (39.0, 2.2)], 'L4-SIG') + tr('TDI', [(38.8, 0.3), (42.7, 0.3), (43.4, 1.0)], 'L4-SIG'),
    'remove_vias': [dict(V('TDO', 38.15, 1.35, 0.3, 0.15, 'L4-SIG', 'L5-VCC3V3'), span=['L4-SIG', 'L5-VCC3V3']),
                    dict(V('TDO', 38.15, 1.35, 0.3, 0.15, 'L5-VCC3V3', 'Bottom Layer'), span=['L5-VCC3V3', 'Bottom Layer'])],
    'drop_seed': {
        'tracks': tr('TDO', [(37.075, 2.175), (37.1, 2.15), (37.175, 2.15), (37.225, 2.125), (37.25, 2.1), (37.275, 2.1),
                             (37.3, 2.075), (37.325, 2.075), (37.4, 2.0), (37.425, 2.0), (38.075, 1.35), (38.15, 1.35)],
                      'L4-SIG') + tr('TDO', [(37.6474, 0.8474), (38.15, 1.35)], 'Bottom Layer'),
        'vias': []},
}
json.dump(step, open('hand_tdi.json', 'w'), indent=1)
print('hand_tdi: %d tracks, %d vias, remove %d + %d' % (len(step['tracks']), len(step['vias']), len(step['remove']),
                                                        len(step['remove_vias'])))
