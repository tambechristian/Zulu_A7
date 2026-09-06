# -*- coding: utf-8 -*-
"""Draw the placement: every part as its pad outline and name, one SVG per
side, moved parts highlighted.

    python tools/place_view.py board.brd out_top.svg out_bottom.svg [--moved A,B,C] [--scale 18]

Bottom view is drawn as seen through the board (not mirrored), the way
Fusion shows it, so x runs the same way in both pictures.
"""

import io
import re
import sys


def rp(x, y, rot):
    r = rot[1:] if rot.startswith("M") else rot
    ang = int(r[1:]) % 360 if len(r) > 1 else 0
    x, y = {0: (x, y), 90: (-y, x), 180: (-x, -y), 270: (y, -x)}[ang]
    return (-x, y) if rot.startswith("M") else (x, y)


def main():
    args = sys.argv[1:]
    moved = set()
    scale = 18.0
    if "--moved" in args:
        i = args.index("--moved")
        moved = set(args[i + 1].split(","))
        del args[i:i + 2]
    if "--scale" in args:
        i = args.index("--scale")
        scale = float(args[i + 1])
        del args[i:i + 2]
    src, out_t, out_b = args[0], args[1], args[2]
    b = io.open(src, encoding="utf-8", errors="replace").read()
    pkg = {}
    for lm in re.finditer(r'<library name="([^"]+)">(.*?)</library>', b, re.S):
        for pm in re.finditer(r'<package name="([^"]+)"[^>]*>(.*?)</package>', lm.group(2), re.S):
            pkg[(lm.group(1), pm.group(1))] = pm.group(2)
    outline = re.findall(r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)"[^>]*layer="20"', b)
    xs = [float(v) for q in outline for v in (q[0], q[2])]
    ys = [float(v) for q in outline for v in (q[1], q[3])]
    x0, y0, x1, y1 = min(xs) - 1, min(ys) - 1, max(xs) + 1, max(ys) + 1
    W, H = (x1 - x0) * scale, (y1 - y0) * scale

    def X(x):
        return (x - x0) * scale

    def Y(y):
        return (y1 - y) * scale

    els = []
    for m in re.finditer(r'<element name="([^"]+)" library="([^"]+)" package="([^"]+)"[^>]*x="([-\d.]+)" y="([-\d.]+)"(?:[^>]*rot="([^"]+)")?', b):
        n, lib, pk, x, y, rot = m.group(1), m.group(2), m.group(3), float(m.group(4)), float(m.group(5)), m.group(6) or "R0"
        body = pkg.get((lib, pk), "")
        pads = []
        for pn, px, py, dx, dy in re.findall(r'<smd name="([^"]+)" x="([-\d.]+)" y="([-\d.]+)" dx="([\d.]+)" dy="([\d.]+)"', body):
            a = rp(float(px), float(py), rot)
            swap = rot.lstrip("M") in ("R90", "R270")
            hx, hy = (float(dy) / 2, float(dx) / 2) if swap else (float(dx) / 2, float(dy) / 2)
            pads.append((x + a[0], y + a[1], hx, hy, "smd"))
        for pn, px, py, d in re.findall(r'<pad name="([^"]+)" x="([-\d.]+)" y="([-\d.]+)"[^>]*drill="([\d.]+)"', body):
            a = rp(float(px), float(py), rot)
            pads.append((x + a[0], y + a[1], float(d) * 0.9, float(d) * 0.9, "th"))
        side = "B" if rot.startswith("M") else "T"
        els.append((n, pk, side, x, y, pads))
    for side, out in (("T", out_t), ("B", out_b)):
        svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" style="background:#1b1b1b">' % (W, H, W, H)]
        svg.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#243024" stroke="#8a8" stroke-width="1"/>' % (X(min(xs)), Y(max(ys)), (max(xs) - min(xs)) * scale, (max(ys) - min(ys)) * scale))
        # mm grid every 5 mm
        for gx in range(0, int(max(xs)) + 1, 5):
            svg.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#334433" stroke-width="0.5"/>' % (X(gx), Y(min(ys)), X(gx), Y(max(ys))))
            svg.append('<text x="%.1f" y="%.1f" fill="#8a8" font-size="9" font-family="sans-serif">%d</text>' % (X(gx) + 1, Y(min(ys)) + 10, gx))
        for gy in range(0, int(max(ys)) + 1, 5):
            svg.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#334433" stroke-width="0.5"/>' % (X(min(xs)), Y(gy), X(max(xs)), Y(gy)))
            svg.append('<text x="%.1f" y="%.1f" fill="#8a8" font-size="9" font-family="sans-serif">%d</text>' % (X(min(xs)) - 12, Y(gy) + 3, gy))
        for n, pk, s, x, y, pads in els:
            th = [p for p in pads if p[4] == "th"]
            if s != side and not th:
                continue
            col = "#ffd54f" if n in moved else ("#ef9a9a" if side == "T" else "#90caf9")
            if s != side:
                col = "#777"
            if pads:
                bx0 = min(p[0] - p[2] for p in pads); bx1 = max(p[0] + p[2] for p in pads)
                by0 = min(p[1] - p[3] for p in pads); by1 = max(p[1] + p[3] for p in pads)
                svg.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="none" stroke="%s" stroke-width="%s" opacity="0.9"/>' % (
                    X(bx0), Y(by1), (bx1 - bx0) * scale, (by1 - by0) * scale, col, "1.5" if n in moved else "0.8"))
                for px, py, hx, hy, kind in pads:
                    if kind == "th":
                        svg.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" stroke="%s" stroke-width="0.6"/>' % (X(px), Y(py), hx * scale, col))
                    else:
                        svg.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" opacity="0.55"/>' % (X(px - hx), Y(py + hy), 2 * hx * scale, 2 * hy * scale, col))
                fs = 8 if (bx1 - bx0) * scale > 30 else 6
                svg.append('<text x="%.1f" y="%.1f" fill="%s" font-size="%d" font-family="sans-serif" text-anchor="middle">%s</text>' % (
                    X((bx0 + bx1) / 2), Y(by1) - 1.5, "#fff" if n in moved else col, fs, n))
        svg.append('<text x="%.1f" y="%.1f" fill="#ccc" font-size="12" font-family="sans-serif">%s side (looking down through the board; yellow = moved)</text>' % (X(min(xs)), 14, "TOP" if side == "T" else "BOTTOM"))
        svg.append("</svg>")
        io.open(out, "w", encoding="utf-8").write("\n".join(svg))
        print("wrote", out, "%dx%d" % (W, H))
    return 0


if __name__ == "__main__":
    sys.exit(main())
