"""X1 micro-B conversion, stage B: fixes from the 2026-11-17 review (wf_3b983b44-cc8), against model_final.json.

  C1 + C5  D+/D- re-routed as a coupled 0.15/0.15 pair: straight 0.2 mm exit from each X1 pad (no 45-degree acid
           trap), 0.30 mm centre pitch down x 5.35/5.65 and along y 7.75/8.05, split to U2-8/U2-7 in the last
           0.83 mm. Uncoupled about 1.6 / 2.0 mm (DiffPairsRouting MaxUncoupledLength 3.0 mm; was 5.3 mm).
  C2       leftover USB-CC2 copper that the ECO renamed to GND, now pad-less: Top>L2>L3 laser stacks at
           (7.975, 3.375) and (8.0, 9.55), the L3 track between them and the Top stub (4 lasers, 3 tracks).
  C3       FLASH-D02 through via moved (17.45, 16.625) -> (17.35, 16.55) so its hole clears R2-1's mask opening.
Writes plan2.json (remove / remove_vias / tracks / vias) and model2.json (model_final with plan2 applied).
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
M = json.load(open(os.path.join(HERE, 'model_final.json')))
TOP, L3, L4 = 'Top Layer', 'L3-SIG', 'L4-SIG'
S = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']


def k(x, y):
    return (round(x, 3), round(y, 3))


def find_t(net, layer, x1, y1, x2, y2):
    c = [t for t in M['tracks'] if t['net'] == net and t['layer'] == layer and
         {k(t['x1'], t['y1']), k(t['x2'], t['y2'])} == {k(x1, y1), k(x2, y2)}]
    assert len(c) == 1, (net, layer, x1, y1, x2, y2, len(c))
    return c


def find_v(net, x, y, n):
    c = [v for v in M['vias'] if v['net'] == net and abs(v['x'] - x) < 0.002 and abs(v['y'] - y) < 0.002]
    assert len(c) == n, (net, x, y, len(c))
    return c


rm, rmv = [], []
usb = [t for t in M['tracks'] if t['net'] in ('USB_D_P', 'USB_D_N')]
assert len(usb) == 8 and not [v for v in M['vias'] if v['net'] in ('USB_D_P', 'USB_D_N')]
rm += usb
rm += find_t('GND', TOP, 8.0, 9.55, 8.0, 9.575)
rm += find_t('GND', L3, 7.975, 3.375, 8.0, 3.425)
rm += find_t('GND', L3, 8.0, 3.425, 8.0, 9.55)
rmv += find_v('GND', 7.975, 3.375, 2) + find_v('GND', 8.0, 9.55, 2)
rm += find_t('FLASH-D02', TOP, 17.45, 16.625, 17.575, 16.775)
rm += find_t('FLASH-D02', L4, 17.45, 16.625, 17.875, 15.8)
rmv += find_v('FLASH-D02', 17.45, 16.625, 1)


def W(net, layer, w, *pts):
    return [dict(net=net, layer=layer, w=w, x1=a[0], y1=a[1], x2=b[0], y2=b[1]) for a, b in zip(pts, pts[1:])]


add_t = []
add_t += W('USB_D_P', TOP, 0.15, (4.80, 11.43), (5.00, 11.43), (5.35, 11.08), (5.35, 8.226), (5.826, 7.75),
           (8.45, 7.75), (8.55, 7.65), (9.275, 7.65))
add_t += W('USB_D_N', TOP, 0.15, (4.80, 12.08), (5.00, 12.08), (5.65, 11.43), (5.65, 8.35), (5.95, 8.05),
           (8.45, 8.05), (8.55, 8.15), (9.275, 8.15))
add_t += W('FLASH-D02', L4, 0.0762, (17.875, 15.8), (17.35, 16.55))
add_t += W('FLASH-D02', TOP, 0.0762, (17.35, 16.55), (17.575, 16.775))
add_v = [dict(net='FLASH-D02', x=17.35, y=16.55, size=0.35, hole=0.20, **{'from': TOP, 'to': 'Bottom Layer'})]

plan = dict(remove=rm, remove_vias=rmv, tracks=add_t, vias=add_v)
json.dump(plan, open(os.path.join(HERE, 'plan2.json'), 'w'), indent=0)
ids_t = {id(t) for t in rm}
ids_v = {id(v) for v in rmv}
R = dict(M)
R['tracks'] = [t for t in M['tracks'] if id(t) not in ids_t] + add_t
R['vias'] = [v for v in M['vias'] if id(v) not in ids_v] + [
    dict({kk: v[kk] for kk in v if kk not in ('from', 'to')}, span=S[S.index(v['from']):S.index(v['to']) + 1]) for v in add_v]
json.dump(R, open(os.path.join(HERE, 'model2.json'), 'w'))
L = {}
for t in add_t:
    if t['net'].startswith('USB'):
        L[t['net']] = L.get(t['net'], 0) + ((t['x2'] - t['x1']) ** 2 + (t['y2'] - t['y1']) ** 2) ** 0.5
print('remove %d tracks, %d vias; add %d tracks, %d vias; USB lengths %s' % (
    len(rm), len(rmv), len(add_t), len(add_v), {n: round(v, 3) for n, v in L.items()}))
