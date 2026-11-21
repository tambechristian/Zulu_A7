"""usb_metrics.py <plan or model json>: USB_D_P/USB_D_N lengths, coupled length (pitch 0.30 +-0.01), vias"""
import json, math, sys
D = json.load(open(sys.argv[1]))
T = {n: [t for t in D['tracks'] if t['net'] == n] for n in ('USB_D_P', 'USB_D_N')}
def segd(px, py, t):
    x1, y1, x2, y2 = t['x1'], t['y1'], t['x2'], t['y2']; dx, dy = x2 - x1, y2 - y1; L2 = dx*dx+dy*dy
    k = 0 if L2 == 0 else max(0, min(1, ((px-x1)*dx+(py-y1)*dy)/L2)); return math.hypot(px-x1-k*dx, py-y1-k*dy)
for n in T: print(n, 'length %.4f' % sum(math.hypot(t['x2']-t['x1'], t['y2']-t['y1']) for t in T[n]), 'tracks', len(T[n]),
                 'layers', sorted({t['layer'] for t in T[n]}), 'widths', sorted({t['w'] for t in T[n]}))
c = 0; step = 0.005
for t in T['USB_D_P']:
    L = math.hypot(t['x2']-t['x1'], t['y2']-t['y1']); k = max(1, int(L/step))
    for i in range(k):
        f = (i+0.5)/k; x = t['x1']+(t['x2']-t['x1'])*f; y = t['y1']+(t['y2']-t['y1'])*f
        if abs(min(segd(x, y, u) for u in T['USB_D_N']) - 0.30) < 0.01: c += L/k
print('coupled (D_P measured) %.3f' % c)
print('vias', [v for v in D['vias'] if 'USB' in v['net']])
