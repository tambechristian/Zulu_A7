#!/usr/bin/env python
"""
stackup_impedance.py -- characteristic impedance of every routed trace width on the board, from the layer stack saved
in the PcbDoc (docs/stackup_impedance.md). Reads the file; changes nothing.

Stack: the authoritative V9_STACK_LAYERn rows of Board6/Data, parsed with tools/verify_stack.py's helpers (copper
thickness, dielectric heights and Dk, solder mask). Planes: the copper layers named in PLANE1NETNAME/PLANE2NETNAME
style -- here L2-GND and L5-VCC3V3, assumed solid. Every other copper layer is a signal layer; when solving one signal
layer, the other signal layers' copper levels are treated as resin (the adjacent prepreg's Dk), and so is the
solved layer's own copper level around the trace.

Cross-sections (a layer in the lower half is solved on the flipped stack, so Bottom mirrors Top and L4 mirrors L3):
  outer   trace on the outermost dielectric, conformal solder mask over trace and laminate, air above; reference =
          nearest plane below.
  inner   trace on the face of the dielectric away from its nearest plane, embedded in prepreg; references = the
          nearest plane on each side (the far one across the core).

Solver: 2-D quasi-static finite differences on a graded grid (1.5 um at conductor edges), rectangular traces,
lossless. C comes from the discrete field energy; Z0 = 1 / (c0 sqrt(C C_air)), eps_eff = C / C_air. Differential
pairs: odd and even modes, Zdiff = 2 Zodd. The scheme converges from below: values are about 0.1-0.15 ohm low
(refining the edge cell to 0.8 um raises them about 0.05 ohm; an independent finite-volume solve agrees).

Usage:  python tools/stackup_impedance.py [path\\to\\zulu_a7.PcbDoc]      (prints markdown tables)
"""
import collections
import math
import os
import sys

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_stack as V                      # noqa: E402  (load / rows / mm / DEFAULT)

E0 = 8.8541878128e-12
C0 = 299792458.0
PLANES = {'L2-GND', 'L5-VCC3V3'}
DIFF_PAIRS = [('USB_D_P', 'USB_D_N', 'Top Layer')]
LAYER_ID = {1: 'Top Layer', 4: 'L2-GND', 2: 'L3-SIG', 3: 'L4-SIG', 5: 'L5-VCC3V3', 32: 'Bottom Layer'}


# ---------------------------------------------------------------- stack
def read_stack(path):
    """Rows from Top Solder to Bottom Solder: (kind, name, thickness_mm, dk, dieltype)."""
    d = V.load(path)
    v9 = V.rows(d, 'V9_STACK_LAYER', '_')
    out, on = [], False
    for i in sorted(v9):
        r = v9[i]
        name = r.get('NAME')
        if name == 'Top Solder':
            on = True
        if not on:
            continue
        if r.get('COPTHICK'):
            out.append(('cu', name, V.mm(r['COPTHICK']), None, None))
        elif r.get('DIELHEIGHT'):
            kind = 'mask' if 'Solder' in name else 'diel'
            out.append((kind, name, V.mm(r['DIELHEIGHT']), float(r['DIELCONST']), r.get('DIELTYPE')))
        if name == 'Bottom Solder':
            break
    assert out[0][0] == 'mask' and out[-1][0] == 'mask', 'stack must run from Top Solder to Bottom Solder'
    return out


def section(stack, layer):
    """Vertical description of the cross-section for a signal layer.
    Returns dict(kind, bands=[(y0, y1, eps)], yb, yt, top=Dirichlet-or-air, mask=(t, dk) or None)."""
    cu = [i for i, r in enumerate(stack) if r[0] == 'cu']
    k = [i for i in cu if stack[i][1] == layer][0]
    if cu.index(k) >= len(cu) / 2:                     # lower half: flip so the layer sits in the upper half
        stack = stack[::-1]
        k = len(stack) - 1 - k
    below = [i for i in range(k + 1, len(stack)) if stack[i][0] == 'cu' and stack[i][1] in PLANES]
    above = [i for i in range(0, k) if stack[i][0] == 'cu' and stack[i][1] in PLANES]
    lo = below[0]

    def fill_dk(i):                                    # resin around a signal copper level
        nb = [stack[j] for j in (i - 1, i + 1) if 0 <= j < len(stack) and stack[j][0] == 'diel']
        pp = [r for r in nb if r[4] == '2'] or nb
        return pp[0][3]

    bands, y = [], 0.0
    for i in range(lo - 1, k, -1):                     # from the plane's face up to the trace's copper level
        r = stack[i]
        t = r[2]
        dk = fill_dk(i) if r[0] == 'cu' else r[3]
        bands.append((y, y + t, dk))
        y += t
    yb, yt = y, y + stack[k][2]
    bands.append((yb, yt, fill_dk(k)))
    if above:                                          # inner: dielectric up to the plane above
        y = yt
        for i in range(k - 1, above[-1], -1):
            r = stack[i]
            t = r[2]
            bands.append((y, y + t, fill_dk(i) if r[0] == 'cu' else r[3]))
            y += t
        return dict(kind='inner', bands=bands, yb=yb, yt=yt, top=y, mask=None)
    m = stack[k - 1]
    assert m[0] == 'mask'
    return dict(kind='outer', bands=bands[:-1], yb=yb, yt=yt, top=None, mask=(m[2], m[3]))


# ---------------------------------------------------------------- solver
def graded(points, lo, hi, fine, coarse, ratio=1.15):
    pts = sorted(set([lo, hi] + [p for p in points if lo <= p <= hi]))
    out = [pts[0]]
    for a, b in zip(pts[:-1], pts[1:]):
        left, right, s = [a], [b], fine
        while True:
            xl, xr = left[-1] + s, right[-1] - s
            if xl >= xr - 1e-12:
                break
            left.append(xl)
            right.append(xr)
            s = min(s * ratio, coarse)
        if len(left) > 1 and right[-1] - left[-1] < fine * 0.3:   # merge a sliver where the two ramps meet
            mid = (left.pop() + right.pop()) / 2
            left.append(mid)
        seg = left + right[::-1]
        out += seg[1:]
    return np.array(out)


def energy(sec, traces, fine=0.0015, dielectric=True):
    """traces: [(x_centre, width, volts)]. Returns sum(a dphi^2) * e0, i.e. 2 x field energy per metre."""
    yb, yt = sec['yb'], sec['yt']
    edges = [x - w / 2 for x, w, v in traces] + [x + w / 2 for x, w, v in traces]
    X = max(3.0, 8 * (max(edges) - min(edges)) + 2.0)
    keyx = list(edges)
    keyy = [b[0] for b in sec['bands']] + [b[1] for b in sec['bands']] + [yb, yt]
    if sec['kind'] == 'outer':
        mt, mdk = sec['mask']
        keyx += [e - mt for e in edges] + [e + mt for e in edges]
        keyy += [yb + mt, yt + mt]
        Ytop = 2.5
    else:
        Ytop = sec['top']
    x = graded(keyx, -X, X, fine, 0.08)
    y = graded(keyy, 0.0, Ytop, fine, 0.08 if sec['kind'] == 'outer' else 0.04)
    nx, ny = len(x), len(y)
    dx, dy = np.diff(x), np.diff(y)
    XC, YC = np.meshgrid((x[:-1] + x[1:]) / 2, (y[:-1] + y[1:]) / 2, indexing='ij')
    eps = np.ones((nx - 1, ny - 1))
    if dielectric:
        for y0, y1, dk in sec['bands']:
            eps[(YC >= y0) & (YC < y1)] = dk
        if sec['kind'] == 'outer':
            mt, mdk = sec['mask']
            m = (YC >= yb) & (YC < yb + mt)
            for xc, w, v in traces:
                m |= (XC > xc - w / 2 - mt) & (XC < xc + w / 2 + mt) & (YC >= yb) & (YC < yt + mt)
            eps[m] = mdk
    XN, YN = np.meshgrid(x, y, indexing='ij')
    fixed = np.zeros((nx, ny), bool)
    val = np.zeros((nx, ny))
    fixed[:, 0] = fixed[:, -1] = fixed[0, :] = fixed[-1, :] = True
    for xc, w, v in traces:
        m = (XN >= xc - w / 2 - 1e-9) & (XN <= xc + w / 2 + 1e-9) & (YN >= yb - 1e-9) & (YN <= yt + 1e-9)
        fixed[m] = True
        val[m] = v
    ax = np.zeros((nx - 1, ny))
    ax[:, 1:] += eps * dy[None, :] / 2
    ax[:, :-1] += eps * dy[None, :] / 2
    ax /= dx[:, None]
    ay = np.zeros((nx, ny - 1))
    ay[1:, :] += eps * dx[:, None] / 2
    ay[:-1, :] += eps * dx[:, None] / 2
    ay /= dy[None, :]
    diag = np.zeros((nx, ny))
    diag[:-1, :] += ax
    diag[1:, :] += ax
    diag[:, :-1] += ay
    diag[:, 1:] += ay
    free = ~fixed
    idx = -np.ones((nx, ny), int)
    idx[free] = np.arange(free.sum())
    fi = np.argwhere(free)
    k = idx[free]
    rows, cols, data = [k], [k], [diag[free]]
    rhs = np.zeros(len(k))
    for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ii, jj = fi[:, 0] + di, fi[:, 1] + dj
        a = (ax[fi[:, 0], fi[:, 1]] if di == 1 else ax[ii, jj] if di == -1 else
             ay[fi[:, 0], fi[:, 1]] if dj == 1 else ay[ii, jj])
        nb = free[ii, jj]
        rows.append(k[nb]); cols.append(idx[ii[nb], jj[nb]]); data.append(-a[nb])
        np.add.at(rhs, k[~nb], a[~nb] * val[ii[~nb], jj[~nb]])
    A = sp.csc_matrix((np.concatenate(data), (np.concatenate(rows), np.concatenate(cols))), shape=(len(k), len(k)))
    phi = val.copy()
    phi[free] = spla.spsolve(A, rhs)
    W = (ax * (phi[1:, :] - phi[:-1, :]) ** 2).sum() + (ay * (phi[:, 1:] - phi[:, :-1]) ** 2).sum()
    return W * E0


def single(sec, w):
    c = energy(sec, [(0.0, w, 1.0)])
    ca = energy(sec, [(0.0, w, 1.0)], dielectric=False)
    return 1 / (C0 * math.sqrt(c * ca)), c / ca


def pair(sec, w, s):
    p = (w + s) / 2
    odd = [(-p, w, 1.0), (p, w, -1.0)]
    even = [(-p, w, 1.0), (p, w, 1.0)]
    co, coa = energy(sec, odd) / 2, energy(sec, odd, dielectric=False) / 2
    ce, cea = energy(sec, even) / 2, energy(sec, even, dielectric=False) / 2
    zo, ze = 1 / (C0 * math.sqrt(co * coa)), 1 / (C0 * math.sqrt(ce * cea))
    return 2 * zo, zo, ze, co / coa


# ---------------------------------------------------------------- board inventory
def inventory(path):
    from altium_monkey import AltiumPcbDoc
    MM = 0.0254
    d = AltiumPcbDoc.from_file(path)
    nets = [n.name for n in d.nets]
    cls = collections.defaultdict(list)
    for c in d.net_classes:
        if int(c.kind) != 0:
            continue                                   # net classes only (not component, pad or layer classes)
        for m in (getattr(c, 'members', None) or []):
            cls[m].append(c.name)
    inv = collections.defaultdict(lambda: {'len': 0.0, 'nets': collections.Counter()})
    segs = collections.defaultdict(list)
    for t in d.tracks:
        name = LAYER_ID.get(t.layer)
        if name is None or name in PLANES:
            continue
        if t.polygon_index is not None and t.polygon_index not in (-1, 65535):
            continue
        w = round(t.width_mils * MM, 4)
        a, b = (t.start_x_mils * MM, t.start_y_mils * MM), (t.end_x_mils * MM, t.end_y_mils * MM)
        n = nets[t.net_index] if t.net_index is not None and 0 <= t.net_index < len(nets) else '-'
        e = inv[(name, w)]
        e['len'] += math.dist(a, b)
        e['nets'][n] += math.dist(a, b)
        segs[(name, n)].append((a, b, w))
    return inv, cls, segs


def coupled_gap(segs, layer, p, n, w):
    """Most common edge-to-edge gap between the two nets' centrelines, sampled along p, and the length at it."""
    def ps(q, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = dx * dx + dy * dy
        t = 0 if L == 0 else max(0, min(1, ((q[0] - a[0]) * dx + (q[1] - a[1]) * dy) / L))
        return math.hypot(q[0] - a[0] - t * dx, q[1] - a[1] - t * dy)
    hist = collections.Counter()
    for a, b, _ in segs[(layer, p)]:
        L = math.dist(a, b)
        m = max(1, int(L / 0.02))
        for i in range(m):
            q = (a[0] + (b[0] - a[0]) * (i + .5) / m, a[1] + (b[1] - a[1]) * (i + .5) / m)
            g = min(ps(q, c, e) for c, e, _ in segs[(layer, n)]) - w
            hist[round(g, 3)] += L / m
    g, L = hist.most_common(1)[0]
    return g, L, sum(math.dist(a, b) for a, b, _ in segs[(layer, p)]), sum(math.dist(a, b) for a, b, _ in segs[(layer, n)])


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else V.DEFAULT
    stack = read_stack(path)
    print('## Stack (V9 rows of %s)\n' % os.path.basename(path))
    print('| Row | Thickness (mm) | Dk |\n|---|---:|---:|')
    for kind, name, t, dk, dt in stack:
        print('| %s | %.4f | %s |' % (name, t, '%.2f' % dk if dk else '-'))
    inv, cls, segs = inventory(path)
    secs, cache = {}, {}
    order = ['Top Layer', 'L3-SIG', 'L4-SIG', 'Bottom Layer']
    print('\n## Every routed width\n')
    print('| Layer | Width (mm) | Z0 (ohm) | eps_eff | Delay (ps/mm) | Length (mm) | Net classes (by length) |')
    print('|---|---:|---:|---:|---:|---:|---|')
    for layer in order:
        secs[layer] = section(stack, layer)
        for (lname, w), e in sorted(inv.items()):
            if lname != layer:
                continue
            s = secs[layer]
            key = (s['kind'], tuple(s['bands']), s['yb'], s['yt'], s['top'], s['mask'], w)
            if key not in cache:
                cache[key] = single(secs[layer], w)
            z, ee = cache[key]
            cl = collections.Counter()
            for n, L in e['nets'].items():
                for c in cls.get(n, ['(no class)']):
                    cl[c] += L
            print('| %s | %.4f | %.1f | %.3f | %.2f | %.1f | %s |' % (
                layer, w, z, ee, math.sqrt(ee) * 1e9 / C0, e['len'], ', '.join(c for c, _ in cl.most_common(3))))
    print('\n## Differential pairs\n')
    for p, n, layer in DIFF_PAIRS:
        ws = {round(w, 4) for a, b, w in segs[(layer, p)] + segs[(layer, n)]}
        assert len(ws) == 1, ws
        w = ws.pop()
        g, Lc, Lp, Ln = coupled_gap(segs, layer, p, n, w)
        zd, zo, ze, ee = pair(secs[layer], w, g)
        print('%s/%s on %s: width %.3f, gap %.3f mm (coupled %.2f of %.2f / %.2f mm): Zdiff %.1f, Zodd %.1f, '
              'Zeven %.1f, Zcommon %.1f ohm, odd-mode eps_eff %.3f, %.2f ps/mm'
              % (p, n, layer, w, g, Lc, Lp, Ln, zd, zo, ze, ze / 2, ee, math.sqrt(ee) * 1e9 / C0))
    return 0


if __name__ == '__main__':
    sys.exit(main())
