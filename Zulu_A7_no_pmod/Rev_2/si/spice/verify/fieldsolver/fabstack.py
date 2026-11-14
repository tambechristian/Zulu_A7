"""Z0/td on the construction the fab notes say will be built (fabrication/Zulu_A7_Fab_B_Rev_2_PCBWay_FAB_NOTES.txt
lines 58-72: L1-L2 3313 0.1015, L2-L3 1080 0.0713, core 1.065, inner 0.5 oz, outer foil+plating), FV solver.
Dk of the PCBWay materials is not in the notes, so it is swept."""
import sys; sys.dont_write_bytecode = True
import numpy as np
from fv_solver import grid, line
G = (1e-3, 1.12, 0.02)
MASK, ER_MASK = 0.03048, 3.8

def strip(w, h1, er1, core, er_core, t=0.0152):
    # z=0 at L5 top; L4/L5 1080 (same h1, er1), core, L3 trace embedded in the L2-L3 prepreg (resin er1 beside it)
    z_l4t = h1 + t; z_l3 = z_l4t + core; z_l3t = z_l3 + t; Ht = z_l3t + h1
    ze = grid([0, h1, z_l4t, z_l3, z_l3t, Ht], *G); xe = grid([0, w / 2, 8.0], *G)
    def eps(X, Z):
        e = np.full(X.shape, er_core); e[Z < z_l4t] = er1; e[Z >= z_l3] = er1; return e
    return line(xe, ze, eps, lambda X, Z: (X < w / 2) & (Z > z_l3) & (Z < z_l3t))

def ms(w, h, er, t, mask='planar'):
    zt = h + t; m = MASK
    ze = grid(sorted(set([0, h, zt, h + m, zt + m, h + 3.0])), *G); xe = grid([0, w / 2, w / 2 + m, 8.0], *G)
    def eps(X, Z):
        e = np.ones(X.shape); e[Z < h] = er
        if mask == 'planar': e[(Z >= h) & (Z < zt + m)] = ER_MASK
        else:
            e[(Z >= h) & (Z < h + m)] = ER_MASK; e[(Z >= h) & (Z < zt + m) & (X < w / 2 + m)] = ER_MASK
        return e
    return line(xe, ze, eps, lambda X, Z: (X < w / 2) & (Z > h) & (Z < zt))

print('L3/L4 w=0.125 on the fab construction (fieldsolve on the PcbDoc stack: 49.08 ohm, 7.133 ps/mm)')
for er1 in (3.9, 4.1, 4.3, 4.6):
    r = strip(0.125, 0.0713, er1, 1.065, 4.5)
    print('  1080 Dk %.1f: Z0 %.2f ohm (%+.1f %%)  td %.3f ps/mm (%+.1f %%)' % (er1, r['Z0'], 100 * (r['Z0'] / 49.075 - 1), r['td'], 100 * (r['td'] / 7.1327 - 1)))
r = strip(0.125, 0.0713, 4.1, 1.065, 4.5, t=0.0178)
print('  1080 Dk 4.1, L3 Cu 0.0178: Z0 %.2f' % r['Z0'])
print('Top w=0.0762 / Bottom w=0.125 on 3313 0.1015 (fieldsolve: 63.61 / 53.18 ohm)')
for er in (4.0, 4.1):
    for t in (0.035, 0.045):
        for w, ref in ((0.0762, 63.614), (0.125, 53.180)):
            r = ms(w, 0.1015, er, t)
            print('  Dk %.1f t=%.3f w=%.4f planar mask: Z0 %.2f (%+.1f %%) td %.3f' % (er, t, w, r['Z0'], 100 * (r['Z0'] / ref - 1), r['td']))
