"""Scratch helper (not owned long-term): verify candidate reroute polylines
against the 9 GND thermal vias under U2 EP, and against all OTHER nets'
copper on the same layer, using the same distance math as check_board.py.

Usage: edit CANDIDATES below, then `python tools/reroute_geom_check.py`.
It only reads zulu_a7.brd; it does not write anything.
"""
import re, math, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRD = os.path.join(ROOT, "zulu_a7.brd")
b = open(BRD, encoding="utf-8").read()

CW = 0.0762  # mdWireWire
CP = 0.0762  # mdWirePad (via counts as pad here)

# The 9 GND thermal vias under U2 EP
GND_VIAS = [(31.908, 11.008), (33.108, 11.008), (34.308, 11.008),
            (31.908, 12.208), (33.108, 12.208), (34.308, 12.208),
            (31.908, 13.408), (33.108, 13.408), (34.308, 13.408)]
VIA_DIA = 0.3


def d_pt(a, c, p):
    (ax, ay), (cx, cy), (px, py) = a, c, p
    dx, dy = cx - ax, cy - ay
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def d_seg(a, c, p, q):
    def cr(o, x, y):
        return (x[0] - o[0]) * (y[1] - o[1]) - (x[1] - o[1]) * (y[0] - o[0])
    if ((cr(p, q, a) > 0) != (cr(p, q, c) > 0)) and \
       ((cr(a, c, p) > 0) != (cr(a, c, q) > 0)):
        return 0.0
    return min(d_pt(a, c, p), d_pt(a, c, q), d_pt(p, q, a), d_pt(p, q, c))


def signal_block(name):
    m = re.search(r'<signal name="%s">(.*?)</signal>' % re.escape(name), b, re.S)
    return m.group(1) if m else ""


def other_layer_wires(layer, exclude_net):
    """All wires on `layer` belonging to any signal other than exclude_net."""
    out = []
    for m in re.finditer(r'<signal name="([^"]+)"[^>]*>(.*?)</signal>', b, re.S):
        nm, body = m.group(1), m.group(2)
        if nm == exclude_net:
            continue
        for w in re.finditer(
                r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" '
                r'y2="([-\d.]+)" width="([\d.]+)" layer="(%s)"/>' % layer, body):
            x1, y1, x2, y2, wd = map(float, w.groups()[:5])
            out.append((nm, (x1, y1), (x2, y2), wd))
    return out


def other_vias(exclude_net):
    out = []
    for m in re.finditer(r'<signal name="([^"]+)"[^>]*>(.*?)</signal>', b, re.S):
        nm, body = m.group(1), m.group(2)
        if nm == exclude_net:
            continue
        for v in re.finditer(r'<via x="([-\d.]+)" y="([-\d.]+)" extent="[^"]*" '
                              r'drill="[\d.]+" diameter="([\d.]+)"', body):
            x, y, dia = map(float, v.groups())
            out.append((nm, x, y, dia))
    return out


def check_path(net, layer, width, points, extra_note=""):
    """points: list of (x,y) forming the new polyline (inclusive of fixed ends)."""
    ok = True
    hw = width / 2.0
    # 1. vs the 9 GND thermal vias
    for i in range(len(points) - 1):
        a, c = points[i], points[i + 1]
        for (vx, vy) in GND_VIAS:
            d = d_pt(a, c, (vx, vy)) - VIA_DIA / 2.0 - hw
            if d < CP - 1e-6:
                print("  VIOLATION vs GND via (%.3f,%.3f): seg %s-%s d=%.4f needs %.4f %s"
                      % (vx, vy, a, c, d, CP, extra_note))
                ok = False
    # 2. vs all other nets' vias (any layer, since vias are copper on every layer)
    for (onm, vx, vy, dia) in other_vias(net):
        for i in range(len(points) - 1):
            a, c = points[i], points[i + 1]
            d = d_pt(a, c, (vx, vy)) - dia / 2.0 - hw
            if d < CP - 1e-6:
                print("  VIOLATION vs %s via (%.3f,%.3f): seg %s-%s d=%.4f needs %.4f"
                      % (onm, vx, vy, a, c, d, CP))
                ok = False
    # 3. vs other same-layer wires of foreign nets
    for (onm, oa, oc, owd) in other_layer_wires(layer, net):
        for i in range(len(points) - 1):
            a, c = points[i], points[i + 1]
            d = d_seg(a, c, oa, oc) - hw - owd / 2.0
            if d < CW - 1e-6:
                print("  VIOLATION vs %s wire L%s %s-%s: seg %s-%s d=%.4f needs %.4f"
                      % (onm, layer, oa, oc, a, c, d, CW))
                ok = False
    if ok:
        print("  OK: %s L%s path %s clears everything" % (net, layer, points))
    return ok


def quiet_check(net, layer, width, points):
    """Like check_path but returns True/False without printing."""
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ok = check_path(net, layer, width, points)
    return ok


def bow(a, c, depth, t1, t2, side):
    """Return [a, m1, m2, c] bowing the a-c segment by `depth` along the
    perpendicular normal, on `side` (+1 or -1), between fractions t1,t2."""
    dx, dy = c[0] - a[0], c[1] - a[1]
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    nx, ny = -uy * side, ux * side
    p1 = (a[0] + t1 * dx, a[1] + t1 * dy)
    p2 = (a[0] + t2 * dx, a[1] + t2 * dy)
    m1 = (p1[0] + nx * depth, p1[1] + ny * depth)
    m2 = (p2[0] + nx * depth, p2[1] + ny * depth)
    return [a, m1, m2, c]


def notch(a, c, depth, t1, t2, side):
    """Stay exactly on the original a-c line until t1, offset by `depth`
    between t1 and t2, then rejoin the original line from t2 to c.
    Returns [a, p1, o1, o2, p2, c]."""
    dx, dy = c[0] - a[0], c[1] - a[1]
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    nx, ny = -uy * side, ux * side
    p1 = (a[0] + t1 * dx, a[1] + t1 * dy)
    p2 = (a[0] + t2 * dx, a[1] + t2 * dy)
    o1 = (p1[0] + nx * depth, p1[1] + ny * depth)
    o2 = (p2[0] + nx * depth, p2[1] + ny * depth)
    return [a, p1, o1, o2, p2, c]


def search_notch(net, layer, width, a, c, t1, t2):
    for side in (1, -1):
        for depth in (0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6):
            pts = notch(a, c, depth, t1, t2, side)
            if quiet_check(net, layer, width, pts):
                print("FOUND notch for %s: side=%d depth=%.2f -> %s" % (net, side, depth, pts))
                return pts
    print("NO NOTCH FOUND for %s between %s and %s" % (net, a, c))
    return None


def search_bow(net, layer, width, a, c, t1, t2):
    for side in (1, -1):
        for depth in (0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6):
            pts = bow(a, c, depth, t1, t2, side)
            if quiet_check(net, layer, width, pts):
                print("FOUND for %s: side=%d depth=%.2f -> %s" % (net, side, depth, pts))
                return pts
    print("NO BOW FOUND for %s between %s and %s" % (net, a, c))
    return None


if __name__ == "__main__":
    # ---- A2 ----
    check_path("A2", 4, 0.1,
               [(36.45, 10.8), (34.6, 10.8), (34.6, 10.6), (31.6, 10.6), (31.6, 10.8), (31.5, 10.8)])
    # ---- FT-RESETN ----
    check_path("FT-RESETN", 6, 0.0762,
               [(24.85, 11.05), (31.6, 11.05), (31.6, 10.65), (34.65, 10.65), (34.65, 11.05), (36.8, 11.05)])
    # ---- SDRAM-CLK ----
    check_path("SDRAM-CLK", 3, 0.1,
               [(32.9, 11.75), (32.78, 12.51), (32.75, 14.79), (32.85, 15.55)])
    # ---- UDQM ----
    check_path("UDQM", 3, 0.1,
               [(36.2, 11.95), (36.2, 11.88), (33.55, 11.88), (33.55, 11.95)])
    # ---- TDI (bow UP away from GND row, staying clear of A9's wires below) ----
    check_path("TDI", 16, 0.0762,
               [(30.0609, 11.0109), (31.6, 11.0109), (31.6, 11.32), (33.42, 11.32),
                (33.42, 11.0109), (33.4899, 11.0109)])
    # ---- PROG# part a (deeper jog to also clear TDI's diagonal) ----
    check_path("PROG#", 16, 0.0762,
               [(34.0614, 11.9634), (34.0614, 11.8), (30.6324, 11.8), (30.6324, 11.9634)])
    # ---- PROG# part b (diagonal near-hit) ----
    check_path("PROG#", 16, 0.0762,
               [(34.0614, 11.9634), (33.9111, 12.3081), (34.2997, 12.6967), (36.0045, 13.9065)])
    # ---- SD-DAT2 (long diagonal grazing bottom-right via; also must avoid CHAN11) ----
    search_bow("SD-DAT2", 16, 0.1, (37.1, 14.5), (24.7, 10.0), 0.15, 0.32)
    # ---- CHAN15 (staircase brushing top-right via corner) ----
    search_bow("CHAN15", 16, 0.1, (34.55, 11.15), (34.15, 10.75), 0.25, 0.75)
