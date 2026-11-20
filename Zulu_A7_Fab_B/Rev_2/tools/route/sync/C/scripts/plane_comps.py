"""plane_comps.py <tag> [...]: the L2-GND / L5-VCC3V3 pour components (planeweb raster, raw) with area and centre,
for base_cur and C/out/<tag>/result.json - to see what any extra component is."""
import json
import os
import sys

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
CDIR = os.path.dirname(HERE)
PREP = os.path.join(os.path.dirname(CDIR), 'prep')
sys.path.insert(0, os.path.join(PREP, 'scripts'))
import geo  # noqa: E402,F401
import planeweb as PW  # noqa: E402

orig_label = ndimage.label
found = {}


def spy(a, structure=None):
    lab, n = orig_label(a, structure=structure)
    found.setdefault('cur', []).append((lab, n))
    return lab, n


ndimage.label = spy
for name, path in [('base_cur', os.path.join(PREP, 'base_cur.json'))] + \
        [(k, os.path.join(CDIR, 'out', k, 'result.json')) for k in sys.argv[1:]]:
    M = json.load(open(path))
    for v in M['vias']:
        v['span'] = PW.J.span(v)
    found['cur'] = []
    PW.run(M, name)
    for (lab, n), (layer, mode) in zip(found['cur'], [(l, m) for l in ('L2-GND', 'L5-VCC3V3') for m in ('raw', 'open')]):
        if mode != 'raw':
            continue
        sizes = np.bincount(lab.ravel())
        out = []
        for c in range(1, n + 1):
            ys, xs = np.nonzero(lab == c)
            out.append((round(sizes[c] * PW.G * PW.G, 3), round(xs.mean() * PW.G, 2), round(ys.mean() * PW.G, 2)))
        out.sort(reverse=True)
        print(name, layer, out)
