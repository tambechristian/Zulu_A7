# -*- coding: utf-8 -*-
"""Turn blind vias into through vias wherever the column is clear.

    python tools/unblind_vias.py board.brd            report
    python tools/unblind_vias.py board.brd --apply    rewrite extents in place

WHY. The 8-layer conversion left nine 0.20 mm vias spanning part of the stack
(1-5, 5-16, 6-16, 1-2) and sixteen 0.10 mm laser vias. PCBWay builds a blind
via as a sequential lamination step and prices it as one; a through via is the
ordinary process. A blind via whose column happens to be clear on the layers it
does not reach costs nothing to make through, and it then stops being a build
question that PCBWay has to approve. Laser vias are not touched here: their
nets are rerouted on signal layers by close_airwires (CLOSE_FORCE), which is
the only honest way to lose a 0.10 mm hole.

CHECK. On every layer the via does not currently span, its 0.30 mm land must
clear foreign wires and pads by the wire-wire rule, and its drill must keep
0.20 mm hole to hole from every other drill (0.40 centre to centre for two
0.20 mm holes). The same measure check_board uses, so a via this passes is one
check_board passes.
"""

import io
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import escape as E   # noqa: E402
import geom as G     # noqa: E402

APPLY = "--apply" in sys.argv
BRD = next((a for a in sys.argv[1:] if a.endswith(".brd")), None)
if not BRD:
    raise SystemExit("usage: unblind_vias.py board.brd [--apply]")


def main():
    board = io.open(BRD, encoding="utf-8", errors="replace").read()
    clr = G.rule_mm(board, "mdWireWire")
    sig = re.search(r"<signals>(.*)</signals>", board, re.S).group(1)
    signals = dict((m.group(1), m.group(2)) for m in
                   re.finditer(r'<signal name="([^"]+)"[^>]*>(.*?)</signal>', sig, re.S))
    holes = []      # (net, x, y, drill)
    for net, body in signals.items():
        for m in re.finditer(r"<via\s([^>]*)>", body):
            a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
            if "x" in a:
                holes.append((net, float(a["x"]), float(a["y"]), float(a.get("drill", "0.2"))))
    for onet, x, y, hx, hy, side in E.board_copper(board, skip=()):
        if side == 0:
            holes.append((onet, x, y, 2 * hx - 0.5))   # board_copper: di = drill + 0.5
    layer_models = {}
    changed, kept = [], []
    out = board
    for net, body in signals.items():
        for m in re.finditer(r"<via\s([^>]*)>", body):
            a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
            if "x" not in a or a.get("extent", "1-16") == "1-16":
                continue
            drill = float(a.get("drill", "0.2"))
            if drill < 0.2 - 1e-6:
                kept.append("%-10s (%s,%s) %s drill %.2f: laser via, reroute its net instead"
                            % (net, a["x"], a["y"], a["extent"], drill))
                continue
            vx, vy = float(a["x"]), float(a["y"])
            dia = float(a["diameter"]) if "diameter" in a else drill + 2 * max(drill * 0.25, 0.05)
            lo, hi = sorted(int(v) for v in a["extent"].split("-"))
            missing = [L for L in (1, 2, 3, 4, 5, 6, 7, 16) if not lo <= L <= hi]
            worst = None
            for L in missing:
                if (net, L) not in layer_models:
                    layer_models[(net, L)] = G.copper_model(board, net, L)
                rects, circs, segs = layer_models[(net, L)]
                for px, py, hx, hy, cr in rects:
                    d = G.rect_pt((px, py, hx, hy), vx, vy) - cr - dia / 2
                    worst = d if worst is None else min(worst, d)
                for cx, cy, r in circs:
                    d = math.hypot(cx - vx, cy - vy) - r - dia / 2
                    worst = d if worst is None else min(worst, d)
                for u, v, r in segs:
                    d = E.seg_pt(u, v, (vx, vy)) - r - dia / 2
                    worst = d if worst is None else min(worst, d)
            hole_ok = True
            for onet, hx_, hy_, dr in holes:
                if abs(hx_ - vx) < 1e-6 and abs(hy_ - vy) < 1e-6:
                    continue
                need = max(0.2, G.rule_mm(board, "mdDrill")) if max(dr, drill) >= 0.2 - 1e-6 else G.rule_mm(board, "mdDrill")
                if math.hypot(hx_ - vx, hy_ - vy) - dr / 2 - drill / 2 < need - 1e-6:
                    hole_ok = False
            if (worst is None or worst >= clr - 1e-6) and hole_ok:
                new = m.group(0).replace('extent="%s"' % a["extent"], 'extent="1-16"')
                out = out.replace(m.group(0), new, 1)
                changed.append("%-10s (%s,%s) %s -> 1-16  (closest foreign copper %.3f mm)"
                               % (net, a["x"], a["y"], a["extent"], worst if worst is not None else 9))
            else:
                kept.append("%-10s (%s,%s) %s stays blind: %s"
                            % (net, a["x"], a["y"], a["extent"],
                               "hole spacing" if not hole_ok else "copper at %.3f mm" % worst))
    for line in changed:
        print("  through  " + line)
    for line in kept:
        print("  ----     " + line)
    print("%d via(s) made through, %d left as they are" % (len(changed), len(kept)))
    if APPLY and changed:
        io.open(BRD, "w", encoding="utf-8", newline="").write(out)
        print("wrote %s" % BRD)
    return 0


if __name__ == "__main__":
    sys.exit(main())
