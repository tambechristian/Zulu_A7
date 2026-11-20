import json, sys, time, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import exact_router as X
R = X.R
M = json.load(open('model_nets_s1.json'))
S = json.load(open('seeds_nets_s1.json'))
B = R.Board(M)
Rt = R.Router(B)
Rt.out_t = S['tracks'][:60]; Rt.out_v = S['vias'][:20]
t = time.time(); X._global(B); print('global field %.1f s' % (time.time() - t))
wins = [R.window(B, [(49, 6, 52, 10)], 1.0), R.window(B, [(50, 5, 63, 9)], 2.5), R.window(B, [(20, 2, 60, 20)], 3)]
for net in ('JA1', 'JA8', 'UART_FT_TXD', 'GND', 'PROG#'):
    for w in wins:
        for base in (True, False):
            t = time.time(); a = X.exact_dist(Rt, net, w, base); ta = time.time() - t
            t = time.time(); b = X.fast_dist(Rt, net, w, base); tb = time.time() - t
            mx = max(float(np.max(np.abs(np.minimum(a[l], 0.5) - np.minimum(b[l], 0.5)))) for l in R.STACK)
            print(net, w, base, 'maxdiff %.2e' % mx, 'slow %.2fs fast %.2fs' % (ta, tb))
