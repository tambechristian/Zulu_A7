"""Axisymmetric (r,z) finite-difference capacitance of a signal via in the Zulu Rev 2 stack, to test Johnson's
1.41 er T D1/(D2-D1) used by bus_sim. Grounds: L2 and L5 planes (with antipads), an outer coaxial wall at radius R
(stand-in for the nearest return vias / plane continuity) and far air boundaries. Energy method, C = eps0 sum G dphi^2.
python viacap.py  -> table for through via 0.35/0.2 and buried L3-L4 0.27/0.15 at several R and antipads."""
import sys, math
import numpy as np, scipy.sparse as sp, scipy.sparse.linalg as spl
sys.path.insert(0, '../..')
import fieldsolve as F

EPS0 = 8.854187817e-12
# z downward from the top of Top copper (mm): (name, z0, z1, eps of the region when not copper)
Z = {}
z = 0.0
LAY = []
for name, t, er_fill, diel_t, diel_er in [('Top', 0.035, 3.8, 0.09939, 4.1), ('L2', 0.0152, 4.6, 0.1, 4.6), ('L3', 0.0152, 4.523, 1.1208, 4.523),
                                          ('L4', 0.0152, 4.523, 0.1, 4.6), ('L5', 0.0152, 4.6, 0.09939, 4.1), ('Bot', 0.035, 3.8, 0, 1)]:
    LAY.append((name, z, z + t, er_fill))
    Z[name] = (z, z + t)
    z += t
    if diel_t:
        LAY.append(('d' + name, z, z + diel_t, diel_er))
        z += diel_t
THK = z


def via_cap(span, pad, hole, antipad_r, R=1.5, air=1.0, nfp=False, mask=True, planes=True, uni=None, zneu=False, allpads=False):
    """span: (first, last) layer names; pad diameter; hole (barrel) diameter; antipad radius on L2/L5.
    nfp: non-functional pads on the inner signal layers inside the span."""
    zt, zb = Z[span[0]][0], Z[span[1]][1]
    rb, rp = hole / 2, pad / 2
    zbreaks = [-air, THK + air] + [l[1] for l in LAY] + [l[2] for l in LAY]
    rbreaks = [0.0, rb, rp, antipad_r, R]
    fine = 0.004
    r = F._axis(rbreaks, fine, coarse=0.04, grow=1.15)
    zz = F._axis(zbreaks, fine, coarse=0.04, grow=1.15)
    nr, nz = len(r), len(zz)
    zc = 0.5 * (zz[:-1] + zz[1:])
    rc = 0.5 * (r[:-1] + r[1:])
    eps = np.ones((nr - 1, nz - 1))
    for name, z0, z1, er in LAY:
        sel = (zc >= z0) & (zc < z1)
        eps[:, sel] = er
    if uni is not None:
        eps[:] = uni
    R2, Z2 = np.meshgrid(r, zz, indexing='ij')
    fixed = np.zeros((nr, nz), bool)
    val = np.zeros((nr, nz))
    tol = 1e-9
    # via conductor: barrel over the span, pads on the span's end layers (and inner signal layers if nfp)
    via = (R2 <= rb + tol) & (Z2 >= zt - tol) & (Z2 <= zb + tol)
    names = ['Top', 'L2', 'L3', 'L4', 'L5', 'Bot']
    i0, i1 = names.index(span[0]), names.index(span[1])
    for k in range(i0, i1 + 1):
        n = names[k]
        if n in (span[0], span[1]) or (nfp and n in ('L3', 'L4')) or n in ('L2', 'L5'):
            if n in ('L2', 'L5') and n not in span and not allpads:
                continue
            a, b = Z[n]
            via |= (R2 <= rp + tol) & (Z2 >= a - tol) & (Z2 <= b + tol)
    fixed |= via
    val[via] = 1.0
    gnd = np.zeros_like(fixed)
    for n in (('L2', 'L5') if planes else ()):
        if n in span:
            continue
        a, b = Z[n]
        gnd |= (R2 >= antipad_r - tol) & (Z2 >= a - tol) & (Z2 <= b + tol)
    gnd[-1, :] = True        # outer wall
    if not zneu:
        gnd[:, 0] = True
        gnd[:, -1] = True        # far air
    fixed |= gnd
    idx = np.arange(nr * nz).reshape(nr, nz)
    dr, dz = np.diff(r), np.diff(zz)
    # radial edges (i,j)-(i+1,j): area = 2 pi r_face * (half cells above/below) ; weight eps
    e_list = []
    epad = np.zeros((nr + 1, nz + 1))
    epad[1:-1, 1:-1] = eps
    # radial
    I, J = np.meshgrid(np.arange(nr - 1), np.arange(nz), indexing='ij')
    hz_lo = np.where(J > 0, np.concatenate([[0], dz])[J], 0)
    hz_hi = np.where(J < nz - 1, np.concatenate([dz, [0]])[J], 0)
    e_lo = epad[I + 1, J]       # cell (i, j-1)
    e_hi = epad[I + 1, J + 1]   # cell (i, j)
    G = 2 * np.pi * rc[I] * (e_lo * hz_lo / 2 + e_hi * hz_hi / 2) / dr[I]
    n1 = idx[I, J].ravel(); n2 = idx[I + 1, J].ravel(); g1 = G.ravel()
    # axial edges (i,j)-(i,j+1): area = annulus of half cells left/right
    I, J = np.meshgrid(np.arange(nr), np.arange(nz - 1), indexing='ij')
    r_lo = np.where(I > 0, np.concatenate([[0], rc])[I], 0.0)
    r_hi = np.where(I < nr - 1, np.concatenate([rc, [r[-1]]])[I], r[-1])
    a_lo = np.pi * (r[I] ** 2 - r_lo ** 2)
    a_hi = np.pi * (r_hi ** 2 - r[I] ** 2)
    e_l = epad[I, J + 1]        # cell (i-1, j)
    e_h = epad[I + 1, J + 1]    # cell (i, j)
    G2 = (e_l * a_lo + e_h * a_hi) / dz[J]
    n1 = np.concatenate([n1, idx[I, J].ravel()]); n2 = np.concatenate([n2, idx[I, J + 1].ravel()]); g = np.concatenate([g1, G2.ravel()])
    N = nr * nz
    A = sp.coo_matrix((np.concatenate([g, g, -g, -g]), (np.concatenate([n1, n2, n1, n2]), np.concatenate([n1, n2, n2, n1]))), shape=(N, N)).tocsr()
    fx = fixed.ravel(); vf = val.ravel(); free = ~fx
    phi = vf.copy()
    phi[free] = spl.spsolve(A[free][:, free].tocsc(), -A[free][:, fx] @ vf[fx])
    C = EPS0 * 1e-3 * np.sum(g * (phi[n1] - phi[n2]) ** 2)   # lengths in mm -> F
    return C


def johnson(h, D1, D2, er=4.45):
    return 1.41 * er * (h / 25.4) * D1 / (D2 - D1) * 1e-12


if __name__ == '__main__':
    # sanity: coax check (no planes, via through whole board, wall at R): C ~ 2 pi eps L / ln(R/a) in the dielectric part
    print('through via 0.35/0.20, Johnson (antipad 0.70): %.3f pF' % (johnson(1.65038, 0.35, 0.70) * 1e12))
    for R in (0.75, 1.0, 1.5, 2.5):
        for ap in (0.35,):
            for nfp in (False, True):
                c = via_cap(('Top', 'Bot'), 0.35, 0.20, ap, R=R, nfp=nfp)
                print('  R=%.2f antipad_r=%.3f nfp=%s  C=%.3f pF' % (R, ap, nfp, c * 1e12))
    print('buried L3-L4 0.27/0.15, Johnson: %.3f pF' % (johnson(1.1512, 0.27, 0.62) * 1e12))
    for R in (0.75, 1.5, 2.5):
        c = via_cap(('L3', 'L4'), 0.27, 0.15, 0.31, R=R)
        print('  R=%.2f C=%.3f pF' % (R, c * 1e12))
