"""Stage A: row moved by DY + via jogs; writes model1.json (pads moved only) and model_a.json (+ jogs, minus the
TDI/FT-RESETN copper that the move makes illegal) as router input."""
import copy
import json
import sys
from geo import *

DY = float(sys.argv[1]) if len(sys.argv) > 1 else 0.125
M0 = load()
M1 = copy.deepcopy(M0)
for p in M1['pads']:
    if p['ref'] in ROW:
        p['y'] = round(p['y'] + DY, 4)
json.dump(M1, open('model1.json', 'w'))


def padc(ref, pad):
    p = [p for p in M1['pads'] if p['ref'] == ref and p['pad'] == pad]
    assert len(p) == 1
    return p[0]['x'], p[0]['y']


def find_v(M, net, x, y, span=None):
    c = [v for v in M['vias'] if v['net'] == net and abs(v['x'] - x) < 0.002 and abs(v['y'] - y) < 0.002 and
         (span is None or ''.join(AB[l] for l in v['span']) == span)]
    assert len(c) == 1, (net, x, y, span, len(c))
    return c[0]


def find_t(M, net, layer, x1, y1, x2, y2):
    k = lambda a, b: (round(a, 3), round(b, 3))
    c = [t for t in M['tracks'] if t['net'] == net and t['layer'] == layer and
         {k(t['x1'], t['y1']), k(t['x2'], t['y2'])} == {k(x1, y1), k(x2, y2)}]
    assert len(c) == 1, (net, layer, x1, y1, x2, y2, len(c))
    return c[0]


# jogs: (net, from-point (a via centre), pad, width)
JOGS = [
    ('GND', (8.750, 2.525), ('C40', '1'), 0.20),
    ('FT-VPHY', (9.675, 2.500), ('C40', '2'), 0.15),
    ('GND', (10.175, 2.350), ('C41', '1'), 0.20),
    ('FT-VPLL', (10.675, 2.350), ('C41', '2'), 0.20),
    ('GND', (13.550, 2.325), ('C152', '1'), 0.20),
    ('GND', (14.725, 2.350), ('C153', '1'), 0.20),
    ('FT-VCORE', (15.675, 2.475), ('C153', '2'), 0.15),
    ('GND', (16.175, 2.350), ('C154', '1'), 0.20),
    ('VCC3V3', (17.775, 2.550), ('R19', '2'), 0.20),
    ('GND', (19.350, 2.525), ('C155', '1'), 0.20),
    ('VCC3V3', (19.950, 2.550), ('C155', '2'), 0.20),
    ('GND', (20.575, 2.300), ('C156', '1'), 0.20),
    ('VCC3V3', (21.150, 2.550), ('C156', '2'), 0.20),
    ('GND', (21.775, 2.525), ('C157', '1'), 0.20),
    ('VCC3V3', (22.350, 2.550), ('C157', '2'), 0.20),
    ('GND', (22.950, 2.525), ('C158', '1'), 0.20),
    ('VCC3V3', (23.575, 2.550), ('C158', '2'), 0.20),
    ('GND', (24.150, 2.525), ('C159', '1'), 0.20),
    ('VCC3V3', (24.775, 2.550), ('C159', '2'), 0.20),
    ('GND', (25.350, 2.525), ('C38', '1'), 0.20),
    ('VCC3V3', (25.950, 2.550), ('C38', '2'), 0.20),
]
jogs = []
for net, (x, y), (ref, pad), w in JOGS:
    assert any(abs(v["x"] - x) < 0.002 and abs(v["y"] - y) < 0.002 and v["net"] == net and "Bottom Layer" in v["span"] for v in M1["vias"]), (net, x, y)
    px, py = padc(ref, pad)
    jogs.append(dict(net=net, layer='Bottom Layer', w=w, x1=x, y1=y, x2=px, y2=py))
json.dump(jogs, open('jogs.json', 'w'), indent=1)

if __name__ == '__main__':
    print('model1 written, %d jogs' % len(jogs))
