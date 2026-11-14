"""Third check of the offset-stripline number: far plane -> infinity limit is a fully embedded microstrip,
Z = Z_air(HJ thick microstrip)/sqrt(er). FV run at growing h2 must approach it from below."""
import sys; sys.dont_write_bytecode = True
import numpy as np
from fv_solver import grid, line
from zulu_independent import hj_thick, CORE, T_IN
w = 0.125; h1 = CORE; er = 4.6
za, _ = hj_thick(w, h1, T_IN, 1.0)
print('HJ embedded-microstrip limit: %.3f ohm' % (za / np.sqrt(er)))
for h2 in (1.136, 3.0, 6.0):
    b = h1 + T_IN + h2
    ze = grid([0, h2, h2 + T_IN, b], 1e-3, 1.12, 0.02); xe = grid([0, w / 2, max(8.0, 4 * h2)], 1e-3, 1.12, 0.05)
    r = line(xe, ze, lambda X, Z: np.full(X.shape, er), lambda X, Z: (X < w / 2) & (Z > h2) & (Z < h2 + T_IN))
    print('FV h2=%.3f: %.3f' % (h2, r['Z0']))
