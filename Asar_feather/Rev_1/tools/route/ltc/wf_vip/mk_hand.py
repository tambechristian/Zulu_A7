"""Hand copper for the via-in-pad strategy: PWR_SW clean on Bottom, VU pin 24 -> C167-2 -> L8-2 on Bottom,
C167 GND re-tie, PWR_FB2 Bottom wall (R113-2 via -> R114-1) removed for re-route."""
import json, sys
base = json.load(open(sys.argv[1]))
out = sys.argv[2]
B = 'Bottom Layer'
def T(net, w, x1, y1, x2, y2, L=B):
    return {'net': net, 'layer': L, 'w': w, 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2}
tracks = [
    # PWR_SW: 0.3 neck between C167's pads, 0.4 to L8-1, Bottom only, no vias
    T('PWR_SW', 0.3, 10.275, 14.9, 10.275, 13.05),
    T('PWR_SW', 0.4, 10.275, 13.05, 11.75, 13.05),
    T('PWR_SW', 0.4, 11.75, 13.05, 12.35, 12.45),
    # VU: U8-24 -> C167-2 -> L8-2
    T('VU', 0.3, 11.25, 14.9, 11.25, 13.9),
    T('VU', 0.5, 10.95, 13.9, 12.45, 13.9),
    # GND: C167-1 (now at 9.65) back to the pin-27 GND via
    T('GND', 0.3, 9.85, 14.425, 9.85, 14.1),
]
rm = []
def same(t, a):
    return t['net'] == a[0] and t['layer'] == a[1] and abs(t['x1'] - a[2]) < 1e-6 and abs(t['y1'] - a[3]) < 1e-6 and abs(t['x2'] - a[4]) < 1e-6 and abs(t['y2'] - a[5]) < 1e-6
kill = [('GND', B, 10.075, 14.15, 9.85, 14.425),
        ('PWR_FB2', B, 15.975, 12.8, 15.8, 12.975), ('PWR_FB2', B, 15.8, 12.975, 15.8, 13.275),
        ('PWR_FB2', B, 15.8, 13.275, 15.725, 13.35), ('PWR_FB2', B, 15.725, 13.35, 12.275, 13.35),
        ('PWR_FB2', B, 12.275, 13.35, 11.825, 12.9), ('PWR_FB2', B, 11.825, 12.9, 11.8, 12.9),
        ('PWR_FB2', B, 11.8, 12.9, 11.775, 12.875), ('PWR_FB2', B, 11.775, 12.875, 9.25, 12.875),
        ('PWR_FB2', B, 9.25, 12.875, 8.85, 12.475)]
for a in kill:
    hit = [t for t in base['tracks'] if same(t, a)]
    assert len(hit) == 1, a
    rm.append(hit[0])
json.dump({'tracks': tracks, 'vias': [], 'remove': rm}, open(out, 'w'), indent=1)
print('tracks', len(tracks), 'remove', len(rm))
