"""Bottom side before vs after around the new JTAG block: python picture.py -> jtag_east_bottom.png"""
import json
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import draw  # noqa: E402

J = os.path.dirname(HERE)
M0 = json.load(open(os.path.join(J, 'model.json')))
MF = json.load(open(os.path.join(HERE, 'model_final.json')))
c0 = json.load(open(os.path.join(J, 'comps.json')))
cF = json.load(open(os.path.join(HERE, 'comps_final.json')))
fig = plt.figure(figsize=(16, 15.5))
gs = fig.add_gridspec(2, 2, height_ratios=[1.05, 1.0])
zoom = (14.6, 20.6, 3.6, 10.2)
wide = (3.0, 21.5, 1.0, 10.6)
a = fig.add_subplot(gs[0, 0]); draw.panel(a, M0, c0, zoom, 'BEFORE (Bottom, seen from the top): JP3 alone at x 17.75', inner=True)
b = fig.add_subplot(gs[0, 1]); draw.panel(b, MF, cF, zoom, 'AFTER: 2x3 block at 1.27 pitch, JP3 x 17.20 | JP4 x 18.47', inner=True)
c = fig.add_subplot(gs[1, 0]); draw.panel(c, M0, c0, wide, 'BEFORE, wide: JP4 at the south-west, 11 mm from JP3')
d = fig.add_subplot(gs[1, 1]); draw.panel(d, MF, cF, wide, 'AFTER, wide: the old JP4 site and its TDI / TDO / VCC3V3 copper removed')
fig.suptitle('Asar A7 Feather JTAG test points, strategy east. Solid: Bottom copper (JTAG nets coloured); dashed: '
             'TCK/TMS/TDI/TDO on L3/L4; tan boxes: part bodies (body_check)', fontsize=10)
fig.tight_layout(rect=(0, 0, 1, 0.98))
fig.savefig(os.path.join(HERE, 'jtag_east_bottom.png'), dpi=130)
print('jtag_east_bottom.png')
