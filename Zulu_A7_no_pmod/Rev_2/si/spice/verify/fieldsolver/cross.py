"""(1) fieldsolve with the mask removed vs HJ thick; (2) FV vs Cohn; (3) FV vs Wheeler symmetric + offset formula error;
(4) stack sensitivities with the FV solver: trapezoid etch, 1 oz inner copper, mask thinner on trace top."""
import sys, os, numpy as np
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import fieldsolve as F
from fv_solver import grid, line
from zulu_independent import *
G = (1e-3, 1.12, 0.02)

print('(1) fieldsolve with ER_MASK=1 (geometry otherwise identical) vs HJ thick uncoated')
for w in (0.0762, 0.125):
    slabs, tr, pb, pt = F.layer_geometry('Top Layer', w)
    slabs = [(s[0], 1.0) if s[1] == F.ER_MASK else s for s in slabs]
    r = F.line_params(slabs, tr, pb, pt)
    z, ee = hj_thick(w, PP, T_OUT, ER_PP)
    print('  w=%.4f fieldsolve Z0 %.3f eeff %.4f | HJ %.3f %.4f | dZ %.2f %%' % (w, r['Z0'], r['eps_eff'], z, ee, 100 * (r['Z0'] / z - 1)))

print('(2) FV vs Cohn (zero-thickness ~ 0.1 um strip, centred, er 4.3)')
for w, b in [(0.125, 0.4), (0.125, 2.4)]:
    tt = 1e-4
    ze = grid([0, b / 2 - tt / 2, b / 2 + tt / 2, b], *G); xe = grid([0, w / 2, 8.0], *G)
    r = line(xe, ze, lambda X, Z: np.full(X.shape, 4.3), lambda X, Z: (X < w / 2) & (Z > b / 2 - tt / 2) & (Z < b / 2 + tt / 2))
    k = 1 / np.cosh(np.pi * w / (2 * b)); kp = np.sqrt(1 - k * k)
    zc = 30 * np.pi / np.sqrt(4.3) * ellipk(k ** 2) / ellipk(kp ** 2)
    print('  w=%.3f b=%.2f FV %.3f Cohn %.3f (%.2f %%)' % (w, b, r['Z0'], zc, 100 * (r['Z0'] / zc - 1)))

print('(3) closed-form stripline formulas vs FV on the Zulu offset geometry, homogeneous er 4.6')
w = 0.125; h1 = CORE; h2 = CORE + T_IN + MID
xe, ze, eps, cond, Ht = strip_geom(w, *G)
r = line(xe, ze, lambda X, Z: np.full(X.shape, 4.6), cond)
print('  FV offset homogeneous: %.3f | Wheeler-offset parallel combo %.3f | IPC-2141 %.3f' % (r['Z0'], offset_strip(w, h1, h2, T_IN, 4.6), ipc_offset(w, h1, h2, T_IN, 4.6)))
b = 2 * h1 + T_IN
ze2 = grid([0, h1, h1 + T_IN, b], *G)
r2 = line(xe, ze2, lambda X, Z: np.full(X.shape, 4.6), lambda X, Z: (X < w / 2) & (Z > h1) & (Z < h1 + T_IN))
print('  symmetric b=%.4f: FV %.3f | Wheeler thick %.3f' % (b, r2['Z0'], wheeler_strip(w, b, T_IN, 4.6)))
b = 2 * h2 + T_IN
ze3 = grid([0, h2, h2 + T_IN, b], *G)
r3 = line(xe, ze3, lambda X, Z: np.full(X.shape, 4.6), lambda X, Z: (X < w / 2) & (Z > h2) & (Z < h2 + T_IN))
print('  symmetric b=%.4f: FV %.3f | Wheeler thick %.3f' % (b, r3['Z0'], wheeler_strip(w, b, T_IN, 4.6)))
print('  parallel combo of the two FV symmetric results: %.3f  (vs FV offset %.3f)' % (2 * r2['Z0'] * r3['Z0'] / (r2['Z0'] + r3['Z0']), r['Z0']))

print('(4) sensitivities (FV, same grid)')
base = line(*strip_geom(0.125, *G)[:4])
print('  L3 base                    Z0 %.3f td %.4f' % (base['Z0'], base['td']))
# 1 oz inner copper (0.035) with the same dielectric heights
import zulu_independent as ZI
save = ZI.T_IN; ZI.T_IN = 0.035
r = line(*ZI.strip_geom(0.125, *G)[:4]); ZI.T_IN = save
print('  L3 inner Cu 0.035          Z0 %.3f (%+.2f %%) td %.4f' % (r['Z0'], 100 * (r['Z0'] / base['Z0'] - 1), r['td']))
# trapezoid etch on L3 (narrow face 0.0254 narrower, narrow side away from the core = facing MID)
xe, ze, eps, cond, Ht = strip_geom(0.125, 2.5e-4, 1.12, 0.02)
z_l3 = CORE + T_IN + MID
tz = lambda X, Z: (Z > z_l3) & (Z < z_l3 + T_IN) & (X < 0.125 / 2 - 0.0127 * (1 - (Z - z_l3) / T_IN))
r = line(xe, ze, eps, tz)
print('  L3 trapezoid (-1 mil)      Z0 %.3f (%+.2f %%)' % (r['Z0'], 100 * (r['Z0'] / base['Z0'] - 1)))
for w in (0.0762, 0.125):
    b0 = line(*ms_geom(w, *G, mask='planar')[:4])
    xe, ze, eps, cond = ms_geom(w, 2.5e-4, 1.12, 0.02, mask='planar')
    tz = lambda X, Z, w=w: (Z > PP) & (Z < PP + T_OUT) & (X < w / 2 - 0.0127 * (Z - PP) / T_OUT)
    r = line(xe, ze, eps, tz)
    print('  Top w=%.4f planar base Z0 %.3f; trapezoid top 1 mil narrower Z0 %.3f (%+.2f %%)' % (w, b0['Z0'], r['Z0'], 100 * (r['Z0'] / b0['Z0'] - 1)))
    # mask 0.5 mil on trace top, 1.2 mil on substrate and sides (typical LPI over a 1.4 mil trace)
    xe, ze, eps0, cond = ms_geom(w, *G, mask='none')
    zt = PP + T_OUT
    ze = grid(sorted(set(list(ze) + [zt + 0.5 * MIL])), *G) if False else grid([0, PP, zt, PP + MASK, zt + 0.5 * MIL, PP + 3.0], *G)
    xe = grid([0, w / 2, w / 2 + MASK, 8.0], *G)
    def e2(X, Z):
        e = np.ones(X.shape); e[Z < PP] = ER_PP
        e[(Z >= PP) & (Z < PP + MASK)] = ER_MASK
        e[(Z >= PP) & (Z < zt + 0.5 * MIL) & (X < w / 2 + MASK)] = ER_MASK
        return e
    r = line(xe, ze, e2, lambda X, Z: (X < w / 2) & (Z > PP) & (Z < zt))
    print('  Top w=%.4f conformal, 0.5 mil on top: Z0 %.3f (%+.2f %% vs planar) td %.4f (%+.2f %%)' % (w, r['Z0'], 100 * (r['Z0'] / b0['Z0'] - 1), r['td'], 100 * (r['td'] / b0['td'] - 1)))
