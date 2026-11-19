import sys, math
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon
import base
C = base.C

def cap_poly(x1, y1, x2, y2, r, n=10):
    a = math.atan2(y2 - y1, x2 - x1)
    pts = []
    for k in range(n + 1):
        t = a + math.pi / 2 + math.pi * k / n
        pts.append((x2 + r * math.cos(t - math.pi), y2 + r * math.sin(t - math.pi)))
    for k in range(n + 1):
        t = a + math.pi / 2 + math.pi * k / n
        pts.append((x1 + r * math.cos(t), y1 + r * math.sin(t)))
    return pts

def draw(ax, L, pads, tracks, vias, box, HL=('D13', 'D14', 'D15'), extra=None):
    X0, X1, Y0, Y1 = box
    ax.set_title(L); ax.set_xlim(X0, X1); ax.set_ylim(Y0, Y1); ax.set_aspect('equal'); ax.grid(alpha=.3)
    for t in tracks:
        if t is None or t['layer'] != L: continue
        if max(t['x1'], t['x2']) < X0-1 or min(t['x1'], t['x2']) > X1+1 or max(t['y1'], t['y2']) < Y0-1 or min(t['y1'], t['y2']) > Y1+1: continue
        col = 'red' if t['net'] in HL else ('blue' if t['net'] and t['net'].startswith('SDRAM') else 'grey')
        ax.add_patch(Polygon(cap_poly(t['x1'], t['y1'], t['x2'], t['y2'], t['w'] / 2), fc=col, alpha=.45, lw=0))
        mx, my = (t['x1']+t['x2'])/2, (t['y1']+t['y2'])/2
        if X0 < mx < X1 and Y0 < my < Y1:
            ax.text(mx, my, '%s' % (t['net']), fontsize=4.5, color='darkgreen')
    for p in pads:
        lay = C.CU if p['layer'] == 'Multi' else [p['layer']]
        if L not in lay: continue
        if not (X0-2 < p['x'] < X1+2 and Y0-2 < p['y'] < Y1+2): continue
        col = 'red' if p['net'] in HL else ('gold' if (p['ref'][0] == 'R' and p['ref'][1:].isdigit() and int(p['ref'][1:]) >= 119) else 'k')
        S = C.pad_shape(p, L)
        if S[0] == 'R':
            ax.add_patch(Rectangle((S[1]-S[3], S[2]-S[4]), 2*S[3], 2*S[4], fc=col, alpha=.35, ec='k', lw=.5))
        else:
            ax.add_patch(Polygon(cap_poly(S[1], S[2], S[3], S[4], S[5]), fc=col, alpha=.35, ec='k', lw=.5))
        ax.text(p['x'], p['y'], '%s-%s\n%s' % (p['ref'], p['pad'], p['net']), fontsize=5, ha='center', va='center')
    for v in vias:
        if v is None or L not in v['span']: continue
        if not (X0-1 < v['x'] < X1+1 and Y0-1 < v['y'] < Y1+1): continue
        col = 'red' if v['net'] in HL else 'c'
        ax.add_patch(Circle((v['x'], v['y']), v['size']/2, fc=col, alpha=.5, ec='k', lw=.3))
        ax.text(v['x'], v['y'], '%s\n%s>%s' % (v['net'], v['span'][0][:3], v['span'][-1][:3]), fontsize=4, ha='center', va='center')
    if extra: extra(ax, L)

if __name__ == '__main__':
    E, pads, tracks, vias, nf = base.applied()
    X0, X1, Y0, Y1 = [float(v) for v in sys.argv[1:5]]
    out = sys.argv[5]
    layers = sys.argv[6].split(',')
    n = len(layers)
    fig, axs = plt.subplots(n, 1, figsize=(16, 16 * n * (Y1 - Y0) / (X1 - X0) + 0.6 * n))
    if n == 1: axs = [axs]
    for ax, L in zip(axs, layers):
        draw(ax, L, pads, tracks, vias, (X0, X1, Y0, Y1))
    plt.tight_layout(); plt.savefig(out, dpi=100)
