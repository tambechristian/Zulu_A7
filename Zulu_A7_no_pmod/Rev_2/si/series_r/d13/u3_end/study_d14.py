"""D14: (1) GND47 microvia sites, (2) Top reach from D14's via land with GND47 unlocked, (3) legal L4 column sites."""
import engine as G, numpy as np, json, math
from scipy import ndimage
W = G.World()
# (1) GND47 sites
sites = []
for x in np.arange(37.96, 38.46, 0.01):
    for y in np.arange(16.90, 17.60, 0.01):
        c = G.Cand(W, 14)
        G.make_gnd47((round(x, 3), round(y, 3)))(c)
        v, w = c.verify(margin=G.DESIGN_MARGIN)
        if not v:
            m = min(val[0] for val in w.values())
            sites.append((round(m, 4), round(x, 3), round(y, 3)))
sites.sort(reverse=True)
print('GND47 microvia sites legal (exact, margin>=2.5um):', len(sites), sites[:8])
json.dump(sites, open('gnd47_sites.json', 'w'))
