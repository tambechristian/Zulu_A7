"""2D electrostatic field solver for a single trace over/between reference planes (Zulu_a7_no_pmod Rev 2 SI cross-check).

Finite differences on a non-uniform tensor grid: div(eps grad phi) = 0, phi = 1 on the trace, 0 on the reference planes
(and on the far boundary of an open microstrip), zero normal flux on the side walls. Capacitance per unit length from
the field energy, C = eps0 * sum_edges G_edge * (dphi)^2. Solving once with the real dielectrics (C) and once with
vacuum everywhere (C0) gives Z0 = 1 / (c * sqrt(C * C0)) and v = c * sqrt(C0 / C).

Units: mm. Stack is passed as a list of horizontal slabs from z = 0 upward: (thickness, eps_r). Conductors:
- plane_bottom / plane_top: True puts a ground plane on that boundary (z = 0 or z = top); False = open boundary there,
  modelled as phi = 0 at a far distance (pad the stack with a thick air slab).
- trace: (z_bottom, thickness, width), centred at x = 0.
"""
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spl

EPS0 = 8.854187817e-12      # F/m
C_LIGHT = 299792458.0       # m/s
GROW = 1.10                 # geometric growth of the grid spacing away from edges
COARSE_DIV = 16.0           # coarsest spacing = max(w, H) / COARSE_DIV


def _axis(breaks, fine, coarse, grow=1.25):
    """Grid coordinates that hit every break point, spacing 'fine' at breaks growing geometrically to 'coarse'."""
    breaks = sorted(set(round(b, 9) for b in breaks))
    pts = [breaks[0]]
    for a, b in zip(breaks[:-1], breaks[1:]):
        L = b - a
        # grow from both ends towards the middle
        left, right = [a], [b]
        h = fine
        while True:
            nl, nr = left[-1] + h, right[-1] - h
            if nl >= nr - 0.5 * h:
                break
            left.append(nl)
            right.append(nr)
            h = min(h * grow, coarse)
        seg = left + right[::-1]
        # clean: drop points too close
        seg = sorted(set(round(s, 9) for s in seg))
        cleaned = [seg[0]]
        for s in seg[1:]:
            if s - cleaned[-1] > fine * 0.3:
                cleaned.append(s)
        if cleaned[-1] != b:
            cleaned[-1] = b
        pts.extend(cleaned[1:])
    return np.array(pts)


def capacitance(slabs, trace, plane_bottom=True, plane_top=True, half_width=None, fine=None, vacuum=False):
    """Capacitance per metre (F/m) of the trace to the reference conductors."""
    zb, t, w = trace
    H = sum(s[0] for s in slabs)
    if half_width is None:
        half_width = max(10 * w, 8 * H if (plane_top and plane_bottom) else 6 * H, 1.5)
    if fine is None:
        fine = min(t / 4.0, w / 160.0)
    zbreaks = [0.0]
    acc = 0.0
    for th, _ in slabs:
        acc += th
        zbreaks.append(acc)
    zbreaks += [zb, zb + t]
    xbreaks = [-half_width, -w / 2, w / 2, half_width, 0.0]
    x = _axis(xbreaks, fine, coarse=max(w, H) / COARSE_DIV, grow=GROW)
    z = _axis(zbreaks, fine, coarse=max(w, H) / COARSE_DIV, grow=GROW)
    nx, nz = len(x), len(z)
    dx, dz = np.diff(x), np.diff(z)
    # permittivity per cell (cell i,j spans x[i]..x[i+1], z[j]..z[j+1])
    zc = 0.5 * (z[:-1] + z[1:])
    eps_z = np.ones(nz - 1)
    if not vacuum:
        acc = 0.0
        for th, er in slabs:
            eps_z[(zc >= acc) & (zc < acc + th)] = er
            acc += th
    eps = np.tile(eps_z, (nx - 1, 1))   # (nx-1, nz-1)
    idx = np.arange(nx * nz).reshape(nx, nz)
    fixed = np.zeros((nx, nz), bool)
    val = np.zeros((nx, nz))
    tr = (x[:, None] >= -w / 2 - 1e-12) & (x[:, None] <= w / 2 + 1e-12) & (z[None, :] >= zb - 1e-12) & (z[None, :] <= zb + t + 1e-12)
    fixed |= tr
    val[tr] = 1.0
    if plane_bottom or True:
        fixed[:, 0] = True      # bottom boundary is a plane or (open case) far phi = 0
    fixed[:, -1] = True
    rows, cols, data = [], [], []
    edges = []   # (n1, n2, G)
    # x-edges: between (i,j) and (i+1,j); adjacent cells (i, j-1) and (i, j)
    for i in range(nx - 1):
        for j in range(nz):
            e = 0.0
            if j > 0:
                e += eps[i, j - 1] * dz[j - 1] / 2
            if j < nz - 1:
                e += eps[i, j] * dz[j] / 2
            edges.append((idx[i, j], idx[i + 1, j], e / dx[i]))
    for i in range(nx):
        for j in range(nz - 1):
            e = 0.0
            if i > 0:
                e += eps[i - 1, j] * dx[i - 1] / 2
            if i < nx - 1:
                e += eps[i, j] * dx[i] / 2
            edges.append((idx[i, j], idx[i, j + 1], e / dz[j]))
    E = np.array(edges)
    n1, n2, G = E[:, 0].astype(int), E[:, 1].astype(int), E[:, 2]
    N = nx * nz
    A = sp.coo_matrix((np.concatenate([G, G, -G, -G]), (np.concatenate([n1, n2, n1, n2]), np.concatenate([n1, n2, n2, n1]))), shape=(N, N)).tocsr()
    fx = fixed.ravel()
    vf = val.ravel()
    free = ~fx
    rhs = -A[free][:, fx] @ vf[fx]
    phi = vf.copy()
    phi[free] = spl.spsolve(A[free][:, free].tocsc(), rhs)
    C = EPS0 * np.sum(G * (phi[n1] - phi[n2]) ** 2)
    return C


def line_params(slabs, trace, plane_bottom=True, plane_top=True, **kw):
    C = capacitance(slabs, trace, plane_bottom, plane_top, **kw)
    C0 = capacitance(slabs, trace, plane_bottom, plane_top, vacuum=True, **kw)
    Z0 = 1.0 / (C_LIGHT * np.sqrt(C * C0))
    v = C_LIGHT * np.sqrt(C0 / C)
    return {'Z0': Z0, 'v_m_per_s': v, 'td_ps_per_mm': 1e12 * 1e-3 / v, 'eps_eff': C / C0, 'C_pF_per_mm': C * 1e12 * 1e-3,
            'L_nH_per_mm': Z0 / v * 1e9 * 1e-3}


# ---- Zulu_a7_no_pmod Rev 2 stack (Board6 V9_STACK, mm) ----
CU_OUT, CU_IN = 0.035, 0.0152
PP, ER_PP = 0.09939, 4.1
CORE, ER_CORE = 0.1, 4.6
MID, ER_MID = 1.1208, 4.523
MASK, ER_MASK = 0.03048, 3.8
AIR = 3.0


# ---- the construction PCBWay builds (Rev_2/fabrication/*_FAB_NOTES.txt 'STACK'; Dk @1 GHz from docs/hdi_fab_facts.md:
# SY 1080 RC69 % Dk 3.99, 3313 ~ 2313 RC58 % Dk 4.27, core 4.5). L3/L4 sit on the core, embedded in 1080 resin. ----
FAB = {'pp_out': 0.1015, 'er_pp_out': 4.27, 'pp_in_top': 0.0713, 'pp_in_bot': 0.0711, 'er_pp_in': 3.99,
       'core': 1.065, 'er_core': 4.5, 'cu_out': 0.035, 'cu_plane': 0.018, 'cu_sig': 0.0152}


def layer_geometry(layer, w, stack='fab'):
    """(slabs, trace, plane_bottom, plane_top) for a trace of width w. stack 'fab' = PCBWay construction (default),
    'pcbdoc' = the stack stored in the PcbDoc (Board6 V9_STACK)."""
    if stack == 'fab':
        f = FAB
        if layer in ('Top Layer', 'Bottom Layer'):
            slabs = [(f['pp_out'], f['er_pp_out']), (f['cu_out'] + MASK, ER_MASK), (AIR, 1.0)]
            return slabs, (f['pp_out'], f['cu_out'], w), True, False
        if layer in ('L3-SIG', 'L4-SIG'):
            # z from the L5 plane up to the L2 plane: 1080 (L4-L5), L4 copper (resin), core, L3 copper (resin), 1080
            slabs = [(f['pp_in_bot'], f['er_pp_in']), (f['cu_sig'], f['er_pp_in']), (f['core'], f['er_core']),
                     (f['cu_sig'], f['er_pp_in']), (f['pp_in_top'], f['er_pp_in'])]
            if layer == 'L3-SIG':
                zb = f['pp_in_bot'] + f['cu_sig'] + f['core']
            else:
                zb = f['pp_in_bot']
            return slabs, (zb, f['cu_sig'], w), True, True
        raise ValueError(layer)
    if layer in ('Top Layer', 'Bottom Layer'):
        # microstrip over the adjacent plane (L2 or L5), solder mask modelled as a planar slab from the dielectric
        # surface up to trace top + mask thickness (fills between conductors: Z0 ~3 % low vs a conformal coat)
        slabs = [(PP, ER_PP), (CU_OUT + MASK, ER_MASK), (AIR, 1.0)]
        return slabs, (PP, CU_OUT, w), True, False
    if layer == 'L3-SIG':
        slabs = [(CORE, ER_CORE), (CU_IN, ER_MID), (MID, ER_MID), (CU_IN, ER_MID), (CORE, ER_CORE)]
        zb = CORE + CU_IN + MID
        return slabs, (zb, CU_IN, w), True, True
    if layer == 'L4-SIG':
        slabs = [(CORE, ER_CORE), (CU_IN, ER_MID), (MID, ER_MID), (CU_IN, ER_MID), (CORE, ER_CORE)]
        zb = CORE
        return slabs, (zb, CU_IN, w), True, True
    raise ValueError(layer)


def stack_z(stack='fab'):
    """Top-of-copper z (mm, from the top surface) and copper thickness per layer, for via heights."""
    if stack == 'fab':
        f = FAB
        cu = {'Top Layer': f['cu_out'], 'L2-GND': f['cu_plane'], 'L3-SIG': f['cu_sig'], 'L4-SIG': f['cu_sig'],
              'L5-VCC3V3': f['cu_plane'], 'Bottom Layer': f['cu_out']}
        gaps = [f['pp_out'], f['pp_in_top'], f['core'], f['pp_in_bot'], f['pp_out']]
    else:
        cu = {'Top Layer': CU_OUT, 'L2-GND': CU_IN, 'L3-SIG': CU_IN, 'L4-SIG': CU_IN, 'L5-VCC3V3': CU_IN,
              'Bottom Layer': CU_OUT}
        gaps = [PP, CORE, MID, CORE, PP]
    order = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
    z, acc = {}, 0.0
    for k, L in enumerate(order):
        z[L] = acc
        acc += cu[L] + (gaps[k] if k < len(gaps) else 0.0)
    return z, cu


def zulu_line(layer, w, stack='fab', **kw):
    slabs, trace, pb, pt = layer_geometry(layer, w, stack)
    return line_params(slabs, trace, pb, pt, **kw)


if __name__ == '__main__':
    import json, sys
    out = {}
    for stack in ('fab', 'pcbdoc'):
        for layer, w in [('L3-SIG', 0.125), ('L4-SIG', 0.125), ('Top Layer', 0.0762), ('Bottom Layer', 0.125), ('Top Layer', 0.125)]:
            r = zulu_line(layer, w, stack)
            out['%s:%s@%.4f' % (stack, layer, w)] = r
            print('%-6s %-13s w=%.4f  Z0=%6.2f ohm  td=%5.2f ps/mm  eps_eff=%.3f' % (stack, layer, w, r['Z0'], r['td_ps_per_mm'], r['eps_eff']))
    json.dump(out, open('lines.json', 'w'), indent=1)
