"""Independent 2D solver (written from scratch, does NOT import fieldsolve).

Cell-centred finite volumes (phi at cell centres, not nodes), half-domain with a symmetry wall at x = 0, eps per cell
from an arbitrary region function, harmonic face conductances, conductors as fixed cells whose surface is the cell
face. Charge from Gauss's law: flux leaving the trace cells (not the energy). Z0 = 1/(c sqrt(C C0)).
Geometry is given as explicit rectangles so the trace position is independent of fieldsolve's slab bookkeeping.
"""
import numpy as np, scipy.sparse as sp, scipy.sparse.linalg as spl
EPS0 = 8.854187817e-12; C0L = 299792458.0

def grid(breaks, h0, ratio, hmax):
    """cell edges hitting every break, refined to h0 at each break with growth 'ratio' up to hmax."""
    breaks = sorted(set(breaks)); out = [breaks[0]]
    for a, b in zip(breaks[:-1], breaks[1:]):
        L = b - a
        # symmetric geometric grading from both ends
        hs = []; h = h0; s = 0.0
        while 2 * (s + h) < L and h < hmax:
            hs.append(h); s += h; h *= ratio
        mid = L - 2 * s
        nm = max(1, int(np.ceil(mid / hmax)))
        seq = hs + [mid / nm] * nm + hs[::-1]
        e = a + np.cumsum(seq); e[-1] = b
        out.extend(e.tolist())
    return np.array(out)

def solve(xe, ze, eps_fn, cond_fn, plane_bot=True, top='plane'):
    """xe: cell edges in x from 0 (symmetry) outward; ze: cell edges in z. eps_fn(xc,zc)->eps array;
    cond_fn(xc,zc)->bool array (trace cells). Bottom boundary is a ground plane, top boundary phi=0 (plane or far)."""
    xc = 0.5 * (xe[1:] + xe[:-1]); zc = 0.5 * (ze[1:] + ze[:-1])
    dx = np.diff(xe); dz = np.diff(ze); nx, nz = len(xc), len(zc)
    X, Z = np.meshgrid(xc, zc, indexing='ij')
    eps = eps_fn(X, Z); cond = cond_fn(X, Z)
    idx = np.arange(nx * nz).reshape(nx, nz)
    rows, cols, vals = [], [], []
    diag = np.zeros(nx * nz); rhs = np.zeros(nx * nz)
    qedges = []   # (free cell, G) for faces between trace and free cells
    # x faces
    for (a, b, Gf) in [(idx[:-1, :], idx[1:, :], None)]:
        pass
    dxa = dx[:, None] * np.ones((1, nz)); dza = np.ones((nx, 1)) * dz[None, :]
    def add_pair(P, Q, G):
        P = P.ravel(); Q = Q.ravel(); G = G.ravel()
        cp = cond.ravel()[P]; cq = cond.ravel()[Q]
        ff = ~cp & ~cq
        rows.extend([P[ff], Q[ff]]); cols.extend([Q[ff], P[ff]]); vals.extend([-G[ff], -G[ff]])
        np.add.at(diag, P[ff], G[ff]); np.add.at(diag, Q[ff], G[ff])
        # trace cell P, free Q: conductor surface at the face, use only Q half-cell
        return cp, cq
    # x-direction faces between (i,j) and (i+1,j)
    P = idx[:-1, :]; Q = idx[1:, :]
    eP, eQ = eps[:-1, :], eps[1:, :]; hP, hQ = dxa[:-1, :] / 2, dxa[1:, :] / 2; A = dza[:-1, :]
    for Pa, Qa, ea, eb, ha, hb, Aa in [(P, Q, eP, eQ, hP, hQ, A)]:
        Gfull = Aa / (ha / ea + hb / eb)
        cp = cond[:-1, :]; cq = cond[1:, :]
        ff = ~cp & ~cq
        rows.extend([Pa[ff], Qa[ff]]); cols.extend([Qa[ff], Pa[ff]]); vals.extend([-Gfull[ff], -Gfull[ff]])
        np.add.at(diag, Pa[ff], Gfull[ff]); np.add.at(diag, Qa[ff], Gfull[ff])
        m = cp & ~cq; G1 = (Aa / (hb / eb))[m]; np.add.at(diag, Qa[m], G1); np.add.at(rhs, Qa[m], G1); qedges.append((Qa[m], G1))
        m = cq & ~cp; G1 = (Aa / (ha / ea))[m]; np.add.at(diag, Pa[m], G1); np.add.at(rhs, Pa[m], G1); qedges.append((Pa[m], G1))
    # z-direction faces
    P = idx[:, :-1]; Q = idx[:, 1:]
    eP, eQ = eps[:, :-1], eps[:, 1:]; hP, hQ = dza[:, :-1] / 2, dza[:, 1:] / 2; A = dxa[:, :-1]
    Gfull = A / (hP / eP + hQ / eQ)
    cp = cond[:, :-1]; cq = cond[:, 1:]; ff = ~cp & ~cq
    rows.extend([P[ff], Q[ff]]); cols.extend([Q[ff], P[ff]]); vals.extend([-Gfull[ff], -Gfull[ff]])
    np.add.at(diag, P[ff], Gfull[ff]); np.add.at(diag, Q[ff], Gfull[ff])
    m = cp & ~cq; G1 = (A / (hQ / eQ))[m]; np.add.at(diag, Q[m], G1); np.add.at(rhs, Q[m], G1); qedges.append((Q[m], G1))
    m = cq & ~cp; G1 = (A / (hP / eP))[m]; np.add.at(diag, P[m], G1); np.add.at(rhs, P[m], G1); qedges.append((P[m], G1))
    # Dirichlet phi=0 at bottom (z=ze[0]) and top (z=ze[-1]) faces; x=0 symmetry and x=xmax: Neumann
    Gb = dx / (dz[0] / 2 / eps[:, 0]); np.add.at(diag, idx[:, 0], Gb * ~cond[:, 0])
    Gt = dx / (dz[-1] / 2 / eps[:, -1]); np.add.at(diag, idx[:, -1], Gt * ~cond[:, -1])
    free = ~cond.ravel()
    Rr = np.concatenate(rows + [np.arange(nx * nz)]); Cc = np.concatenate(cols + [np.arange(nx * nz)]); Vv = np.concatenate(vals + [diag])
    M = sp.csr_matrix((Vv, (Rr, Cc)), shape=(nx * nz, nx * nz))
    fi = np.where(free)[0]
    Mf = M[fi][:, fi].tocsc()
    phi = np.zeros(nx * nz); phi[cond.ravel()] = 1.0
    phi[fi] = spl.spsolve(Mf, rhs[fi])
    Q = 0.0
    for c, G in qedges:
        Q += np.sum(G * (1.0 - phi[c]))
    return 2 * EPS0 * Q   # x2 for the mirrored half; F/m (lengths in mm cancel in 2D)

def line(xe, ze, eps_fn, cond_fn):
    C = solve(xe, ze, eps_fn, cond_fn)
    Cv = solve(xe, ze, lambda X, Z: np.ones_like(X), cond_fn)
    return dict(Z0=1 / (C0L * np.sqrt(C * Cv)), td=1e9 * np.sqrt(C / Cv) / C0L, eeff=C / Cv, C=C)
