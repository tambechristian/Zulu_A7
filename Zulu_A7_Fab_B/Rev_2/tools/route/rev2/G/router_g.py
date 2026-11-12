"""router_g.py <router.py args...>: tools/router.py with Strategy G's via policy patched in.
  * no through via (0.35/0.20) whose land overlaps ANY SMD pad (user rule for this board), exact raster per layer;
  * every route is first tried with NO via land overlapping an SMD pad at all (strict); only if that finds nothing
    is a microvia in a same-net pad allowed (lenient retry);
  * plane ties prefer microvia columns: GND from Bottom = L5>Bo + L4>L5 + L3>L4 + L2>L3 (no Top land), GND from L3 =
    L2>L3, GND from L4 = L3>L4 + L2>L3; VCC3V3 from L4 = L4>L5, from L3 = L3>L4 + L4>L5, from Top = stack_tie;
    through vias stay last.
"""
import math
import os
import sys

import numpy as np

T = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools'
sys.path.insert(0, T)
import router as R  # noqa: E402
import route_conn as C  # noqa: E402

S = R.STACK
R.VIAS['col_gnd'] = ([('L5-VCC3V3', 'Bottom Layer', 0.30, 0.15), ('L4-SIG', 'L5-VCC3V3', 0.30, 0.15),
                      ('L3-SIG', 'L4-SIG', 0.27, 0.15), ('L2-GND', 'L3-SIG', 0.30, 0.15)], S[1:6], ('Bottom Layer',))
R.VIAS['uvia_23'] = ([('L2-GND', 'L3-SIG', 0.30, 0.15)], S[1:3], ('L3-SIG',))
R.VIAS['col_gnd4'] = ([('L3-SIG', 'L4-SIG', 0.27, 0.15), ('L2-GND', 'L3-SIG', 0.30, 0.15)], S[1:4], ('L4-SIG',))
R.VIAS['uvia_45'] = ([('L4-SIG', 'L5-VCC3V3', 0.30, 0.15)], S[3:5], ('L4-SIG',))
R.VIAS['col_vcc3'] = ([('L3-SIG', 'L4-SIG', 0.27, 0.15), ('L4-SIG', 'L5-VCC3V3', 0.30, 0.15)], S[2:5], ('L3-SIG',))
for k, c in (('col_gnd', 1.2), ('uvia_23', 0.5), ('col_gnd4', 0.9), ('uvia_45', 0.5), ('col_vcc3', 0.9)):
    R.VIA_COST[k] = c
R.PLANE_VIAS['GND'] = {'Top Layer': ('uvia_top', 'stack_top', 'through'), 'Bottom Layer': ('col_gnd', 'through'),
                       'L3-SIG': ('uvia_23', 'stack_top'), 'L4-SIG': ('col_gnd4', 'through')}
R.PLANE_VIAS['VCC3V3'] = {'Bottom Layer': ('uvia_bot', 'stack_bot', 'through'), 'Top Layer': ('stack_tie', 'through'),
                          'L4-SIG': ('uvia_45', 'stack_bot'), 'L3-SIG': ('col_vcc3', 'through')}

STATE = {'strict': True, 'masks': None}


def build_masks(M):
    """{(layer, radius): bool raster} of via centres whose land of that radius overlaps an SMD pad on the layer"""
    W = int(math.ceil(M['board']['w'] / R.G)) + 1
    H = int(math.ceil(M['board']['h'] / R.G)) + 1
    out = {}
    for layer in ('Top Layer', 'Bottom Layer'):
        for r in (0.135, 0.15, 0.175):
            a = np.zeros((H, W), bool)
            for p in M['pads']:
                if p['drill'] or layer not in (p['layers'] or []):
                    continue
                ext = max(p['w'], p['h']) / 2 + r + R.G
                j0, j1 = max(0, int((p['x'] - ext) / R.G)), min(W, int((p['x'] + ext) / R.G) + 2)
                i0, i1 = max(0, int((p['y'] - ext) / R.G)), min(H, int((p['y'] + ext) / R.G) + 2)
                yy, xx = np.mgrid[i0:i1, j0:j1]
                X, Y = xx * R.G, yy * R.G
                if C.pad_round(p):
                    d = np.hypot(X - p['x'], Y - p['y']) - min(p['w'], p['h']) / 2
                else:
                    d = np.hypot(np.maximum(abs(X - p['x']) - p['w'] / 2, 0), np.maximum(abs(Y - p['y']) - p['h'] / 2, 0))
                a[i0:i1, j0:j1] |= d < r + 1e-6
            out[(layer, r)] = a
    return out


_via_ok = R.Router.via_ok


def via_ok(self, net, kind, x, y, D, win, base=False):
    if not _via_ok(self, net, kind, x, y, D, win, base):
        return False
    objs, occ, _ = R.VIAS[kind]
    i, j = int(round(y / R.G)), int(round(x / R.G))
    for fr, to, size, hole in objs:
        through = fr == 'Top Layer' and to == 'Bottom Layer'
        if not (through or STATE['strict']):
            continue
        for layer in ('Top Layer', 'Bottom Layer'):
            if layer in (fr, to):
                m = STATE['masks'][(layer, min((0.135, 0.15, 0.175), key=lambda r: abs(r - size / 2)))]
                if m[i, j]:
                    return False
    return True


R.Router.via_ok = via_ok
_route = R.Router.route


_window = R.window


def window(B, boxes, margin):
    STATE['margin'] = margin
    return _window(B, boxes, margin)


R.window = window


def route(self, net, src, dst, win, plane=None, base=False):
    if STATE['masks'] is None:
        STATE['masks'] = build_masks(self.B.M)
    STATE['strict'] = True
    r = _route(self, net, src, dst, win, plane, base)
    # lenient (microvia in a same-net pad) only once the caller's window has grown: a strict route may still exist
    # in a larger window (plane ties try 0.8 / 1.6 / 3.0 mm, signal routes margin / 2.5 x margin / 60 mm)
    if r is None and STATE.get('margin', 99) >= (2.9 if plane else 6.0):
        STATE['strict'] = False
        r = _route(self, net, src, dst, win, plane, base)
        STATE['strict'] = True
    return r


R.Router.route = route

if __name__ == '__main__':
    sys.argv[0] = os.path.join(T, 'router.py')
    R.main()
