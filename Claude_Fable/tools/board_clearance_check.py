"""Full-fidelity local clearance checker mirroring check_board.py's routing
section exactly: real via diameters (via geom.vias(), including the
drill+restring default for vias with no explicit diameter attribute), all
component pads (via _scratch_pad_model.build_cop), and all other-net copper
wires per layer. Used to validate/iterate candidate CHAN15 segments before
burning a full check_board.py run.
"""
import sys, re, math, collections
sys.path.insert(0, "tools")
import geom as G
import board_pad_model as PM

CW = 0.0762   # wire-wire / wire-via clearance
CP = 0.0762   # wire-pad clearance
GND_DRILL_MIN = 0.2  # informational only


def load(board_path):
    b = open(board_path, encoding="utf-8").read()
    cop, cv, cp, cw = PM.build_cop(b)
    sigs = dict(re.findall(r'<signal name="([^"]+)">(.*?)</signal>', b, re.S))
    other_wires = []   # (net, (x1,y1),(x2,y2),width,layer)
    other_vias = []    # (net, x,y,dia)
    for nm, body in sigs.items():
        if nm == "CHAN15":
            continue
        for m in re.finditer(
                r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)" width="([\d.]+)" layer="(\d+)"',
                body):
            x1, y1, x2, y2, wd, ly = m.groups()
            other_wires.append((nm, (float(x1), float(y1)), (float(x2), float(y2)), float(wd), int(ly)))
        for vx, vy, vd in G.vias(body):
            other_vias.append((nm, vx, vy, vd))
    return cop, other_wires, other_vias


def d_pt_seg(a, c, p):
    ax, ay = a; cx, cy = c; px, py = p
    dx, dy = cx - ax, cy - ay
    L2 = dx * dx + dy * dy
    if L2 < 1e-12:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def seg_vs_seg_dist(a, c, p, q):
    # min distance between two segments (a-c) and (p-q); coarse sampling ok since
    # our segments are short and this is only used for wire-vs-wire on same layer.
    n = 40
    best = 1e9
    for i in range(n + 1):
        t = i / n
        x = a[0] + (c[0] - a[0]) * t
        y = a[1] + (c[1] - a[1]) * t
        d = d_pt_seg(p, q, (x, y))
        if d < best:
            best = d
    return best


def check_wire(cop, other_wires, other_vias, a, c, width, layer, verbose=False):
    """Return list of violation strings for a candidate CHAN15 wire segment."""
    viol = []
    half = width / 2.0
    # vs other-net vias (checked on every layer, vias are copper everywhere)
    for nm, vx, vy, vd in other_vias:
        d = d_pt_seg(a, c, (vx, vy)) - vd / 2.0 - half
        if d < CW - 1e-9:
            viol.append("wire vs %s via at %.4f,%.4f: %.4f, needs %.4f" % (nm, vx, vy, d, CW))
    # vs other-net wires on same layer
    for nm, p, q, wd, ly in other_wires:
        if ly != layer:
            continue
        d = seg_vs_seg_dist(a, c, p, q) - wd / 2.0 - half
        if d < CW - 1e-9:
            viol.append("wire vs %s wire L%d at (%.3f,%.3f)-(%.3f,%.3f): %.4f, needs %.4f"
                         % (nm, ly, p[0], p[1], q[0], q[1], d, CW))
    # vs pads (layer-gated exactly like check_board.py), via the shared helper
    ok, margin = PM.wire_vs_pad_ok(a, c, layer, width, cop, CP)
    if not ok:
        viol.append("wire vs pad: worst margin %.4f, needs 0" % margin)
    return viol


def check_via(cop, other_vias, vx, vy, dia, exclude_nets=()):
    viol = []
    for nm, ox, oy, od in other_vias:
        d = math.hypot(vx - ox, vy - oy) - dia / 2.0 - od / 2.0
        if d < CW - 1e-9:
            viol.append("via vs %s via at %.4f,%.4f: %.4f, needs %.4f" % (nm, ox, oy, d, CW))
    ok, margin = PM.via_vs_pad_ok(vx, vy, dia, cop, CW)
    if not ok:
        viol.append("via vs pad: worst margin %.4f, needs 0" % margin)
    return viol


if __name__ == "__main__":
    cop, other_wires, other_vias = load("zulu_a7.brd")
    print("cop entries:", len(cop), "other wires:", len(other_wires), "other vias:", len(other_vias))
