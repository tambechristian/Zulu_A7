"""Strategy C hand fix: USB_D_P/N coupled pair on Top (no vias) around X1's moved MH1; CHAN10's Top detour and the
U10-5 GND via moved out of the pair's path.   python usb_fix.py <model.json> <out_fix.json> [jogP]"""
import json, math, sys
M = json.load(open(sys.argv[1]))
W = 0.15
def path(net, pts, layer='Top Layer', w=W):
    return [{'net': net, 'layer': layer, 'w': w, 'x1': a[0], 'y1': a[1], 'x2': b[0], 'y2': b[1]} for a, b in zip(pts, pts[1:]) if a != b]
c = 0.5; cN = c + 0.30 * (math.sqrt(2) - 1) * math.sqrt(2)
P = [(25.775, 13.85), (25.775, 14.02), (27.3946, 14.02), (27.7825, 14.4079), (27.7825, 17.2621), (26.8, 18.2446),
     (26.8, 19.62), (26.98, 19.80), (26.98, 22.35 - c), (26.98 + c, 22.35)]
yN1 = 26.5 - (26.8 - 19.62 - 0.30 * math.sqrt(2))
N = [(25.775, 14.3501), (25.775, 14.32), (27.2704, 14.32), (27.4825, 14.5321), (27.4825, 17.1379), (26.5, 18.1204),
     (26.5, yN1), (26.68, yN1 + 0.18), (26.68, 22.65 - cN), (26.68 + cN, 22.65)]
# east end (Rev 1 shape shifted 2.54 west)
Pe = [(30.5879, 22.35), (30.75, 22.1879), (30.75, 21.2585), (30.48, 21.2585)]
Ne = [(30.7121, 22.65), (31.05, 22.3121), (31.05, 21.2585), (31.13, 21.2585)]
jog = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
L = lambda pts: sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
def build(jog):
    p = P[:]
    if jog > 0:   # a 45-degree bump north on P's straight run at x 28.6 .. (bump height h adds 2h(sqrt2-1))
        h = jog / (2 * (math.sqrt(2) - 1)); x0 = 28.4
        p += [(x0, 22.35), (x0 + h, 22.35 - h), (x0 + h + 0.2, 22.35 - h), (x0 + 2 * h + 0.2, 22.35)]
    return p + Pe, N + Ne
p, n = build(0)
d = L(n) - L(p)
p, n = build(max(d, 0) if jog == 0 else jog)
print('P %.4f N %.4f mismatch %.4f (pre-jog diff %.4f)' % (L(p), L(n), L(n) - L(p), d))
T = path('USB_D_P', p) + path('USB_D_N', n)
# CHAN10: drop the Top detour + the 27.9 stack + the L4 hop, run it on L3 instead
rm, rmv = [], []
for t in M['tracks']:
    if t['net'] == 'CHAN10' and ((t['layer'] == 'Top Layer' and t['x1'] < 30) or (t['layer'] == 'L4-SIG' and t['x2'] <= 29.0 + 1e-6)):
        rm.append(t)
for v in M['vias']:
    if v['net'] == 'CHAN10' and ((abs(v['x'] - 27.9) < 1e-6 and abs(v['y'] - 22.45) < 1e-6) or (abs(v['x'] - 29.0) < 1e-6 and abs(v['y'] - 22.4) < 1e-6)
                                 or (abs(v['x'] - 21.25) < 1e-6 and abs(v['y'] - 22.9) < 1e-6 and v['span'][0] == 'Top Layer')):
        rmv.append(v)
T += path('CHAN10', [(21.25, 22.9), (21.75, 22.4), (29.0, 22.4)], 'L3-SIG', 0.0762)
V = []
# U10-5 GND: via 27.215,21.9 -> GVX,GVY
GV = (25.95, 22.0)
for t in M['tracks']:
    if t['net'] == 'GND' and t['layer'] == 'Bottom Layer' and abs(t['x1'] - 27.215) < 1e-6 and abs(t['y1'] - 21.9) < 1e-6: rm.append(t)
for v in M['vias']:
    if v['net'] == 'GND' and abs(v['x'] - 27.215) < 1e-6 and abs(v['y'] - 21.9) < 1e-6: rmv.append(v)
V.append({'net': 'GND', 'x': GV[0], 'y': GV[1], 'size': 0.35, 'hole': 0.2, 'span': ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']})
T += path('GND', [GV, (26.45, 22.505), (27.215, 22.505)], 'Bottom Layer', 0.4)
json.dump({'tracks': T, 'vias': V, 'remove': rm, 'remove_vias': rmv}, open(sys.argv[2], 'w'), indent=1)
print('fix: %d tracks %d vias, remove %d tracks %d vias' % (len(T), len(V), len(rm), len(rmv)))
