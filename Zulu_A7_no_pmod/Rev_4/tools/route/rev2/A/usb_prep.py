"""Strategy A pre-route: a hand-designed coupled USB pair (Top, 0.15 / 0.15 gap, no vias) for the moved X1, and
CHAN10's Top detour (which now sits in the only pair corridor south of MH1) moved down to L3.

    python usb_prep.py   (paths are fixed: reads ../prep, writes here)

Writes rip_A.json (prep rip + CHAN10 detour), model_A.json (prep model minus the CHAN10 detour plus the USB pair and
the new CHAN10 L3 piece, all as fixed board copper) and pre.json (the USB + CHAN10 copper as a plan)."""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PREP = os.path.join(HERE, '..', 'prep')
W = 0.15


def path(net, pts, layer='Top Layer', w=W):
    return [{'net': net, 'layer': layer, 'w': w, 'x1': a[0], 'y1': a[1], 'x2': b[0], 'y2': b[1]}
            for a, b in zip(pts, pts[1:])]


# P (east / north line) and N (west / south line); north end is rev 1's (unchanged U2 and its surroundings)
xp1, xp2, xp3 = 26.80, 26.96, 26.86       # P vertical positions: under U2-64 / past C155's via / past the GND via
d = 0.30
a = 0.15
b = a + 2 * d - d * math.sqrt(2)          # outer chamfer so the 45 deg corner keeps the 0.30 pitch
XE = 30.75                                # the pair rises to X1 coupled: P between pads 3 and 2, N inside pad 2
BX, BH, BW = float(os.environ.get('BX', 29.26)), float(os.environ.get('BH', 0.2018)), float(os.environ.get('BW', 0.1))
BUMP = [(BX, 22.35), (BX + BH, 22.35 - BH), (BX + BH + BW, 22.35 - BH), (BX + 2 * BH + BW, 22.35)] if BH else []
P = [(25.775, 13.85), (25.775, 14.02), (27.3946, 14.02), (27.7825, 14.4079), (27.7825, 17.2621), (xp1, 18.2446),
     (xp1, 19.60), (xp2, 19.95), (xp2, 21.00), (xp3, 21.50), (xp3, 22.35 - a), (xp3 + a, 22.35)] + BUMP + [
     (XE - a, 22.35), (XE, 22.35 - a), (XE, 21.2585), (30.48, 21.2585)]
N = [(25.775, 14.3501), (25.775, 14.32), (27.2704, 14.32), (27.4825, 14.5321), (27.4825, 17.1379),
     (xp1 - d, 18.1204), (xp1 - d, 19.60), (xp2 - d, 19.95), (xp2 - d, 21.00), (xp3 - d, 21.50),
     (xp3 - d, 22.65 - b), (xp3 - d + b, 22.65), (XE + d - b, 22.65), (XE + d, 22.65 - b), (XE + d, 21.2585),
     (31.13, 21.2585)]
usb = path('USB_D_P', P) + path('USB_D_N', N)

# CHAN10: drop the Top detour (21.25,22.9) -> Top y 22.45 -> (27.9,22.45) -> L4 -> buried (29.0,22.4);
# reconnect on L3 from the L3 end at (21.25,22.9) to the buried via at (29.0,22.4)
ch_rm_t = [
    {'net': 'CHAN10', 'layer': 'Top Layer', 'w': 0.0762, 'x1': 21.7, 'y1': 22.45, 'x2': 27.9, 'y2': 22.45},
    {'net': 'CHAN10', 'layer': 'Top Layer', 'w': 0.0762, 'x1': 21.25, 'y1': 22.9, 'x2': 21.7, 'y2': 22.45},
    {'net': 'CHAN10', 'layer': 'L4-SIG', 'w': 0.0762, 'x1': 27.95, 'y1': 22.4, 'x2': 29.0, 'y2': 22.4},
    {'net': 'CHAN10', 'layer': 'L4-SIG', 'w': 0.0762, 'x1': 27.9, 'y1': 22.45, 'x2': 27.95, 'y2': 22.4},
]
ch_rm_v = [
    {'net': 'CHAN10', 'x': 27.9, 'y': 22.45, 'size': 0.27, 'hole': 0.15, 'span': ['L3-SIG', 'L4-SIG']},
    {'net': 'CHAN10', 'x': 27.9, 'y': 22.45, 'size': 0.3, 'hole': 0.15, 'span': ['L2-GND', 'L3-SIG']},
    {'net': 'CHAN10', 'x': 27.9, 'y': 22.45, 'size': 0.3, 'hole': 0.15, 'span': ['Top Layer', 'L2-GND']},
    {'net': 'CHAN10', 'x': 21.25, 'y': 22.9, 'size': 0.3, 'hole': 0.15, 'span': ['L2-GND', 'L3-SIG']},
    {'net': 'CHAN10', 'x': 21.25, 'y': 22.9, 'size': 0.3, 'hole': 0.15, 'span': ['Top Layer', 'L2-GND']},
]
ch_new = []                              # CHAN10 is re-routed by the router (a straight L3 run collides)


def tk(t):
    return (t['net'], t['layer'], frozenset({(round(t['x1'], 3), round(t['y1'], 3)), (round(t['x2'], 3), round(t['y2'], 3))}))


def vk(v):
    return (v['net'], round(v['x'], 3), round(v['y'], 3), round(v['hole'], 3), tuple(v['span']))


if __name__ == '__main__':
    rip = json.load(open(os.path.join(PREP, 'rip.json')))
    rip['remove'] += ch_rm_t
    rip['remove_vias'] += ch_rm_v
    json.dump(rip, open(os.path.join(HERE, 'rip_A.json'), 'w'), indent=0)
    M = json.load(open(os.path.join(PREP, 'model.json')))
    rt, rv = {tk(t) for t in ch_rm_t}, {vk(v) for v in ch_rm_v}
    n0 = len(M['tracks']), len(M['vias'])
    M['tracks'] = [t for t in M['tracks'] if tk(t) not in rt] + usb + ch_new
    M['vias'] = [v for v in M['vias'] if vk(v) not in rv]
    print('model tracks %d -> %d, vias %d -> %d' % (n0[0], len(M['tracks']), n0[1], len(M['vias'])))
    json.dump(M, open(os.path.join(HERE, 'model_A.json'), 'w'))
    pre = {'tracks': usb + ch_new, 'vias': [], 'remove': ch_rm_t,
           'remove_vias': [dict(v, **{'from': v['span'][0], 'to': v['span'][-1]}) for v in ch_rm_v]}
    json.dump(pre, open(os.path.join(HERE, 'pre.json'), 'w'), indent=0)
    L = lambda ts: sum(math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) for t in ts)  # noqa: E731
    print('USB_D_P %.4f  USB_D_N %.4f' % (L(path('USB_D_P', P)), L(path('USB_D_N', N))))
