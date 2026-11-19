"""router_e.py: tools/router.py with strategy E's via policy (all router.py arguments pass through).

  * no via land of the router's may overlap an SMD pad (any net) on Top or Bottom: a through via never, a microvia
    only with --inpad (then only where clearance already allows it, i.e. a same-net pad)
  * extra plane-tie columns so a plane net never needs a through via to reach its pour:
      gtie_bot  Bottom>L5>L4>L3>L2 (GND from Bottom)     uvia_l3  L3>L2 (GND from L3)    gtie_l4  L4>L3>L2 (GND from L4)
      uvia_l4   L4>L5 (VCC3V3 from L4)                   vtie_l3  L3>L4>L5 (VCC3V3 from L3)
"""
import os
import sys

import numpy as np

TOOLS = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, TOOLS)
import route_conn as C  # noqa: E402
import router as R  # noqa: E402

S = R.STACK
INPAD = '--inpad' in sys.argv
if INPAD:
    sys.argv.remove('--inpad')

R.VIAS['gtie_bot'] = ([('L5-VCC3V3', 'Bottom Layer', 0.30, 0.15), ('L4-SIG', 'L5-VCC3V3', 0.30, 0.15),
                       ('L3-SIG', 'L4-SIG', 0.27, 0.15), ('L2-GND', 'L3-SIG', 0.30, 0.15)], S[1:6], ('Bottom Layer',))
R.VIAS['uvia_l3'] = ([('L2-GND', 'L3-SIG', 0.30, 0.15)], S[1:3], ('L3-SIG',))
R.VIAS['gtie_l4'] = ([('L3-SIG', 'L4-SIG', 0.27, 0.15), ('L2-GND', 'L3-SIG', 0.30, 0.15)], S[1:4], ('L4-SIG',))
R.VIAS['uvia_l4'] = ([('L4-SIG', 'L5-VCC3V3', 0.30, 0.15)], S[3:5], ('L4-SIG',))
R.VIAS['vtie_l3'] = ([('L3-SIG', 'L4-SIG', 0.27, 0.15), ('L4-SIG', 'L5-VCC3V3', 0.30, 0.15)], S[2:5], ('L3-SIG',))
R.VIA_COST.update({'gtie_bot': 1.5, 'uvia_l3': 0.5, 'gtie_l4': 0.8, 'uvia_l4': 0.5, 'vtie_l3': 0.8})
R.PLANE_VIAS['GND'] = {'Top Layer': ('uvia_top', 'stack_top', 'through'), 'Bottom Layer': ('through', 'gtie_bot'),
                       'L3-SIG': ('uvia_l3', 'stack_top'), 'L4-SIG': ('gtie_l4', 'through')}
R.PLANE_VIAS['VCC3V3'] = {'Bottom Layer': ('uvia_bot', 'stack_bot', 'through'), 'Top Layer': ('stack_tie', 'through'),
                          'L4-SIG': ('uvia_l4', 'stack_bot'), 'L3-SIG': ('vtie_l3', 'through')}
# the single-level plane ties join no pair of routing layers, so they never appear as a layer change
for k in ('gtie_bot', 'uvia_l3', 'gtie_l4', 'uvia_l4', 'vtie_l3'):
    objs, occ, joins = R.VIAS[k]
    assert len(joins) == 1

_init = R.Board.__init__


def _board_init(self, M):
    _init(self, M)
    G = R.G
    self.padban = {}
    for l in ('Top Layer', 'Bottom Layer'):
        for r in (0.175, 0.15):
            a = np.zeros((self.H, self.W), bool)
            for p in M['pads']:
                if p['drill'] or l not in (p['layers'] or []):
                    continue
                ext = max(p['w'], p['h']) / 2 + r + G
                i0, i1 = max(0, int((p['y'] - ext) / G)), min(self.H - 1, int((p['y'] + ext) / G) + 1)
                j0, j1 = max(0, int((p['x'] - ext) / G)), min(self.W - 1, int((p['x'] + ext) / G) + 1)
                yy, xx = np.mgrid[i0:i1 + 1, j0:j1 + 1]
                X, Y = xx * G, yy * G
                if C.pad_round(p):
                    d = np.hypot(X - p['x'], Y - p['y']) - min(p['w'], p['h']) / 2
                else:
                    d = np.hypot(np.maximum(abs(X - p['x']) - p['w'] / 2, 0), np.maximum(abs(Y - p['y']) - p['h'] / 2, 0))
                a[i0:i1 + 1, j0:j1 + 1] |= d < r + 0.002
            self.padban[(l, r)] = a


R.Board.__init__ = _board_init
_orig_via_ok = R.Router.via_ok


def _via_ok(self, net, kind, x, y, D, win, base=False):
    objs, occ, _ = R.VIAS[kind]
    i, j = int(round(y / R.G)), int(round(x / R.G))
    for l in ('Top Layer', 'Bottom Layer'):
        if l not in occ:
            continue
        if kind == 'through':
            r = 0.175
        elif INPAD:
            continue
        else:
            r = 0.15
        if self.B.padban[(l, r)][i, j]:
            return False
    return _orig_via_ok(self, net, kind, x, y, D, win, base)


R.Router.via_ok = _via_ok

if __name__ == '__main__':
    print('router_e: via-in-SMD-pad ban (%s), plane-tie columns on' % ('through only' if INPAD else 'all vias'), flush=True)
    R.main()
