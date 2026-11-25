"""Does ngspice's B-source pwl() clamp or extrapolate outside its table? Table (0,0) (1,1) (2,4); sweep x -2..5."""
import sys, os
sys.path.insert(0, os.path.abspath('../..'))
import numpy as np, ngs
lines = ['* pwl extrap', 'Vx x 0 0', 'B1 y 0 V = pwl(V(x), 0, 0, 1, 1, 2, 4)', 'Ry y 0 1k',
         '.dc Vx -2 5 0.5', '.end']
r = ngs.run(lines)
x = r['v-sweep'] if 'v-sweep' in r else r[[k for k in r if 'sweep' in k][0]]
for a, b in zip(x, r['y']):
    print('x=%5.2f  pwl=%7.3f   clamp=%5.2f  linear-extrap=%6.2f' % (a, b, np.interp(a, [0, 1, 2], [0, 1, 4]),
          a if a < 0 else (np.interp(a, [0,1,2],[0,1,4]) if a <= 2 else 4 + 3 * (a - 2))))
