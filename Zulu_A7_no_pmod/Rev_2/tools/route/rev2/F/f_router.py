"""f_router.py [--inpad-micro] <router.py args...> -- router.py with two Rev 2 board rules patched in:

  1. no via whose land overlaps an SMD pad on an outer layer of its span (the user's rule for through vias, applied
     to every via kind: a microvia in a pad needs --inpad-micro, which then allows microvias -- never through
     vias -- in a pad of their own net);
  2. a Bottom pad reaches the GND pour through a microvia column (Bottom>L5>L4>L3>L2: 'stack_tieg') instead of
     only a through via.
Everything else is router.py unchanged (it is imported, patched and its main() run).
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, TOOLS)
import router as R  # noqa: E402
import route_conn as C  # noqa: E402

INPAD_MICRO = '--inpad-micro' in sys.argv
if INPAD_MICRO:
    sys.argv.remove('--inpad-micro')

S = R.STACK
R.VIAS['stack_tieg'] = ([('L2-GND', 'L3-SIG', 0.30, 0.15), ('L3-SIG', 'L4-SIG', 0.27, 0.15),
                         ('L4-SIG', 'L5-VCC3V3', 0.30, 0.15), ('L5-VCC3V3', 'Bottom Layer', 0.30, 0.15)],
                        S[1:6], ('Bottom Layer',))
R.VIA_COST['stack_tieg'] = 1.5
R.PLANE_VIAS['GND']['Bottom Layer'] = ('stack_tieg', 'through')

_masks = {}


def pad_mask(B, layer, r, net):
    """grid points where a via land of radius r on `layer` would touch an SMD pad (of any net, or -- in-pad
    micro mode -- of another net than `net`)"""
    key = (layer, r, net if INPAD_MICRO else None)
    if key in _masks:
        return _masks[key]
    m = np.zeros((B.H, B.W), bool)
    for p in B.M['pads']:
        if p['drill'] or layer not in (p['layers'] or []):
            continue
        if INPAD_MICRO and p['net'] == net:
            continue
        rr = max(p['w'], p['h']) / 2 + r + 0.05
        i0, i1 = max(0, int((p['y'] - rr) / R.G)), min(B.H - 1, int((p['y'] + rr) / R.G) + 1)
        j0, j1 = max(0, int((p['x'] - rr) / R.G)), min(B.W - 1, int((p['x'] + rr) / R.G) + 1)
        yy, xx = np.mgrid[i0:i1 + 1, j0:j1 + 1]
        X, Y = xx * R.G, yy * R.G
        if C.pad_round(p):
            d = np.maximum(0, np.hypot(X - p['x'], Y - p['y']) - min(p['w'], p['h']) / 2)
        else:
            d = np.hypot(np.maximum(abs(X - p['x']) - p['w'] / 2, 0), np.maximum(abs(Y - p['y']) - p['h'] / 2, 0))
        m[i0:i1 + 1, j0:j1 + 1] |= d < r + 0.002
    _masks[key] = m
    return m


_orig_via_ok = R.Router.via_ok


def via_ok(self, net, kind, x, y, D, win, base=False):
    objs, occ, _ = R.VIAS[kind]
    i, j = int(round(y / R.G)), int(round(x / R.G))
    through = kind == 'through'
    for layer in ('Top Layer', 'Bottom Layer'):
        if layer not in occ:
            continue
        r = max(o[2] for o in objs if layer in S[S.index(o[0]):S.index(o[1]) + 1]) / 2
        if INPAD_MICRO and not through:
            m = pad_mask(self.B, layer, r, net)
        else:
            m = pad_mask(self.B, layer, r, None)
        if 0 <= i < m.shape[0] and 0 <= j < m.shape[1] and m[i, j]:
            return False
    return _orig_via_ok(self, net, kind, x, y, D, win, base)


R.Router.via_ok = via_ok

if __name__ == '__main__':
    print('f_router: no via in SMD pads%s; GND Bottom ties by microvia column' % (
        ' (microvias in own-net pads allowed)' if INPAD_MICRO else ''), flush=True)
    R.main()
