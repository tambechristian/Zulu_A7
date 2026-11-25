"""usb_hand.py <out_plan.json> [bumps]
Hand-built Rev 2 USB pair (Top, 0.15/0.15, no vias) from X1 (moved 2.54 west) to U2, reusing the Rev 1 U2-end
geometry, plus the CHAN10 Top re-route that clears the pair's corridor (its Top->L3 drop moves from 27.9,22.45 to
31.5,22.4 onto its own existing L3 run). Writes a plan {tracks, vias, remove, remove_vias} against prep/model.json."""
import json
import math
import sys

W = 0.15
# Rev 1 U2 end (kept exactly)
P_u2 = [(25.775, 13.85), (25.775, 14.02), (27.3946, 14.02), (27.7825, 14.4079), (27.7825, 17.2621), (26.8, 18.2446)]
N_u2 = [(25.775, 14.3501), (25.775, 14.32), (27.2704, 14.32), (27.4825, 14.5321), (27.4825, 17.1379), (26.5, 18.1204)]
Y1 = 19.55            # first jog (centre 26.65 -> 26.80, clears C155 / GND via 26.3,20.675)
Y2 = 21.35            # second jog (centre 26.80 -> 26.70, clears the GND via 27.215,21.9)
t225 = math.tan(math.radians(22.5)) * 0.3
HE, C, YA, YB = 0.456, 0.1, 19.75, 20.40   # length-tuning bump east of P (room up to U2 pad 64 at x 27.585)
P_mid = [(26.8, Y1), (26.95, Y1 + 0.15), (26.95, YA), (26.95 + C, YA + C), (26.95 + HE - C, YA + C), (26.95 + HE, YA + 2 * C),
         (26.95 + HE, YB - 2 * C), (26.95 + HE - C, YB - C), (26.95 + C, YB - C), (26.95, YB), (26.95, Y2), (26.85, Y2 + 0.1), (26.85, 22.0379), (27.1121, 22.30)]
N_mid = [(26.5, Y1 + t225), (26.65, Y1 + t225 + 0.15), (26.65, Y2 - t225), (26.55, Y2 - t225 + 0.1), (26.55, 22.1621),
         (26.9879, 22.60)]
P_pad = [(30.18, 22.30), (30.48, 22.00), (30.48, 21.2585)]
N_pad = [(30.88, 22.60), (31.13, 22.35), (31.13, 21.2585)]


def bumps(xs, y, h):
    """trapezoid bumps north (towards smaller y) of height h on a horizontal run at y, 45 deg sides"""
    out = []
    for x in xs:
        out += [(x, y), (x + h, y - h), (x + h + 0.1, y - h), (x + 2 * h + 0.1, y)]
    return out


def poly(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def build(bump_xs=(), h=0.2):
    P = P_u2 + P_mid + bumps(bump_xs, 22.30, h) + P_pad
    N = N_u2 + N_mid + N_pad
    return P, N


def tracks(pts, net, layer='Top Layer', w=W):
    return [{'net': net, 'layer': layer, 'w': w, 'x1': a[0], 'y1': a[1], 'x2': b[0], 'y2': b[1]}
            for a, b in zip(pts, pts[1:]) if math.hypot(b[0] - a[0], b[1] - a[1]) > 1e-6]


if __name__ == '__main__':
    bx = [float(v) for v in sys.argv[2].split(',')] if len(sys.argv) > 2 and sys.argv[2] else []
    h = float(sys.argv[3]) if len(sys.argv) > 3 else 0.2
    P, N = build(bx, h)
    print('P %.4f  N %.4f  diff %.4f' % (poly(P), poly(N), poly(N) - poly(P)))
    w10 = 0.0762
    ch10 = [(21.7, 22.45), (22.1, 22.85), (31.35, 22.85), (31.5, 22.70), (31.5, 22.4)]
    plan = {'tracks': tracks(P, 'USB_D_P') + tracks(N, 'USB_D_N') + tracks(ch10, 'CHAN10', w=w10) +
            [{'net': 'CHAN10', 'layer': 'L3-SIG', 'w': w10, 'x1': 31.5, 'y1': 22.4, 'x2': 40.1, 'y2': 22.4}],
            'vias': [{'net': 'CHAN10', 'x': 31.5, 'y': 22.4, 'size': 0.3, 'hole': 0.15, 'from': 'Top Layer', 'to': 'L2-GND'},
                     {'net': 'CHAN10', 'x': 31.5, 'y': 22.4, 'size': 0.3, 'hole': 0.15, 'from': 'L2-GND', 'to': 'L3-SIG'}],
            'remove': [{'net': 'CHAN10', 'layer': 'Top Layer', 'w': w10, 'x1': 21.7, 'y1': 22.45, 'x2': 27.9, 'y2': 22.45},
                       {'net': 'CHAN10', 'layer': 'L3-SIG', 'w': w10, 'x1': 29.0, 'y1': 22.4, 'x2': 40.1, 'y2': 22.4},
                       {'net': 'CHAN10', 'layer': 'L4-SIG', 'w': w10, 'x1': 27.95, 'y1': 22.4, 'x2': 29.0, 'y2': 22.4},
                       {'net': 'CHAN10', 'layer': 'L4-SIG', 'w': w10, 'x1': 27.9, 'y1': 22.45, 'x2': 27.95, 'y2': 22.4}],
            'remove_vias': [{'net': 'CHAN10', 'x': 27.9, 'y': 22.45, 'size': 0.3, 'hole': 0.15, 'from': 'Top Layer', 'to': 'L2-GND'},
                            {'net': 'CHAN10', 'x': 27.9, 'y': 22.45, 'size': 0.3, 'hole': 0.15, 'from': 'L2-GND', 'to': 'L3-SIG'},
                            {'net': 'CHAN10', 'x': 27.9, 'y': 22.45, 'size': 0.27, 'hole': 0.15, 'from': 'L3-SIG', 'to': 'L4-SIG'},
                            {'net': 'CHAN10', 'x': 29.0, 'y': 22.4, 'size': 0.27, 'hole': 0.15, 'from': 'L3-SIG', 'to': 'L4-SIG'}]}
    json.dump(plan, open(sys.argv[1], 'w'), indent=1)
