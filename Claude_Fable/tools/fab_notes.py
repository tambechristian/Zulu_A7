# -*- coding: utf-8 -*-
"""Write the FAB NOTE lines on layer 48 from what the board actually holds.

    python tools/fab_notes.py in.brd out.brd

WHY. The notes are read by PCBWay's CAM engineer, not by Fusion, and they
went stale twice: the lamination note still listed deep laser spans the HDI
swap removed, and nothing said that the 30 microvias sit in BGA and TSOP pads,
or that one GND capacitor pad carries a 0.20 mm via (gnd_stitch.py,
2026-09-05). So the notes are generated: the via inventory is counted from the
file, and every via whose centre lies inside an SMD pad is listed as
via-in-pad. Existing "FAB NOTE:" texts on layer 48 are replaced; other text
is untouched.
"""

import collections
import io
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import escape as E   # noqa: E402

NOTE_RE = re.compile(r'<text x="[^"]*" y="[^"]*" size="[^"]*" layer="48"[^>]*>(?:FAB NOTE:|  )[^<]*</text>\s*')   # note lines and their wrapped continuations
Y0, DY, X = 59, 1, 0


def main():
    src, dst = sys.argv[1], sys.argv[2]
    board = io.open(src, encoding="utf-8", errors="replace").read()
    inv = collections.Counter()
    vias = []
    for m in re.finditer(r"<via\s([^>]*)>", board):
        at = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        if "x" not in at:
            continue
        lo, hi = sorted(int(v) for v in at.get("extent", "1-16").split("-"))
        drill = float(at.get("drill", "0.2"))
        inv[(lo, hi, drill)] += 1
        vias.append((float(at["x"]), float(at["y"]), lo, hi, drill))
    pads = [(n, x, y, hx, hy, side) for n, x, y, hx, hy, side in E.board_copper(board, skip=()) if side != 0]
    in_pad = collections.Counter()
    for vx, vy, lo, hi, drill in vias:
        for n, x, y, hx, hy, side in pads:
            if abs(vx - x) <= hx and abs(vy - y) <= hy:
                in_pad[(drill, "BGA/TSOP pad" if drill < 0.15 else "SMD pad of %s" % (n or "no net"))] += 1
                break
    through = sum(c for (lo, hi, d), c in inv.items() if (lo, hi) == (1, 16))
    micro = [(k, c) for k, c in inv.items() if k[2] < 0.15]
    blind = [(k, c) for k, c in inv.items() if k[2] >= 0.15 and (k[0], k[1]) != (1, 16)]
    # count via-in-pad by drill size and pad kind, never per net: the per-net
    # list made one text 300 mm wide and Fusion's zoom-to-fit shrank the board
    # to a thumbnail (2026-09-05)
    by_kind = collections.Counter()
    for (drill, kind), c in in_pad.items():
        by_kind[(drill, "BGA/TSOP PADS" if kind.startswith("BGA") else "PASSIVE SMD PADS")] += c
    setup = re.search(r'<param name="layerSetup" value="([^"]*)"', board)
    build = "2+4+2 HDI (BUILD-UP L1 L2 / CORE L3-L6 / BUILD-UP L7 L16), STAGGERED MICROVIAS 1-2, 2-3, 16-7, 7-6" \
        if setup and setup.group(1).startswith("[3:") else "1+6+1 HDI"
    notes = [
        "FAB NOTE: 8-LAYER %s, SEQUENTIAL LAMINATION. PCBWAY PRE-PRODUCTION APPROVAL REQUIRED. 3 MIL TRACE / 3 MIL SPACE." % build,
        "FAB NOTE: %d THROUGH VIAS 0.20 DRILL / 0.30 LAND. LASER MICROVIAS 0.10 DRILL / 0.20 LAND: %s." % (
            through, ", ".join("%dx L%d-L%d" % (c, k[0], k[1]) for k, c in sorted(micro)) or "none"),
        "FAB NOTE: MECHANICAL BLIND VIAS 0.20 DRILL: %s." % (
            ", ".join("%dx L%d-L%d" % (c, k[0], k[1]) for k, c in sorted(blind)) or "none"),
        "FAB NOTE: EVERY VIA IN AN SMD PAD IS VIA-IN-PAD: %s. IPC-4761 TYPE VII RESIN FILLED, COPPER CAPPED, PLANARIZED." % (
            "; ".join("%dx %.2fmm IN %s" % (c, k[0], k[1]) for k, c in sorted(by_kind.items())) or "none"),
        "FAB NOTE: U2 EP - 9x 0.20mm FINISHED VIA-IN-PAD, SAME FILL AND CAP. DO NOT SUBSTITUTE TENTING ANYWHERE.",
    ]
    body, n_old = NOTE_RE.subn("", board)
    # keep every line under WRAP characters (about 60 mm at this size), so the
    # note block stays narrower than the board
    WRAP = 118
    lines = []
    for t in notes:
        words, cur = t.split(" "), ""
        for w in words:
            if cur and len(cur) + 1 + len(w) > WRAP:
                lines.append(cur)
                cur = "  " + w
            else:
                cur = (cur + " " + w) if cur else w
        lines.append(cur)
    notes = lines
    # first note on top: y grows upwards on the board
    text = "".join('<text x="%d" y="%d" size="0.6" layer="48" ratio="10">%s</text>\n' % (X, Y0 + (len(notes) - 1 - i) * DY, t)
                   for i, t in enumerate(notes))
    pm = re.search(r"<plain>\s*", body)
    if pm:
        body = body[:pm.end()] + text + body[pm.end():]
    else:
        body = body.replace("</board>", "<plain>\n" + text + "</plain>\n</board>", 1)
    import xml.etree.ElementTree as ET
    ET.fromstring(body)
    io.open(dst, "w", encoding="utf-8", newline="").write(body)
    print("%d old note(s) replaced by %d:" % (n_old, len(notes)))
    for t in notes:
        print("  " + t)
    print("wrote", dst)


if __name__ == "__main__":
    main()
