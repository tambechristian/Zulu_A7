"""hand plan for PWR_SW / USB5V0 / VBATT / VU around U8's bottom row (Asar feather).
writes plan_hand.json (relative to placed.json = model_frozenC + R114 moved)"""
import json

B, T, L3, L4 = 'Bottom Layer', 'Top Layer', 'L3-SIG', 'L4-SIG'
M = json.load(open('placed.json'))
tracks, vias = [], []


def tr(net, layer, w, pts):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        tracks.append({'net': net, 'layer': layer, 'w': w, 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2})


def via(net, x, y, fr, to, size=0.3, hole=0.15):
    vias.append({'net': net, 'x': x, 'y': y, 'size': size, 'hole': hole, 'from': fr, 'to': to})


def stack_bot(net, x, y):            # Bottom -> L5 -> L4
    via(net, x, y, 'L4-SIG', 'L5-VCC3V3')
    via(net, x, y, 'L5-VCC3V3', B)


def stack_full(net, x, y):           # Bottom -> Top
    via(net, x, y, T, 'L2-GND')
    via(net, x, y, 'L2-GND', L3)
    via(net, x, y, L3, L4, 0.27, 0.15)
    stack_bot(net, x, y)


# ---- PWR_SW: pin 26 via-in-pad, L4 loop under the pin row, up into L8-1 (two stacks)
stack_bot('PWR_SW', 10.25, 14.75)
stack_bot('PWR_SW', 13.35, 12.3)
stack_bot('PWR_SW', 13.35, 11.85)
tr('PWR_SW', L4, 0.35, [(10.25, 14.75), (10.65, 15.2), (12.45, 15.2), (13.35, 14.3), (13.35, 11.85)])

# ---- VBATT: pin 23 full stack -> Top -> X4-1; L4 1.1 strip -> C151-2 stack
stack_full('VBATT', 11.75, 14.75)
tr('VBATT', T, 0.33, [(11.6, 14.72), (10.55, 14.72), (10.15, 15.15)])
tr('VBATT', L4, 1.1, [(11.75, 14.3), (12.15, 13.9), (12.15, 10.95)])
stack_bot('VBATT', 12.35, 10.95)

# ---- USB5V0: pin 25 north to C150-2
tr('USB5V0', B, 0.2, [(10.75, 14.6), (10.75, 14.5), (10.9, 14.35), (10.9, 12.1)])

# ---- VU: pin 24 -> L8-2 ; R108-1 -> between C150 pads -> C167-2
tr('VU', B, 0.25, [(11.25, 14.6), (11.25, 14.25)])
tr('VU', B, 0.3, [(11.3, 14.25), (12.3, 14.25)])
tr('VU', B, 0.2, [(10.525, 10.8), (10.525, 13.0), (9.2, 13.0), (9.2, 13.5)])

# ---- PWR_PROG (re-routed by hand to clear the VBATT strip): L4 then L3 to the through via
tr('PWR_PROG', L4, 0.0762, [(12.35, 10.025), (12.95, 10.45), (12.95, 13.9)])
via('PWR_PROG', 12.95, 13.9, L3, L4, 0.27, 0.15)
tr('PWR_PROG', L3, 0.0762, [(12.95, 13.9), (12.95, 14.55), (12.8, 14.9), (12.72, 15.35), (12.675, 16.475)])

# ---- PWR_FB2: R114 moved next to R113
tr('PWR_FB2', B, 0.1, [(15.55, 11.72), (15.8, 11.97), (15.8, 12.45), (15.975, 12.625)])
tr('GND', B, 0.2, [(14.95, 11.72), (14.95, 12.2)])

# ---- removals
def sel_t(f):
    return [t for t in M['tracks'] if f(t)]
rm = []
rm += sel_t(lambda t: t['net'] == 'PWR_FB2' and t['layer'] == B and min(t['y1'], t['y2']) > 12.4 and max(t['y1'], t['y2']) < 13.4)
rm += sel_t(lambda t: t['net'] == 'GND' and t['layer'] == B and abs(t['x1'] - 8.725) < 1e-3 and abs(t['y1'] - 11.675) < 1e-3)
pg = [((9.85, 12.625), (11.325, 14.1)), ((11.325, 14.1), (11.8, 14.875)), ((11.8, 14.875), (11.85, 15.5)), ((11.85, 15.5), (11.825, 15.8))]
en = [((12.575, 15.225), (9.35, 15.175)), ((14.525, 17.175), (12.575, 15.225))]
pp = [((12.35, 10.025), (12.7, 12.3)), ((12.7, 12.3), (12.7, 14.95)), ((12.7, 14.95), (12.675, 16.475))]
def match(t, net, segs):
    if t['net'] != net:
        return False
    e = {(round(t['x1'], 3), round(t['y1'], 3)), (round(t['x2'], 3), round(t['y2'], 3))}
    return any(e == {a, b} for a, b in segs)
rm += sel_t(lambda t: match(t, 'PWR_PGOODALL', pg) or match(t, 'EN', en) or match(t, 'PWR_PROG', pp))
rmv = [v for v in M['vias'] if (v['net'] == 'PWR_PGOODALL' and (v['x'], v['y']) in ((11.8, 14.875), (11.85, 15.5))) or
       (v['net'] == 'PWR_PROG' and (v['x'], v['y']) == (12.7, 14.95))]
print('remove tracks', len(rm), 'vias', len(rmv))
json.dump({'tracks': tracks, 'vias': vias, 'remove': rm, 'remove_vias': rmv}, open('plan_hand.json', 'w'), indent=0)
