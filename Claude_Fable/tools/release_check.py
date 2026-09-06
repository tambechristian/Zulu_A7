# -*- coding: utf-8 -*-
"""Every check that gates the board, in one run, with one summary.

    python tools/release_check.py [board.brd [schematic.sch]]

Runs, in order, and reports each as a line:
  check_board.py        structure, parts, nets, pads, libraries, placement,
                        rules, routing geometry (clearances, drills, landings)
  check_connectivity.py every net one piece, planes taken as the flood finds them
  plane_islands.py      L2 GND and L5 VCC3V3 pours reach every own through object
  blind vias            how many vias are not 1-16 through holes, and which
  airwires              what Fusion's Ratsnest should report: the sum over nets
                        of (pieces - 1) under the honest connectivity model

The exit code is the number of gates that failed, so it can gate a commit.
"""

import collections
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import check_connectivity as C   # noqa: E402
import plane_islands as PI       # noqa: E402

BRD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "zulu_a7.brd")
SCH = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "zulu_a7.sch")


def main():
    failed = 0
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    run = subprocess.run([sys.executable, os.path.join(HERE, "check_board.py"), BRD, SCH],
                         capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    findings = [l.strip() for l in run.stdout.splitlines() if l.strip().startswith("****")]
    m = re.search(r"(\d+) finding\(s\)", run.stdout)
    n = int(m.group(1)) if m else -1
    print("%s  check_board      %s" % ("PASS" if n == 0 else "FAIL", "0 findings" if n == 0 else "%d finding(s)" % n))
    for f in findings[:10]:
        print("        " + f[:200])
    failed += n != 0

    board = io.open(BRD, encoding="utf-8", errors="replace").read()
    parsed = C.parse_signal_objects(board)
    split, airwires = [], 0
    for net, (objects, terminals, planes) in sorted(parsed.items()):
        if terminals < 2:
            continue
        pieces = len(C.components(objects, terminals, planes))
        if pieces > 1:
            split.append("%s:%d" % (net, pieces))
            airwires += pieces - 1
    print("%s  connectivity     %s" % ("PASS" if not split else "FAIL",
                                       "every net one piece" if not split else
                                       "%d split net(s): %s" % (len(split), ", ".join(split))))
    print("%s  airwires         %d (what Ratsnest should report)" % ("PASS" if airwires == 0 else "FAIL", airwires))
    failed += bool(split)

    planes = []
    for net in ("GND", "VCC3V3"):
        m = re.search(r'<signal name="%s"[^>]*>(.*?)</signal>' % net, board, re.S)
        for layer in re.findall(r'<polygonpour layer="(\d+)"', m.group(1) if m else ""):
            if 2 <= int(layer) <= 7:
                planes.append((int(layer), net))
    for layer, net in planes:
        res = PI.analyse(board, layer, net, log=lambda *a: None)
        if res is None:
            print("FAIL  plane L%d %-7s no pour" % (layer, net))
            failed += 1
            continue
        bad = len(res["isolated"]) + len(res["islanded"])
        print("%s  plane L%d %-7s %s" % ("PASS" if bad == 0 else "FAIL", layer, net,
                                          "main piece reaches every own through object" if bad == 0 else
                                          "%d isolated, %d on islands" % (len(res["isolated"]), len(res["islanded"]))))
        failed += bad != 0

    blind = collections.Counter()
    for m in re.finditer(r"<via\s([^>]*)>", board):
        a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        if "x" not in a:
            continue
        ext = a.get("extent", "1-16")
        drill = float(a.get("drill", "0.2"))
        if ext != "1-16" or drill < 0.2 - 1e-6:
            blind["%s drill %.2f" % (ext, drill)] += 1
    total = sum(blind.values())
    print("%s  vias             %s" % ("PASS" if total == 0 else "NOTE",
                                       "all through 1-16 at 0.20 mm or larger" if total == 0 else
                                       "%d not through/0.20: %s" % (total, dict(blind))))
    print("%d gate(s) failed" % failed)
    return failed


if __name__ == "__main__":
    sys.exit(main())
