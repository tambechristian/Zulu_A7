"""X1 micro-B conversion, stage A: hand removals + hand additions on the router model (docs/x1_microb.md).

model0.json is the board after AsarX1Place (X1 = Amphenol 10118193-0001LF on the west edge, Q1 moved 1.46 mm east),
before any copper edit. Writes hand_plan.json (remove / remove_vias / tracks / vias) and route_in.json (model0 with
the hand plan applied: the router's input).

Removed
  X1 area  the VU Top hop under the new X1 (track + both through vias: V42 sat on pin 5, V43 on MP2); the dead VU
           Bottom stub that ran from C149-2 through MH1's slot to (2.889, 21.963); every USB_D_P / USB_D_N track and
           via (the old routes to the USB-C); the dangling USB5V0 Top>L4 stack at (8.29, 8.98) with its L4 stub; the
           orphan GND laser at (7.6, 7.95) that tied the USB-C shell.
  Q1 area  the VU Top detour T42..T80 that the moved Q1 now sits on; FLASH-D02's Top track and Top>L3 stack at
           (17.85, 15.8) (inside Q1-4); GND through vias (16.75, 14.925) / (17.875, 14.925) with their Bottom stubs
           (inside Q1-4); CLK-12M-SHARED's Top>L3 stack at (15.375, 12.65) (inside Q1-2) and Top track T1021 (0.077 mm
           from Q1-2); FT-PWREN# T673 (crosses Q1-3).
Added
  VU       the hop drops to L4 (Bottom is blocked by C78-1 and L3-2, 0.3 mm apart): blind L4>L5>Bottom stacks at
           the old via spots (3.475, 10.2) and (3.075, 8.85) joined by a 0.2 mm L4 track (it only feeds R26's pull-up);
           the feed to V37 goes straight down from V33: (14.475, 17.5) -> (14.475, 14.55) -> (15.55, 14.225), 0.4 mm
  USB      D+ (4.80, 11.43) > (5.25, 10.98) > (5.25, 8.43) > (6.03, 7.65) > U2-8 (9.275, 7.65), 0.15 mm Top;
           D- (4.80, 12.08) > (5.55, 11.33) > (5.55, 8.73) > (6.13, 8.15) > U2-7 (9.275, 8.15), 0.15 mm Top
           (0.15 mm gap along the 2.5 mm vertical run, the board's DiffPairsRouting width/gap)
  USB5V0   X1-1 (4.80, 12.73) > (6.75, 12.73) > the USB5V0 Top>L4 stack at (7.90, 13.88), 0.35 mm Top
  GND      shell ties on Top: MP2 -> MH2, MP1 -> MH1 (0.4 mm), pin 5 -> MP4 (0.3 mm)
  VCC3V3   Q1-4 -> Q1-1 on Top (0.3 mm; Q1-1 already sits on the VCC3V3 stack at (15.375, 14.85))
The router then closes what is left open (FLASH-D02, CLK-12M-SHARED, FT-PWREN#, GND ties for Q1-2 / C93-2 / C144-2).
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
M0 = json.load(open(os.path.join(HERE, 'model0.json')))
TOP, L3, L4, BOT = 'Top Layer', 'L3-SIG', 'L4-SIG', 'Bottom Layer'
S = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']


def k(x, y):
    return (round(x, 3), round(y, 3))


def find_t(net, layer, x1, y1, x2, y2):
    c = [t for t in M0['tracks'] if t['net'] == net and t['layer'] == layer and
         {k(t['x1'], t['y1']), k(t['x2'], t['y2'])} == {k(x1, y1), k(x2, y2)}]
    assert len(c) >= 1, (net, layer, x1, y1, x2, y2)
    return c


def find_v(net, x, y, n=None):
    c = [v for v in M0['vias'] if v['net'] == net and abs(v['x'] - x) < 0.002 and abs(v['y'] - y) < 0.002]
    assert c and (n is None or len(c) == n), (net, x, y, len(c))
    return c


rm, rmv = [], []
# --- X1 area
rm += find_t('VU', TOP, 3.075, 8.85, 3.475, 10.2)
rmv += find_v('VU', 3.475, 10.2, 1) + find_v('VU', 3.075, 8.85, 1)
# dead VU Bottom stub: walk from the dangling end (2.889, 21.963) to C149-2
stub = [t for t in M0['tracks'] if t['net'] == 'VU' and t['layer'] == BOT and
        (t['y1'] > 13.8 or t['y2'] > 13.8) and max(t["x1"], t["x2"]) <= 2.951 and min(t['x1'], t['x2']) > 0.8]
assert len(stub) == 23, len(stub)
ends = {}
for t in stub:
    for p in (k(t['x1'], t['y1']), k(t['x2'], t['y2'])):
        ends[p] = ends.get(p, 0) + 1
free = sorted(p for p, n in ends.items() if n == 1)
assert free == [(2.889, 21.963), (2.95, 13.825)], free     # one dangling end, one end inside C149-2
rm += stub
for net in ('USB_D_P', 'USB_D_N'):
    rm += [t for t in M0['tracks'] if t['net'] == net]
    rmv += [v for v in M0['vias'] if v['net'] == net]
rmv += find_v('USB5V0', 8.29, 8.98, 3)
rm += find_t('USB5V0', L4, 8.29, 8.98, 8.29, 10.2)
rmv += find_v('GND', 7.6, 7.95, 1)
# --- Q1 area
q1vu = [t for t in M0['tracks'][42:81] if t['net'] == 'VU' and t['layer'] == TOP]
assert len(q1vu) == 39 and all(12.7 < min(t['x1'], t['x2']) and max(t['x1'], t['x2']) < 17.3 for t in q1vu)
rm += q1vu
rm += find_t('FLASH-D02', TOP, 17.775, 16.775, 17.85, 15.8)
rmv += find_v('FLASH-D02', 17.85, 15.8, 2)
for x in (16.75, 17.875):
    rmv += find_v('GND', x, 14.925, 1)
    rm += find_t('GND', BOT, x, 14.925, x, 14.95)
rmv += find_v('CLK-12M-SHARED', 15.375, 12.65, 2)
rm += find_t('CLK-12M-SHARED', TOP, 16.325, 13.75, 18.2, 14.6)
rm += find_t('FT-PWREN#', TOP, 17.55, 12.35, 19.825, 13.375)

# de-duplicate (a twin track on the board needs its own entry, so dedupe by identity only)
seen, rm2 = set(), []
for t in rm:
    if id(t) not in seen:
        seen.add(id(t))
        rm2.append(t)
rm = rm2
seen, rmv2 = set(), []
for v in rmv:
    if id(v) not in seen:
        seen.add(id(v))
        rmv2.append(v)
rmv = rmv2


def W(net, layer, w, *pts):
    return [dict(net=net, layer=layer, w=w, x1=a[0], y1=a[1], x2=b[0], y2=b[1]) for a, b in zip(pts, pts[1:])]


add_t = []
add_t += W('VU', L4, 0.2, (3.475, 10.2), (3.075, 8.85))
add_t += W('VU', TOP, 0.4, (14.475, 17.5), (14.475, 14.55), (15.55, 14.225))
add_t += W('USB_D_P', TOP, 0.15, (4.80, 11.43), (5.25, 10.98), (5.25, 8.43), (6.03, 7.65), (9.275, 7.65))
add_t += W('USB_D_N', TOP, 0.15, (4.80, 12.08), (5.55, 11.33), (5.55, 8.73), (6.13, 8.15), (9.275, 8.15))
add_t += W('USB5V0', TOP, 0.35, (4.80, 12.73), (6.75, 12.73), (7.90, 13.88))
add_t += W('GND', TOP, 0.4, (3.9, 8.23), (1.45, 8.23))
add_t += W('GND', TOP, 0.4, (3.9, 14.63), (1.45, 14.63))
add_t += W('GND', TOP, 0.3, (4.125, 10.13), (1.45, 10.13))
add_t += W('VCC3V3', TOP, 0.3, (15.61, 15.4), (17.31, 15.4))
add_v = []
for x, y in ((3.475, 10.2), (3.075, 8.85)):        # VU hop: blind L4>L5>Bottom stacks at the old through-via spots
    add_v.append(dict(net='VU', x=x, y=y, size=0.30, hole=0.15, **{'from': L4, 'to': 'L5-VCC3V3'}))
    add_v.append(dict(net='VU', x=x, y=y, size=0.30, hole=0.15, **{'from': 'L5-VCC3V3', 'to': BOT}))

plan = dict(remove=rm, remove_vias=rmv, tracks=add_t, vias=add_v)
json.dump(plan, open(os.path.join(HERE, 'hand_plan.json'), 'w'), indent=0)
ids_t = {id(t) for t in rm}
ids_v = {id(v) for v in rmv}
R = dict(M0)
R['tracks'] = [t for t in M0['tracks'] if id(t) not in ids_t] + add_t
R['vias'] = [v for v in M0['vias'] if id(v) not in ids_v] + [dict({kk: v[kk] for kk in v if kk not in ('from', 'to')}, span=S[S.index(v['from']):S.index(v['to']) + 1]) for v in add_v]
json.dump(R, open(os.path.join(HERE, 'route_in.json'), 'w'))
print('remove %d tracks, %d vias; add %d tracks, %d vias' % (len(rm), len(rmv), len(add_t), len(add_v)))
