import json
M = json.load(open('base2.json'))
rem = [t for t in M['tracks'] if t['net'] == 'PWR_PGOODALL' and (
    (abs(t['x1'] - 11.325) < 1e-3 and abs(t['y1'] - 14.1) < 1e-3) or (abs(t['x1'] - 11.8) < 1e-3 and abs(t['y1'] - 14.875) < 1e-3)
    or (abs(t['x1'] - 11.85) < 1e-3 and abs(t['y1'] - 15.5) < 1e-3))]
remv = [v for v in M['vias'] if v['net'] == 'PWR_PGOODALL' and ((abs(v['x'] - 11.8) < 1e-3 and abs(v['y'] - 14.875) < 1e-3) or (abs(v['x'] - 11.85) < 1e-3 and abs(v['y'] - 15.5) < 1e-3))]
print(len(rem), len(remv))
X, Y = 11.75, 14.75
vias = [dict(net='VBATT', x=X, y=Y, size=0.25, hole=0.10, **{'from': 'L5-VCC3V3', 'to': 'Bottom Layer'}),
        dict(net='VBATT', x=X, y=Y, size=0.25, hole=0.10, **{'from': 'L4-SIG', 'to': 'L5-VCC3V3'}),
        dict(net='VBATT', x=X, y=Y, size=0.27, hole=0.15, **{'from': 'L3-SIG', 'to': 'L4-SIG'}),
        dict(net='VBATT', x=X, y=Y, size=0.25, hole=0.10, **{'from': 'L2-GND', 'to': 'L3-SIG'}),
        dict(net='VBATT', x=X, y=Y, size=0.25, hole=0.10, **{'from': 'Top Layer', 'to': 'L2-GND'})]
T = 'Top Layer'
pts = [(X, Y), (10.4, 14.75), (10.0, 15.25)]
tr = [{'net': 'VBATT', 'layer': T, 'w': 0.3, 'x1': a[0], 'y1': a[1], 'x2': b[0], 'y2': b[1]} for a, b in zip(pts, pts[1:])]
json.dump({'tracks': tr, 'vias': vias, 'remove': rem, 'remove_vias': remv}, open('vbatt_m.json', 'w'), indent=0)
