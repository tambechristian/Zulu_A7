"""Independent Z0/td for the Zulu Rev 2 geometries: own FV solver (refinement series + Richardson) and closed forms."""
import sys, time, numpy as np
sys.dont_write_bytecode = True
from fv_solver import grid, line
from scipy.special import ellipk
MIL = 0.0254
T_OUT, T_IN = 1.378 * MIL, 0.5984 * MIL
PP, ER_PP = 3.913 * MIL, 4.1
CORE, ER_CORE = 3.937 * MIL, 4.6
MID, ER_MID = 44.126 * MIL, 4.523
MASK, ER_MASK = 1.2 * MIL, 3.8

def strip_geom(w, h0, ratio, hmax):
    # z = 0 at L5 top face, z = Htot at L2 bottom face. L3 trace: top face touches the L2/L3 core.
    z_l4 = CORE; z_mid0 = CORE + T_IN; z_l3 = z_mid0 + MID; z_l3t = z_l3 + T_IN; Ht = z_l3t + CORE
    ze = grid([0, CORE, z_mid0, z_l3, z_l3t, Ht], h0, ratio, hmax)
    xe = grid([0, w / 2, 8.0], h0, ratio, hmax)
    def eps(X, Z):
        e = np.full(X.shape, ER_MID)
        e[Z < CORE] = ER_CORE; e[Z > z_l3t] = ER_CORE
        return e
    cond = lambda X, Z: (X < w / 2) & (Z > z_l3) & (Z < z_l3t)
    return xe, ze, eps, cond, Ht

def ms_geom(w, h0, ratio, hmax, mask='planar', air=3.0, t=T_OUT, h=PP):
    zt = h + t; m = MASK
    br = [0, h, zt, h + m, zt + m, h + air]
    ze = grid(sorted(set(br)), h0, ratio, hmax)
    xe = grid([0, w / 2, w / 2 + m, 8.0], h0, ratio, hmax)
    def eps(X, Z):
        e = np.ones(X.shape); e[Z < h] = ER_PP
        if mask == 'planar':
            e[(Z >= h) & (Z < zt + m)] = ER_MASK
        elif mask == 'conformal':
            e[(Z >= h) & (Z < h + m)] = ER_MASK
            e[(Z >= h) & (Z < zt + m) & (X < w / 2 + m)] = ER_MASK
        return e
    cond = lambda X, Z: (X < w / 2) & (Z > h) & (Z < zt)
    return xe, ze, eps, cond

def series(builder, label):
    res = []
    for k, (h0, ratio, hmax) in enumerate([(4e-3, 1.3, 0.08), (2e-3, 1.2, 0.04), (1e-3, 1.12, 0.02), (5e-4, 1.08, 0.01)]):
        t0 = time.time(); xe, ze, eps, cond = builder(h0, ratio, hmax)[:4]
        r = line(xe, ze, eps, cond); res.append(r)
        print('  %-30s h0=%.0e N=%7d  Z0=%8.4f td=%7.4f eeff=%.4f (%.1fs)' % (label, h0, (len(xe) - 1) * (len(ze) - 1), r['Z0'], r['td'], r['eeff'], time.time() - t0), flush=True)
    z = [r['Z0'] for r in res]
    # Richardson assuming the h0 halving with first order (corner singularity) -> conservative bracket
    print('  %-30s last-step change %.3f %%, Richardson(p=1) %.3f' % (label, 100 * (z[-1] - z[-2]) / z[-2], 2 * z[-1] - z[-2]))
    return res[-1]

# --- closed forms -----------------------------------------------------------
def wheeler_strip(w, b, t, er):
    """Wheeler thick centred stripline (Wadell 3.5.x), ~0.5 % accurate."""
    x = t / b; m = 2 / (1 + 2 * x / (3 * (1 - x)))
    dw = x / (np.pi * (1 - x)) * (1 - 0.5 * np.log((x / (2 - x)) ** 2 + (0.0796 * x / (w / b + 1.1 * x)) ** m))
    mm = w / (b - t) + dw
    return 30 / np.sqrt(er) * np.log(1 + 4 / (np.pi * mm) * (8 / (np.pi * mm) + np.sqrt((8 / (np.pi * mm)) ** 2 + 6.27)))

def offset_strip(w, h1, h2, t, er):
    """Asymmetric stripline as the parallel combination of two centred striplines (Wadell/Gunston)."""
    z1 = wheeler_strip(w, 2 * h1 + t, t, er); z2 = wheeler_strip(w, 2 * h2 + t, t, er)
    return 2 * z1 * z2 / (z1 + z2)

def ipc_offset(w, h1, h2, t, er):
    return 80 / np.sqrt(er) * np.log(1.9 * (2 * h1 + t) / (0.8 * w + t)) * (1 - h1 / (4 * (h1 + t + h2)))

def hj_thick(w, h, t, er):
    """Hammerstad-Jensen with the thickness correction (uncoated)."""
    def z0_ee(u, er):
        f = 6 + (2 * np.pi - 6) * np.exp(-(30.666 / u) ** 0.7528)
        z01 = 60 * np.log(f / u + np.sqrt(1 + (2 / u) ** 2))
        a = 1 + np.log((u ** 4 + (u / 52) ** 2) / (u ** 4 + 0.432)) / 49 + np.log(1 + (u / 18.1) ** 3) / 18.7
        b = 0.564 * ((er - 0.9) / (er + 3)) ** 0.053
        ee = (er + 1) / 2 + (er - 1) / 2 * (1 + 10 / u) ** (-a * b)
        return z01, ee
    u = w / h; tn = t / h
    du1 = tn / np.pi * np.log(1 + 4 * np.e / (tn * (1 / np.tanh(np.sqrt(6.517 * u))) ** 2))
    dur = 0.5 * (1 + 1 / np.cosh(np.sqrt(er - 1))) * du1
    u1, ur = u + du1, u + dur
    z1, _ = z0_ee(u1, 1.0); zr, _ = z0_ee(ur, 1.0); _, eer = z0_ee(ur, er)
    ee = eer * (z1 / zr) ** 2
    return zr / np.sqrt(eer), ee

if __name__ == '__main__':
    w = 0.125
    print('== L3/L4 stripline w=0.125 (fieldsolve 49.08 ohm, 7.133 ps/mm)')
    r = series(lambda a, b, c: strip_geom(w, a, b, c), 'FV L3 0.125')
    h1, h2 = CORE, CORE + T_IN + MID   # near and far dielectric distances (trace faces to planes)
    for er, lab in [(ER_CORE, 'er=4.6'), (ER_MID, 'er=4.523'), ((ER_CORE + ER_MID) / 2, 'er=avg')]:
        print('  Wheeler offset (%s): %.3f ohm, td %.3f ps/mm ; IPC-2141: %.2f' % (lab, offset_strip(w, h1, h2, T_IN, er), 1e9 * np.sqrt(er) / 299792458.0, ipc_offset(w, h1, h2, T_IN, er)))
    print('== Microstrip, mask variants')
    for w, ref in [(0.0762, '63.61 / 6.210'), (0.125, '53.18 / 6.214')]:
        print('-- w=%.4f (fieldsolve %s)' % (w, ref))
        for mk in ('none', 'planar', 'conformal'):
            series(lambda a, b, c, mk=mk: ms_geom(w, a, b, c, mask=mk), 'FV mask=%s' % mk)
        z, ee = hj_thick(w, PP, T_OUT, ER_PP)
        print('  HJ thick uncoated: Z0 %.3f eeff %.4f td %.4f' % (z, ee, 1e9 * np.sqrt(ee) / 299792458.0))
