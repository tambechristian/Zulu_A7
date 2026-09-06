"""Reusable pad/smd obstacle model matching check_board.py's exact 'cop'
(copper-obstacle) construction (parsing <smd>/<pad> elements per package,
applying element rotation/mirror via rp(), roundness-adjusted rectangle math,
THT restring-radius logic), plus via_vs_pad_ok() and wire_vs_pad_ok() helpers
matching check_board.py's exact clearance formulas. Read-only w.r.t.
zulu_a7.brd; import and call build_cop(board_text). Used by
board_clearance_check.py and any future routing work on this board.
"""
import re, math


def _mm(v):
    v = v.strip()
    if v.endswith("mm"):
        return float(v[:-2])
    if v.endswith("mil"):
        return float(v[:-3]) * 0.0254
    if v.endswith("in") or v.endswith('"'):
        return float(v.rstrip('in"')) * 25.4
    return float(v)


def rp(x, y, rot):
    r = re.sub(r"^M", "", rot)
    x, y = {"R0": (x, y), "R90": (-y, x), "R180": (-x, -y), "R270": (y, -x)}[r]
    return (-x, y) if rot.startswith("M") else (x, y)


def d_rect(a, c, px, py, hx, hy, n=64):
    best = 1e9
    for k in range(n + 1):
        t = k / float(n)
        qx, qy = a[0] + (c[0] - a[0]) * t, a[1] + (c[1] - a[1]) * t
        d = math.hypot(max(abs(qx - px) - hx, 0.0), max(abs(qy - py) - hy, 0.0))
        if d < best:
            best = d
    return best


def build_cop(b):
    """Return (cop, cv, cp, cw) matching check_board.py semantics.

    cop entries: (net, px, py, r, side, hx, hy, cr, ri)
    """
    par = lambda k: _mm((re.search(r'<param name="%s" value="([^"]+)"/>' % k, b)
                         or [None, "0"])[1])
    cw, cp = par("mdWireWire"), par("mdWirePad")
    cv = max(par("mdSmdVia"), cw)
    RVPADI = _mm((re.search(r"<param name=\"rvPadInner\" value=\"([^\"]+)\"/>", b) or [None, "0.25"])[1])
    RLMINPADI = _mm((re.search(r"<param name=\"rlMinPadInner\" value=\"([^\"]+)\"/>", b) or [None, "0.1"])[1])
    RLMAXPADI = _mm((re.search(r"<param name=\"rlMaxPadInner\" value=\"([^\"]+)\"/>", b) or [None, "0.5"])[1])

    el = {m.group(1): (m.group(2), m.group(3)) for m in
          re.finditer(r'<element name="([^"]+)" library="([^"]+)" package="([^"]+)"', b)}
    epos = {m.group(1): (float(m.group(2)), float(m.group(3)),
                         (re.search(r'rot="(M?R\d+)"', m.group(4)) or [None, "R0"])[1])
            for m in re.finditer(r'<element name="([^"]+)"[^>]*x="([-\d.]+)" y="([-\d.]+)"([^>]*)>', b)}
    bpkg = {}
    for m in re.finditer(r'<library name="([^"]+)">(.*?)</library>', b, re.S):
        for p in re.finditer(
            r'<package name="([^"]+)"[^>]*>(.*?)</package>', m.group(2), re.S
        ):
            bpkg[(m.group(1), p.group(1))] = p.group(2)

    bsig = {m.group(1): m.group(2) for m in
            re.finditer(r'<signal name="([^"]+)"[^>]*>(.*?)</signal>', b, re.S)}
    bcon = {n: set(re.findall(r'<contactref element="([^"]+)" pad="([^"]+)"/>', v)) for n, v in bsig.items()}
    pnet = {(e, pd): n for n, cs in bcon.items() for e, pd in cs}

    cop = []
    for p, (lib, pkname) in el.items():
        body = bpkg.get((lib, pkname), "")
        if p not in epos:
            continue
        ox, oy, rot = epos[p]
        side = 16 if rot.startswith("M") else 1
        for mm in re.finditer(r'<smd ([^>]*)/>', body):
            at = mm.group(1)
            nmm = re.search(r'name="([^"]+)"', at)
            gx = re.search(r'\sx="([-\d.]+)"', at)
            gy = re.search(r'\sy="([-\d.]+)"', at)
            gdx = re.search(r'dx="([\d.]+)"', at)
            gdy = re.search(r'dy="([\d.]+)"', at)
            if not (nmm and gx and gy and gdx and gdy):
                continue
            x, y = float(gx.group(1)), float(gy.group(1))
            dx, dy = float(gdx.group(1)), float(gdy.group(1))
            rnd = re.search(r'roundness="([\d.]+)"', at)
            cr = (float(rnd.group(1)) / 100.0) * min(dx, dy) / 2.0 if rnd else 0.0
            a = rp(x, y, rot)
            hx, hy = ((dx / 2.0, dy / 2.0)
                      if rot.lstrip("M") not in ("R90", "R270")
                      else (dy / 2.0, dx / 2.0))
            cop.append((pnet.get((p, nmm.group(1))), ox + a[0], oy + a[1],
                        max(dx, dy) / 2.0, side,
                        max(hx - cr, 0.0), max(hy - cr, 0.0), cr, None))
        for mm in re.finditer(r'<pad name="([^"]+)" x="([-\d.]+)" y="([-\d.]+)"'
                              r'[^>]*drill="([\d.]+)"(?:[^>]*diameter="([\d.]+)")?', body):
            x, y, dr = float(mm.group(2)), float(mm.group(3)), float(mm.group(4))
            di = float(mm.group(5)) if mm.group(5) else dr + 0.5
            a = rp(x, y, rot)
            _rs = min(max(dr * RVPADI, RLMINPADI), RLMAXPADI)
            _ri = min(dr / 2.0 + _rs, di / 2.0)
            cop.append((pnet.get((p, mm.group(1))), ox + a[0], oy + a[1], di / 2.0, 0,
                        None, None, 0.0, _ri))
    return cop, cv, cp, cw


def via_vs_pad_ok(vx, vy, dia, cop, cv, exclude_net=None):
    """Return (ok, min_margin) for a NEW via at (vx,vy) with diameter dia."""
    minm = 1e9
    for onet, px, py, r, side, hx, hy, cr, ri in cop:
        if onet == exclude_net or onet is None or hx is None:
            continue
        dx = max(0.0, abs(vx - px) - hx)
        dy = max(0.0, abs(vy - py) - hy)
        d = math.hypot(dx, dy) - cr - dia / 2.0
        m = d - cv
        if m < minm:
            minm = m
    return minm >= -1e-9, minm


def wire_vs_pad_ok(a, c, ly, wd, cop, cp, exclude_net=None):
    """Return (ok, min_margin) for a NEW wire a-c on layer ly, width wd."""
    minm = 1e9
    for onet, px, py, r, side, hx, hy, cr, ri in cop:
        if onet == exclude_net or (side and side != ly):
            continue
        rr = ri if (ri is not None and ly not in (1, 16)) else r
        d = (d_rect(a, c, px, py, hx, hy) - cr if hx is not None
             else 1e9) - wd / 2.0
        if hx is None:
            # THT pad: circle check via point-to-segment distance (approx with d_rect n/a)
            # use straight point-seg distance to a circle of radius rr
            def d_pt(a, c, p):
                (ax, ay), (cx, cy), (px_, py_) = a, c, p
                dx, dy = cx - ax, cy - ay
                L = dx * dx + dy * dy
                t = 0.0 if L == 0 else max(0.0, min(1.0, ((px_ - ax) * dx + (py_ - ay) * dy) / L))
                return math.hypot(px_ - (ax + t * dx), py_ - (ay + t * dy))
            d = d_pt(a, c, (px, py)) - rr - wd / 2.0
        m = d - cp
        if m < minm:
            minm = m
    return minm >= -1e-9, minm
