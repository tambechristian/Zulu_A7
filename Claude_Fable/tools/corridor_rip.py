# -*- coding: utf-8 -*-
"""Take the through vias of signal nets out of a rectangle, so the router
has to re-route those nets without a layer change there.

    python tools/corridor_rip.py in.brd out.brd --box x0,y0,x1,y1 [--keep NET,NET]

WHY. The strip between U3's east end (x 38.8) and U1's west balls (x 42)
holds one column of through vias at x 38.9..39.2 -- the layer changes of
the SDRAM bus and of a dozen other nets crossing to U2/U3. A through via
blocks every layer; 21 of them at 0.35 mm pitch are a 7 mm wall on all six
signal layers, and every re-route so far has had to go round it (A8 alone
routes as a 99 mm detour on the 2026-09-06 branch). With microvias in U1's
balls the wall is the only thing left in the corridor that needs a via.

WHAT IT DOES. Deletes every through via inside the box whose net is not a
plane/power net, and every wire of those nets that ends at a deleted via
(the router drops the rest of the dangling copper itself when the net is
forced). Writes out.brd.nets with the affected nets for CLOSE_FORCE.
"""

import io
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_connectivity as C   # noqa: E402
import bga_microvias as BM   # noqa: E402

SIG_RE = re.compile(r'(<signal name="([^"]+)"[^>]*>)(.*?)(</signal>)', re.S)


def main():
    args = sys.argv[1:]
    i = args.index("--box")
    x0, y0, x1, y1 = (float(v) for v in args[i + 1].split(","))
    del args[i:i + 2]
    keep = set()
    if "--keep" in args:
        i = args.index("--keep")
        keep = set(args[i + 1].split(","))
        del args[i:i + 2]
    src, dst = args[0], args[1]
    board = io.open(src, encoding="utf-8", errors="replace").read()
    parsed = C.parse_signal_objects(board)
    victims = {}
    for net, (objects, terminals, planes) in parsed.items():
        if net in BM.PLANE or net.startswith("VCC") or net in keep:
            continue
        vias = [o for o in objects if o["kind"] == "via" and len(o["layers"]) > 2
                and x0 <= o["at"][0] <= x1 and y0 <= o["at"][1] <= y1]
        if not vias:
            continue
        wires = [o for o in objects if o["kind"] == "wire" and any(
            math.hypot(o[e][0] - v["at"][0], o[e][1] - v["at"][1]) < 1e-6 for v in vias for e in ("a", "b"))]
        victims[net] = (vias, wires)
        print("  %-12s %d through via(s) in the box at %s, %d attached wire(s)" % (
            net, len(vias), ", ".join("(%.2f,%.2f)" % tuple(v["at"]) for v in vias), len(wires)))

    def sub(m):
        net = m.group(2)
        if net not in victims:
            return m.group(0)
        vias, wires = victims[net]
        body = m.group(3)

        def keep_w(w):
            a = (float(w.group(1)), float(w.group(2)))
            b = (float(w.group(3)), float(w.group(4)))
            L = int(w.group(6))
            for o in wires:
                if L in o["layers"] and abs(a[0] - o["a"][0]) < 1e-6 and abs(a[1] - o["a"][1]) < 1e-6 \
                        and abs(b[0] - o["b"][0]) < 1e-6 and abs(b[1] - o["b"][1]) < 1e-6:
                    return ""
            return w.group(0)

        def keep_v(v):
            at = dict(re.findall(r'(\w+)="([^"]*)"', v.group(0)))
            if "x" in at:
                for o in vias:
                    if abs(float(at["x"]) - o["at"][0]) < 1e-6 and abs(float(at["y"]) - o["at"][1]) < 1e-6:
                        return ""
            return v.group(0)
        body = re.sub(r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)" width="([\d.]+)" layer="(\d+)"[^>]*/>', keep_w, body)
        body = re.sub(r"<via\s[^>]*?(?:/>|>\s*</via>)", keep_v, body, flags=re.S)
        return m.group(1) + body + m.group(4)

    out = SIG_RE.sub(sub, board)
    import xml.etree.ElementTree as ET
    ET.fromstring(out)
    io.open(dst, "w", encoding="utf-8", newline="").write(out)
    io.open(dst + ".nets", "w").write(",".join(sorted(victims)))
    print("wrote %s: %d via(s) of %d net(s) removed from x %.1f..%.1f y %.1f..%.1f" % (
        dst, sum(len(v) for v, w in victims.values()), len(victims), x0, x1, y0, y1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
