import json, sys, copy
sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools')
import board_illustration as BI
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
cx, Yp, out, title = float(sys.argv[1]), float(sys.argv[2]), sys.argv[3], sys.argv[4]
M = json.load(open(BI.BASE)); D = json.load(open(BI.COMPS))
M['pads'] = [p for p in M['pads'] if p['ref'] != 'X4'] + [
    {'ref': 'X4', 'pad': '1', 'net': 'VBATT', 'x': cx, 'y': Yp, 'shape': 'circle', 'w': 1.2, 'h': 1.2, 'layers': None, 'drill': 0.75},
    {'ref': 'X4', 'pad': '2', 'net': 'GND', 'x': cx - 2, 'y': Yp, 'shape': 'circle', 'w': 1.2, 'h': 1.2, 'layers': None, 'drill': 0.75}]
# old SMD X4 feed tracks on Top are gone with the part
M['tracks'] = [t for t in M['tracks'] if not (t['layer'] == 'Top Layer' and t['net'] in ('VBATT',) and min(t['y1'], t['y2']) < 7)]
D['mech']['X4']['off'] = [-1.35, -5.65, 1.35, 0.75]
silk = BI.read_silk(BI.PCB)
W, H = M['board']['w'], M['board']['h']
xr, yr = (-1.0, W + 1.0), (-6.0, H + 1.9)
fig_w = 20.0; fig_h = fig_w * (yr[1] - yr[0]) / (xr[1] - xr[0])
fig = plt.figure(figsize=(fig_w, fig_h), dpi=100, facecolor='white'); ax = fig.add_axes([0, 0, 1, 1])
pts = fig_w * 72.0 / (xr[1] - xr[0])
BI.draw(ax, M, D, silk, pts)
# side-entry housing: cream body, the mating opening on the south (off-board) face, pins at the back
b = (cx - 3.95, Yp - 6.25, cx + 1.95, Yp + 1.35)
ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fc=BI.CREAM, ec='#333333', lw=0.8, zorder=4.8))
ax.add_patch(Rectangle((b[0] + 0.7, b[1]), b[2] - b[0] - 1.4, 3.2, fc='#4a4536', ec='#333333', lw=0.6, zorder=4.9))
ax.plot([xr[0], xr[1]], [0, 0], color='#ff5050', lw=1.2, ls='--', zorder=9)
ax.text(b[2] + 0.4, b[1] + 1.2, 'battery plug enters here (side entry)\nhousing overhangs the edge by %.2f mm' % (6.25 - Yp),
        fontsize=12, color='#333333', va='center', zorder=9)
ax.text(xr[0] + 0.3, -0.55, 'board edge', fontsize=10, color='#ff5050', zorder=9)
ax.text(xr[0] + 0.3, yr[1] - 0.6, title, fontsize=13, color='#333333', zorder=9)
ax.set_xlim(*xr); ax.set_ylim(*yr); ax.set_aspect('equal'); ax.axis('off')
fig.savefig(out, facecolor='white'); print(out)
